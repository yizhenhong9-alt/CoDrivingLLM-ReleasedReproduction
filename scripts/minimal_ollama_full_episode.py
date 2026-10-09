import argparse
import json
import platform
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if hasattr(value, "item"):
        return json_safe(value.item())
    return str(value)


def write_json(path, value):
    path.write_text(
        json.dumps(json_safe(value), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(json_safe(value), ensure_ascii=False) + "\n")


def create_run_directory(output_dir, run_id=None):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    identifier = run_id or "{}_{}".format(
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        uuid.uuid4().hex[:8],
    )
    run_directory = root / identifier
    run_directory.mkdir(exist_ok=False)
    return run_directory


def git_value(repository, *arguments):
    return subprocess.check_output(
        ["git", *arguments], cwd=str(repository), text=True,
        encoding="utf-8").strip()


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def environment_terminal_reason(env):
    vehicles = env.controlled_vehicles
    if any(bool(vehicle.crashed) for vehicle in vehicles):
        return "controlled_vehicle_collision"
    if all(bool(env.has_arrived(vehicle)) for vehicle in vehicles):
        return "all_controlled_vehicles_arrived"
    terminal_step = env.config["duration"] * env.config["policy_frequency"] - 1
    if env.steps >= terminal_step:
        return "released_duration_limit"
    if env.config.get("offroad_terminal") and not env.vehicle.on_road:
        return "offroad_terminal"
    return "unresolved_environment_terminal_condition"


def reliable_outcomes(env):
    try:
        collisions = [bool(vehicle.crashed)
                      for vehicle in env.controlled_vehicles]
    except (AttributeError, TypeError):
        collisions = "unavailable"
    try:
        arrivals = [bool(env.has_arrived(vehicle))
                    for vehicle in env.controlled_vehicles]
    except (AttributeError, TypeError):
        arrivals = "unavailable"
    return {
        "controlled_vehicle_collision": collisions,
        "controlled_vehicle_arrival": arrivals,
        "success": {
            "value": None,
            "status": "unavailable",
            "reason": "Released runner defines no independent success metric.",
        },
    }


def runtime_error_summary(error, completed_records, wall_clock_seconds,
                          traceback_text):
    return {
        "status": "runtime_error",
        "completion_status": "runtime_error",
        "termination_reason": "runtime_error",
        "total_steps": len(completed_records),
        "total_reward": sum(record["reward"] for record in completed_records),
        "wall_clock_seconds": wall_clock_seconds,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback_text,
        "llm_call_count": {
            "value": None,
            "status": "unavailable",
            "reason": "Existing backend exposes only its latest call, not a counter.",
        },
        "parser_failure_count": {
            "value": None,
            "status": "unavailable",
            "reason": "Released parsers expose no failure counter.",
        },
    }


def run_episode(env, negotiation_agent_factory, action_agent_factory,
                max_steps, record_step=None, clock=time.perf_counter):
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")

    total_reward = 0.0
    records = []
    for step_index in range(max_steps):
        step_started = clock()
        negotiation_agent = negotiation_agent_factory()
        action_agent = action_agent_factory()

        negotiation_prompt, conflicting_info = (
            negotiation_agent.llm_controller_run(env))
        llm_actions = action_agent.llm_controller_run(
            env,
            negotiation_prompt,
            conflicting_info,
            env.controlled_vehicles,
            memory=None,
        )
        action = [item for sublist in llm_actions for item in sublist]
        if action_agent.ACTIONS_ALL is not None and any(
                item not in action_agent.ACTIONS_ALL for item in action):
            raise ValueError(
                "Original action parser/mapping produced an invalid action ID: {}"
                .format(action))

        observation, reward, terminated, info = env.step(tuple(action), env)
        reward_value = float(reward)
        total_reward += reward_value
        record = {
            "step_index": step_index,
            "joint_action": [int(item) for item in action],
            "reward": reward_value,
            "terminated": bool(terminated),
            "step_execution_seconds": float(clock() - step_started),
            "environment_steps": json_safe(getattr(env, "steps", None)),
            "observation_shape": json_safe(
                getattr(observation, "shape", None)),
            "info": json_safe(info),
        }
        records.append(record)
        if record_step is not None:
            record_step(record)

        if terminated:
            return {
                "status": "completed",
                "completion_status": "environment_terminated",
                "termination_reason": environment_terminal_reason(env),
                "total_steps": len(records),
                "total_reward": total_reward,
                "records": records,
            }

    return {
        "status": "stopped",
        "completion_status": "max_steps_reached",
        "termination_reason": "max_steps_guard",
        "total_steps": len(records),
        "total_reward": total_reward,
        "records": records,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one Intersection Memory-OFF CoDrivingLLM episode.")
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument(
        "--output-dir", default="runs/intersection-memory-off")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    run_directory = create_run_directory(args.output_dir)
    metadata_path = run_directory / "run_metadata.json"
    steps_path = run_directory / "steps.jsonl"
    summary_path = run_directory / "episode_summary.json"
    error_path = run_directory / "error.json"
    started_wall = utc_now()
    started = time.perf_counter()
    env = None
    completed_records = []

    run_metadata = {
        "git_commit": git_value(repository, "rev-parse", "HEAD"),
        "branch": git_value(repository, "branch", "--show-current"),
        "scenario": "intersection-multi-agent-v0",
        "seed": args.seed,
        "memory_mode": "off",
        "backend": args.backend,
        "model": args.model,
        "ollama_endpoint": args.endpoint,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
        "start_time_utc": started_wall,
        "end_time_utc": None,
        "python_version": platform.python_version(),
        "packages": {
            "gym": package_version("gym"),
            "numpy": package_version("numpy"),
            "pandas": package_version("pandas"),
            "highway_env": "repository-local; package version unavailable",
        },
        "execution_status": "running",
    }
    write_json(metadata_path, run_metadata)

    try:
        # Runtime-only imports keep Local fake tests independent of simulator and
        # never import llm_controller.memory.
        import gym
        import highway_env  # noqa: F401 - registers repository environments
        from llm_controller.llm_agent_action import LlmAgent_action_module
        from llm_controller.llm_agent_negotiation_system import (
            LlmAgent_negotiation_module,
        )
        from llm_controller.llm_backend import ChatBackend

        env = gym.make("intersection-multi-agent-v0")
        env.reset(is_training=False, testing_seeds=args.seed)
        chat_backend = ChatBackend(
            backend=args.backend,
            model=args.model,
            endpoint=args.endpoint,
            timeout=args.timeout,
        )

        def record_completed_step(record):
            append_jsonl(steps_path, record)
            completed_records.append(record)

        result = run_episode(
            env,
            negotiation_agent_factory=lambda: LlmAgent_negotiation_module(
                env, chat_backend=chat_backend),
            action_agent_factory=lambda: LlmAgent_action_module(
                env, chat_backend=chat_backend),
            max_steps=args.max_steps,
            record_step=record_completed_step,
        )
        summary = {
            **{key: value for key, value in result.items()
               if key != "records"},
            "wall_clock_seconds": time.perf_counter() - started,
            "llm_call_count": {
                "value": None,
                "status": "unavailable",
                "reason": "Existing backend exposes only its latest call, not a counter.",
            },
            "parser_failure_count": {
                "value": None,
                "status": "unavailable",
                "reason": "Released parsers expose no failure counter.",
            },
            **reliable_outcomes(env),
        }
        write_json(summary_path, summary)
        run_metadata["execution_status"] = result["completion_status"]
        return 0
    except Exception as error:
        error_record = runtime_error_summary(
            error,
            completed_records,
            time.perf_counter() - started,
            traceback.format_exc(),
        )
        write_json(error_path, error_record)
        write_json(summary_path, error_record)
        run_metadata["execution_status"] = "runtime_error"
        raise
    finally:
        run_metadata["end_time_utc"] = utc_now()
        write_json(metadata_path, run_metadata)
        if env is not None:
            env.close()


if __name__ == "__main__":
    sys.exit(main())
