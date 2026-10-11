"""Bounded, diagnostic-only Highway probes for Stage 1N-R1.

This module intentionally keeps simulator/controller imports inside the RDP-only
entry path so Local tests can exercise orchestration with fakes.  It is not a
formal experiment runner and computes no success rate, PET, or travel velocity.
"""

import argparse
import json
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path


HIGHWAY_ENV_ID = "highway-v0"
DIAGNOSTIC_SEED = 987654
ALTERNATE_DIAGNOSTIC_SEED = 987655
FORMAL_SEEDS = frozenset(range(20))
DEFAULT_OUTPUT_ROOT = Path("runs/highway-stage1n-r1-runtime-probes")
MEMORY_NAMESPACE = (
    "runs/highway-stage1n-r1-preflight-memory-on/memory-db/highway-v0")
ACTION_CASES = {
    "same_first_reference": (3, 1, 1, 1),
    "same_first_changed_tail": (3, 4, 4, 4),
    "changed_first": (4, 1, 1, 1),
}
MAX_TERMINATION_STEPS = 45
MEMORY_CYCLES = 2
EXPECTED_CONTROLLED_VEHICLES = 4


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
    return {
        "status": "unsupported_type",
        "python_type": "{}.{}".format(
            type(value).__module__, type(value).__qualname__),
        "repr": repr(value),
    }


def write_json(path, value):
    path.write_text(
        json.dumps(json_safe(value), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_diagnostic_seed(seed):
    if seed in FORMAL_SEEDS:
        raise ValueError(
            "Stage 1N-R1 diagnostic seed must not be in formal range 0..19")
    if seed not in (DIAGNOSTIC_SEED, ALTERNATE_DIAGNOSTIC_SEED):
        raise ValueError(
            "Only documented diagnostic seeds {} and {} are allowed".format(
                DIAGNOSTIC_SEED, ALTERNATE_DIAGNOSTIC_SEED))
    return seed


def validate_probe_bounds(probe, max_steps, memory_cycles):
    if probe == "termination" and not (1 <= max_steps <= MAX_TERMINATION_STEPS):
        raise ValueError(
            "Termination probe max steps must be between 1 and {}".format(
                MAX_TERMINATION_STEPS))
    if probe == "memory-on" and memory_cycles != MEMORY_CYCLES:
        raise ValueError(
            "Memory probe is fixed at exactly {} cycles".format(MEMORY_CYCLES))
    return True


def validate_output_root(path):
    resolved = Path(path).resolve()
    lowered = [part.lower() for part in resolved.parts]
    if "runs" not in lowered:
        raise ValueError("Diagnostic output must be under runs/")
    if any("formal" in part or "batch" in part for part in lowered):
        raise ValueError("Diagnostic output must not use formal/batch namespaces")
    if not any("stage1n-r1" in part for part in lowered):
        raise ValueError("Diagnostic output must use a Stage 1N-R1 namespace")
    return resolved


def validate_fresh_diagnostic_db(path):
    resolved = Path(path).resolve()
    lowered = [part.lower() for part in resolved.parts]
    prohibited = ("intersection", "merge", "formal")
    if any(any(word in part for word in prohibited) for part in lowered):
        raise ValueError(
            "Diagnostic DB must not use Intersection, Merge, or formal namespaces")
    required = ("runs", "highway-stage1n-r1-preflight-memory-on",
                "memory-db", HIGHWAY_ENV_ID)
    for component in required:
        if component.lower() not in lowered:
            raise ValueError(
                "Diagnostic DB path must include namespace component {!r}"
                .format(component))
    if resolved.exists():
        raise FileExistsError(
            "Diagnostic DB must be absent; existing DB is never cleared/reused: {}"
            .format(resolved))
    return resolved


def vehicle_state(vehicle, index):
    route = getattr(vehicle, "route", None)
    destination_error = None
    try:
        destination = getattr(vehicle, "destination")
    except Exception as error:  # diagnostic evidence, not a fallback
        destination = None
        destination_error = {
            "type": type(error).__name__, "message": str(error)}
    return {
        "index": index,
        "python_class": "{}.{}".format(
            type(vehicle).__module__, type(vehicle).__qualname__),
        "display_id": str(vehicle).split(":")[0].strip(),
        "lane_index": json_safe(getattr(vehicle, "lane_index", None)),
        "position": json_safe(getattr(vehicle, "position", None)),
        "speed": json_safe(getattr(vehicle, "speed", None)),
        "crashed": json_safe(getattr(vehicle, "crashed", None)),
        "on_road": json_safe(getattr(vehicle, "on_road", None)),
        "route_present": route is not None,
        "route": json_safe(route),
        "destination": json_safe(destination),
        "destination_read_error": destination_error,
    }


def controlled_state(env):
    return [vehicle_state(vehicle, index)
            for index, vehicle in enumerate(env.controlled_vehicles)]


def canonical_initial_state(env):
    controlled_ids = {id(vehicle) for vehicle in env.controlled_vehicles}
    road_states = []
    for index, vehicle in enumerate(env.road.vehicles):
        state = vehicle_state(vehicle, index)
        state["controlled"] = id(vehicle) in controlled_ids
        road_states.append(state)
    return {
        "controlled": controlled_state(env),
        "road_vehicles": road_states,
    }


def topology_record(env, seed):
    controlled_count = len(env.controlled_vehicles)
    road_count = len(env.road.vehicles)
    unwrapped = getattr(env, "unwrapped", env)
    return {
        "probe": "reset",
        "diagnostic_only": True,
        "seed": seed,
        "environment_id": getattr(getattr(env, "spec", None), "id", None),
        "environment_class": "{}.{}".format(
            type(unwrapped).__module__, type(unwrapped).__qualname__),
        "action_space_repr": repr(env.action_space),
        "action_space_class": "{}.{}".format(
            type(env.action_space).__module__, type(env.action_space).__qualname__),
        "action_space_n": json_safe(getattr(env.action_space, "n", None)),
        "controlled_vehicle_count": controlled_count,
        "road_vehicle_count": road_count,
        "background_vehicle_count": road_count - controlled_count,
        "config": {
            key: json_safe(env.config.get(key)) for key in (
                "simulation_frequency", "policy_frequency", "duration",
                "controlled_vehicles", "vehicles_count", "offroad_terminal")
        },
        "controlled_vehicle_order": controlled_state(env),
    }


def differing_paths(left, right, prefix=""):
    if type(left) is not type(right):
        return [prefix or "$type"]
    if isinstance(left, dict):
        differences = []
        for key in sorted(set(left) | set(right)):
            path = "{}.{}".format(prefix, key) if prefix else str(key)
            if key not in left or key not in right:
                differences.append(path)
            else:
                differences.extend(differing_paths(left[key], right[key], path))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return ["{}.length".format(prefix)]
        differences = []
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences.extend(differing_paths(
                left_item, right_item, "{}[{}]".format(prefix, index)))
        return differences
    return [] if left == right else [prefix]


def create_and_reset(make_env, seed):
    validate_diagnostic_seed(seed)
    env = make_env()
    env.reset(is_training=False, testing_seeds=seed)
    return env


def run_seed_probe(make_env):
    states = []
    for seed in (DIAGNOSTIC_SEED, DIAGNOSTIC_SEED,
                 ALTERNATE_DIAGNOSTIC_SEED):
        env = create_and_reset(make_env, seed)
        try:
            states.append(canonical_initial_state(env))
        finally:
            env.close()
    same_differences = differing_paths(states[0], states[1])
    different_differences = differing_paths(states[0], states[2])
    return {
        "probe": "seed",
        "diagnostic_only": True,
        "seeds": [DIAGNOSTIC_SEED, DIAGNOSTIC_SEED,
                  ALTERNATE_DIAGNOSTIC_SEED],
        "same_seed_identical": not same_differences,
        "same_seed_differing_fields": same_differences,
        "different_seed_state_differs": bool(different_differences),
        "different_seed_differing_fields": different_differences,
        "canonical_states": states,
    }


def run_action_case(make_env, seed, action):
    env = create_and_reset(make_env, seed)
    try:
        before = controlled_state(env)
        observation, reward, terminated, info = env.step(action, env)
        return {
            "input_type": type(action).__name__,
            "action": json_safe(action),
            "accepted": True,
            "before": before,
            "after": controlled_state(env),
            "reward": json_safe(reward),
            "terminated": bool(terminated),
            "environment_steps": json_safe(getattr(env, "steps", None)),
            "observation_shape": json_safe(getattr(observation, "shape", None)),
            "info": json_safe(info),
        }
    except Exception as error:
        return {
            "input_type": type(action).__name__,
            "action": json_safe(action),
            "accepted": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }
    finally:
        env.close()


def run_action_probe(make_env, seed=DIAGNOSTIC_SEED):
    validate_diagnostic_seed(seed)
    cases = {
        name: run_action_case(make_env, seed, action)
        for name, action in ACTION_CASES.items()
    }
    list_case = run_action_case(make_env, seed, [3, 1, 1, 1])
    reference = cases["same_first_reference"]
    changed_tail = cases["same_first_changed_tail"]
    changed_first = cases["changed_first"]
    comparable = all(case.get("accepted") for case in cases.values())
    return {
        "probe": "action",
        "diagnostic_only": True,
        "seed": seed,
        "identical_seed_recreated_per_case": True,
        "cases": cases,
        "list_case": list_case,
        "same_first_transition_identical": (
            comparable and reference["after"] == changed_tail["after"]),
        "changed_first_transition_differs": (
            comparable and reference["after"] != changed_first["after"]),
        "interpretation_guard": (
            "Equality/difference is diagnostic evidence only; preserve raw states "
            "and do not infer from exception status alone."),
    }


def run_termination_probe(make_env, seed, max_steps):
    validate_diagnostic_seed(seed)
    validate_probe_bounds("termination", max_steps, MEMORY_CYCLES)
    env = create_and_reset(make_env, seed)
    records = []
    try:
        for policy_step in range(1, max_steps + 1):
            _, reward, terminated, info = env.step((1, 1, 1, 1), env)
            record = {
                "policy_step": policy_step,
                "environment_steps": json_safe(getattr(env, "steps", None)),
                "terminated": bool(terminated),
                "reward": json_safe(reward),
                "controlled_collisions": [
                    bool(getattr(vehicle, "crashed", False))
                    for vehicle in env.controlled_vehicles],
                "controlled_on_road": [
                    json_safe(getattr(vehicle, "on_road", None))
                    for vehicle in env.controlled_vehicles],
                "info": json_safe(info),
            }
            records.append(record)
            if terminated:
                break
        first_termination = next(
            (record["policy_step"] for record in records
             if record["terminated"]), None)
        collision_before_40 = any(
            any(record["controlled_collisions"])
            for record in records if record["policy_step"] < 40)
        return {
            "probe": "termination",
            "diagnostic_only": True,
            "seed": seed,
            "fixed_action": [1, 1, 1, 1],
            "max_steps_guard": max_steps,
            "config_duration": json_safe(env.config.get("duration")),
            "policy_frequency": json_safe(env.config.get("policy_frequency")),
            "first_terminated_policy_step": first_termination,
            "collision_before_step_40": collision_before_40,
            "duration_40_confirmed": (
                first_termination == 40 and not collision_before_40),
            "records": records,
            "bounded_alternative": (
                "If collision prevents duration confirmation, manually run once "
                "with seed 987655; do not search additional seeds."),
        }
    finally:
        env.close()


def run_arrival_probe(make_env, seed=DIAGNOSTIC_SEED):
    env = create_and_reset(make_env, seed)
    try:
        has_arrived = getattr(env, "has_arrived", None)
        calls = []
        if callable(has_arrived):
            for index, vehicle in enumerate(env.controlled_vehicles):
                try:
                    calls.append({
                        "index": index,
                        "value": bool(has_arrived(vehicle)),
                        "error": None,
                    })
                except Exception as error:
                    calls.append({
                        "index": index,
                        "value": None,
                        "error": {
                            "type": type(error).__name__,
                            "message": str(error),
                            "traceback": traceback.format_exc(),
                        },
                    })
        return {
            "probe": "arrival",
            "diagnostic_only": True,
            "seed": seed,
            "has_arrived_present": callable(has_arrived),
            "has_arrived_calls": calls,
            "controlled_vehicles": controlled_state(env),
            "termination_function": "{}.{}".format(
                type(getattr(env, "_is_terminal", None)).__module__,
                type(getattr(env, "_is_terminal", None)).__qualname__),
            "success_metric": "unavailable; no interpretation is applied",
        }
    finally:
        env.close()


def summarize_conflicts(env, conflicts):
    road_index = {id(vehicle): index
                  for index, vehicle in enumerate(env.road.vehicles)}
    records = []
    for vehicle, related in conflicts.items():
        records.append({
            "road_vehicle_index": road_index.get(id(vehicle)),
            "controlled": vehicle in env.controlled_vehicles,
            "conflict_count": len(related),
            "conflicts_with_road_indices": [
                road_index.get(id(other)) for other in related],
        })
    return records


def flatten_actions(llm_actions):
    return [item for sublist in llm_actions for item in sublist]


def run_negotiation_probe(make_env, negotiation_factory,
                          action_factory=None, with_llm=False,
                          seed=DIAGNOSTIC_SEED):
    env = create_and_reset(make_env, seed)
    try:
        agent = negotiation_factory(env)
        conflicts = agent.detect_conflicts(env)
        result = {
            "probe": "negotiation",
            "diagnostic_only": True,
            "seed": seed,
            "road_vehicle_count": len(env.road.vehicles),
            "controlled_vehicle_count": len(env.controlled_vehicles),
            "candidate_scope": "env.road.vehicles for non-intersection",
            "candidate_vehicle_count": len(env.road.vehicles),
            "pre_llm_conflicts": summarize_conflicts(env, conflicts),
            "pre_llm_conflict_set_empty": all(
                len(related) == 0 for related in conflicts.values()),
            "with_llm": with_llm,
            "llm_call_performed": False,
            "env_step_calls": 0,
        }
        if not with_llm:
            result["note"] = (
                "Pre-LLM evidence only; no Ollama call and no ActionAgent call.")
            return result
        if action_factory is None:
            raise ValueError("action_factory is required with --with-llm")
        negotiation_prompt, conflicting_info = agent.llm_controller_run(env)
        result["llm_call_performed"] = True
        action_agent = action_factory(env)
        llm_actions = action_agent.llm_controller_run(
            env, negotiation_prompt, conflicting_info,
            env.controlled_vehicles, memory=None)
        action = flatten_actions(llm_actions)
        result["negotiation_output"] = negotiation_prompt
        result["conflicting_info"] = json_safe(conflicting_info)
        result["action_decision_count"] = len(llm_actions)
        result["negotiation_supplied_to_action_module"] = True
        result["joint_action"] = json_safe(action)
        env.step(tuple(action), env)
        result["env_step_calls"] = 1
        return result
    finally:
        env.close()


class RecordingMemory:
    """Diagnostic proxy around the unmodified DrivingMemory interface."""

    def __init__(self, memory, event_sink, cycle, count_records):
        self._memory = memory
        self._events = event_sink
        self._cycle = cycle
        self._count_records = count_records

    def retrieveMemory(self, query_scenario, top_k=5):
        before = self._count_records(self._memory)
        result = self._memory.retrieveMemory(query_scenario, top_k=top_k)
        self._events.append({
            "event": "memory_retrieval",
            "cycle": self._cycle,
            "top_k": top_k,
            "record_count_visible_before_query": before,
        })
        return result

    def addMemory(self, *args, **kwargs):
        before = self._count_records(self._memory)
        result = self._memory.addMemory(*args, **kwargs)
        after = self._count_records(self._memory)
        self._events.append({
            "event": "memory_write",
            "cycle": self._cycle,
            "record_count_before": before,
            "record_count_after": after,
        })
        return result

    def __getattr__(self, name):
        return getattr(self._memory, name)


def run_memory_cycles(env, negotiation_factory, action_factory,
                      memory_factory, count_records,
                      cycles=MEMORY_CYCLES):
    validate_probe_bounds("memory-on", MAX_TERMINATION_STEPS, cycles)
    events = []
    cycle_records = []
    for cycle in range(1, cycles + 1):
        memory = memory_factory()
        proxy = RecordingMemory(memory, events, cycle, count_records)
        before = count_records(memory)
        retrieval_start = len([event for event in events
                               if event["event"] == "memory_retrieval"])
        write_start = len([event for event in events
                           if event["event"] == "memory_write"])
        negotiation_prompt, conflicting_info = (
            negotiation_factory(env).llm_controller_run(env))
        llm_actions = action_factory(env).llm_controller_run(
            env, negotiation_prompt, conflicting_info,
            env.controlled_vehicles, memory=proxy)
        action = flatten_actions(llm_actions)
        retrievals = len([event for event in events
                          if event["event"] == "memory_retrieval"]) - retrieval_start
        writes = len([event for event in events
                      if event["event"] == "memory_write"]) - write_start
        if retrievals != EXPECTED_CONTROLLED_VEHICLES:
            raise RuntimeError(
                "Expected 4 retrievals before env.step; observed {}".format(
                    retrievals))
        if writes != EXPECTED_CONTROLLED_VEHICLES:
            raise RuntimeError(
                "Expected 4 writes before env.step; observed {}".format(writes))
        after_decisions = count_records(memory)
        env.step(tuple(action), env)
        events.append({
            "event": "env_step",
            "cycle": cycle,
            "record_count": count_records(memory),
            "after_four_decisions_and_writes": True,
        })
        cycle_records.append({
            "cycle": cycle,
            "record_count_before_cycle": before,
            "retrieval_count": retrievals,
            "write_count": writes,
            "record_count_after_four_writes": after_decisions,
            "joint_action": json_safe(action),
        })
    return {
        "probe": "memory-on",
        "diagnostic_only": True,
        "cycles": cycles,
        "expected_queries_per_cycle": EXPECTED_CONTROLLED_VEHICLES,
        "expected_writes_per_cycle": EXPECTED_CONTROLLED_VEHICLES,
        "expected_top_k": 2,
        "events": events,
        "cycle_records": cycle_records,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 1N-R1 bounded Highway runtime diagnostics")
    parser.add_argument(
        "--probe", required=True,
        choices=("reset", "seed", "action", "termination", "arrival",
                 "negotiation", "memory-on"))
    parser.add_argument("--confirm-rdp", action="store_true")
    parser.add_argument("--seed", type=int, default=DIAGNOSTIC_SEED)
    parser.add_argument("--max-steps", type=int, default=MAX_TERMINATION_STEPS)
    parser.add_argument("--memory-cycles", type=int, default=MEMORY_CYCLES)
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument("--backend", default="ollama", choices=("ollama",))
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--embedding-backend", default="ollama",
                        choices=("ollama",))
    parser.add_argument("--embedding-model", default="nomic-embed-text:latest")
    parser.add_argument("--embedding-endpoint",
                        default="http://127.0.0.1:11435")
    parser.add_argument("--embedding-timeout", type=float, default=120)
    parser.add_argument("--memory-db-path", default=MEMORY_NAMESPACE)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args(argv)


def run_directory(output_root, probe):
    root = validate_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    identifier = "{}_{}_{}".format(
        probe,
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        uuid.uuid4().hex[:8],
    )
    directory = root / identifier
    directory.mkdir(exist_ok=False)
    return directory


def main(argv=None):
    args = parse_args(argv)
    if not args.confirm_rdp:
        raise RuntimeError(
            "Refusing runtime probe without explicit --confirm-rdp")
    validate_diagnostic_seed(args.seed)
    validate_probe_bounds(args.probe, args.max_steps, args.memory_cycles)
    if args.with_llm and args.probe != "negotiation":
        raise ValueError("--with-llm is only valid for the negotiation probe")
    if args.probe == "memory-on":
        database_path = validate_fresh_diagnostic_db(args.memory_db_path)
    else:
        database_path = None

    output = run_directory(args.output_root, args.probe)
    result_path = output / "probe_result.json"
    error_path = output / "probe_error.json"

    try:
        # RDP-only imports. Importing this module for Local tests has no
        # simulator, Ollama, embedding, Chroma, or DrivingMemory side effects.
        import gym
        import highway_env  # noqa: F401 - registers repository environments

        def make_env():
            return gym.make(HIGHWAY_ENV_ID)

        def chat_backend():
            from llm_controller.llm_backend import ChatBackend
            return ChatBackend(
                backend=args.backend, model=args.model,
                endpoint=args.endpoint, timeout=args.timeout)

        if args.probe == "reset":
            env = create_and_reset(make_env, args.seed)
            try:
                result = topology_record(env, args.seed)
            finally:
                env.close()
        elif args.probe == "seed":
            result = run_seed_probe(make_env)
        elif args.probe == "action":
            result = run_action_probe(make_env, args.seed)
        elif args.probe == "termination":
            result = run_termination_probe(make_env, args.seed, args.max_steps)
        elif args.probe == "arrival":
            result = run_arrival_probe(make_env, args.seed)
        elif args.probe == "negotiation":
            from llm_controller.llm_agent_negotiation_system import (
                LlmAgent_negotiation_module)
            backend = chat_backend() if args.with_llm else None
            negotiation_factory = lambda env: LlmAgent_negotiation_module(
                env, chat_backend=backend)
            action_factory = None
            if args.with_llm:
                from llm_controller.llm_agent_action import (
                    LlmAgent_action_module)
                action_factory = lambda env: LlmAgent_action_module(
                    env, chat_backend=backend, memory_mode="off")
            result = run_negotiation_probe(
                make_env, negotiation_factory, action_factory,
                with_llm=args.with_llm, seed=args.seed)
        else:
            from llm_controller.llm_agent_action import LlmAgent_action_module
            from llm_controller.llm_agent_negotiation_system import (
                LlmAgent_negotiation_module)
            from llm_controller.memory import DrivingMemory
            backend = chat_backend()
            env = create_and_reset(make_env, args.seed)

            def memory_factory():
                return DrivingMemory(
                    env,
                    embedding_backend=args.embedding_backend,
                    embedding_model=args.embedding_model,
                    embedding_endpoint=args.embedding_endpoint,
                    embedding_timeout=args.embedding_timeout,
                    persist_directory=str(database_path),
                )

            def count_records(memory):
                collection = memory.scenario_memory._collection
                return len(collection.get(include=["metadatas"])["ids"])

            try:
                result = run_memory_cycles(
                    env,
                    negotiation_factory=lambda current_env:
                        LlmAgent_negotiation_module(
                            current_env, chat_backend=backend),
                    action_factory=lambda current_env: LlmAgent_action_module(
                        current_env, chat_backend=backend, memory_mode="on"),
                    memory_factory=memory_factory,
                    count_records=count_records,
                    cycles=args.memory_cycles,
                )
                result["temporary_database_path"] = str(database_path)
            finally:
                env.close()

        result["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["formal_experiment"] = False
        result["success_rate_computed"] = False
        write_json(result_path, result)
        print(json.dumps(json_safe(result), indent=2, ensure_ascii=False))
        return 0
    except Exception as error:
        failure = {
            "probe": args.probe,
            "diagnostic_only": True,
            "formal_experiment": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }
        write_json(error_path, failure)
        raise


if __name__ == "__main__":
    sys.exit(main())
