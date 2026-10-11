"""Controlled 20-seed Merge Memory-OFF batch orchestration only.

This is OUR EXPERIMENT DESIGN. Each manifest seed is delegated exactly once
to the validated single-episode runner in a fresh Python process. No
CoDrivingLLM controller, simulator, or Memory semantics are implemented here.
"""

import argparse
import json
import platform
import sys
from pathlib import Path

from scripts import run_intersection_memory_off_batch as batch_base


PROTOCOL_NAME = "controlled-merge-memory-off"
PROTOCOL_VERSION = 1
SCENARIO = "merge-multi-agent-v0"
EXPECTED_SEEDS = list(range(20))
EXPECTED_CONFIG = {
    "simulation_frequency": 20,
    "policy_frequency": 5,
    "duration": 40,
}
EXPECTED_CONTROLLED_VEHICLES = 3
EXPECTED_ACTION_ARITY = 3
DURATION_BOUNDARY = 200


def load_seed_manifest(path):
    manifest = batch_base.load_seed_manifest(path)
    requirements = {
        "manifest_id": "merge-memory-off-controlled-v1",
        "scenario": SCENARIO,
        "memory_mode": "off",
        "seed_count": 20,
        "unique": True,
        "order": "ascending",
        "effective_controlled_vehicles": EXPECTED_CONTROLLED_VEHICLES,
        "expected_action_tuple_arity": EXPECTED_ACTION_ARITY,
        "duration_boundary_policy_steps": DURATION_BOUNDARY,
        "retry_policy": "none",
        "replacement_seed_policy": "none",
    }
    for field, expected in requirements.items():
        if manifest.get(field) != expected:
            raise ValueError(
                "Unexpected Merge manifest {}: expected {!r}, got {!r}"
                .format(field, expected, manifest.get(field)))
    if manifest["seeds"] != EXPECTED_SEEDS:
        raise ValueError("Merge seeds must be exactly 0..19 in ascending order")
    if manifest.get("environment_config") != EXPECTED_CONFIG:
        raise ValueError("Unexpected Merge environment configuration")
    success = manifest.get("success_metric", {})
    if success.get("definition") != (
            "completion_status == environment_terminated AND all "
            "controlled_vehicle_arrival values are true AND all "
            "controlled_vehicle_collision values are false"):
        raise ValueError("Unexpected Merge derived-success definition")
    if success.get("released_independent_metric") != "unavailable":
        raise ValueError("Released independent success must remain unavailable")
    return manifest


def trial_command(repository, trial_root, seed, config):
    return [
        sys.executable, "-m", "scripts.minimal_ollama_full_episode",
        "--scenario", SCENARIO,
        "--backend", config["backend"],
        "--model", config["model"],
        "--endpoint", config["endpoint"],
        "--timeout", str(config["timeout_seconds"]),
        "--seed", str(seed),
        "--max-steps", str(config["max_steps_guard"]),
        "--memory-mode", "off",
        "--output-dir", str(trial_root),
    ]


def default_trial_executor(repository, trial_root, seed, config):
    completed = batch_base.subprocess.run(
        trial_command(repository, trial_root, seed, config),
        cwd=str(repository), capture_output=True, text=True)
    (trial_root / "runner_stdout.txt").write_text(
        completed.stdout, encoding="utf-8")
    (trial_root / "runner_stderr.txt").write_text(
        completed.stderr, encoding="utf-8")
    run_directories = sorted(
        path for path in trial_root.iterdir() if path.is_dir())
    if len(run_directories) != 1:
        raise RuntimeError(
            "Single-episode runner produced {} result directories"
            .format(len(run_directories)))
    run_directory = run_directories[0]
    summary_path = run_directory / "episode_summary.json"
    if not summary_path.exists():
        raise RuntimeError("Single-episode runner did not write a summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if completed.returncode != 0:
        raise batch_base.TrialExecutionError(
            "Single-episode runner exited with code {}".format(
                completed.returncode),
            summary=summary, run_directory=run_directory)
    return summary, run_directory


def parse_args(argv=None):
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the controlled Merge Memory-OFF batch.")
    parser.add_argument(
        "--manifest", default=str(
            repository / "experiments" / "merge_memory_off_seeds.json"))
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument(
        "--output-dir", default="runs/stage1l_merge_memory_off_20seeds")
    parser.add_argument("--ollama-version", default="unavailable")
    parser.add_argument("--model-digest", default="unavailable")
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args(argv)


def base_metadata(args, manifest, repository):
    result = {
        "experiment_protocol": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "classification": "OUR EXPERIMENT DESIGN",
        "scenario": SCENARIO,
        "memory_mode": "off",
        "backend": args.backend,
        "model": args.model,
        "model_substitution": True,
        "ollama_endpoint": args.endpoint,
        "ollama_version": args.ollama_version,
        "model_digest": args.model_digest,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
        "guard_classification": (
            "protective only; does not redefine Released termination"),
        "environment_config": dict(EXPECTED_CONFIG),
        "duration_boundary_policy_steps": DURATION_BOUNDARY,
        "expected_controlled_vehicles": EXPECTED_CONTROLLED_VEHICLES,
        "expected_action_tuple_arity": EXPECTED_ACTION_ARITY,
        "success_metric": manifest["success_metric"],
        "retry_policy": "none",
        "replacement_seed_policy": "none",
        "fresh_process_per_seed": True,
        "seed_order": list(manifest["seeds"]),
        "seed_manifest_path": str(Path(args.manifest).resolve()),
        "seed_manifest_id": manifest["manifest_id"],
        "seed_manifest_version": manifest["schema_version"],
        "planned_trials": len(manifest["seeds"]),
        "python_version": platform.python_version(),
        "packages": {
            "gym": batch_base.package_version("gym"),
            "numpy": batch_base.package_version("numpy"),
            "pandas": batch_base.package_version("pandas"),
            "highway_env": "repository-local",
        },
    }
    result.update(batch_base.collect_git_metadata(repository))
    return result


def main(argv=None):
    args = parse_args(argv)
    if args.max_steps < DURATION_BOUNDARY:
        raise ValueError(
            "max_steps must be at least {} so Released Merge duration "
            "termination can occur".format(DURATION_BOUNDARY))
    repository = Path(__file__).resolve().parents[1]
    manifest = load_seed_manifest(args.manifest)
    metadata_record = base_metadata(args, manifest, repository)
    if args.preflight:
        metadata_record["preflight_status"] = "ready"
        print(json.dumps(metadata_record, indent=2, ensure_ascii=False))
        return 0

    batch_directory = batch_base.create_unique_directory(
        args.output_dir, PROTOCOL_NAME)
    metadata_record["start_time_utc"] = batch_base.utc_now()
    metadata_record["end_time_utc"] = None
    metadata_record["execution_status"] = "running"
    metadata_path = batch_directory / "batch_metadata.json"
    batch_base.write_json(metadata_path, metadata_record)
    config = {
        "backend": args.backend,
        "model": args.model,
        "endpoint": args.endpoint,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
    }
    try:
        records, summary = batch_base.run_batch(
            manifest, batch_directory, repository, config,
            execute_trial=default_trial_executor)
        metadata_record["execution_status"] = (
            "complete_batch_attempt" if len(records) == 20
            else "incomplete_batch_attempt")
        metadata_record["batch_summary"] = summary
        return 0 if len(records) == 20 else 1
    finally:
        metadata_record["end_time_utc"] = batch_base.utc_now()
        batch_base.write_json(metadata_path, metadata_record)


if __name__ == "__main__":
    sys.exit(main())
