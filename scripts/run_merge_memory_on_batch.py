"""Prepare/run the controlled Released-style Merge Memory-ON batch.

This thin orchestrator reuses the validated generic full-episode runner and
Stage 1H Memory path. It contains no controller, simulator, retrieval, prompt,
or Memory-update logic.
"""

import argparse
import json
import platform
import re
import sys
from pathlib import Path

from scripts import run_intersection_memory_off_batch as batch_base


PROTOCOL_NAME = "released-style-merge-memory-on"
PROTOCOL_VERSION = 1
SCENARIO = "merge-multi-agent-v0"
MANIFEST_ID = "merge-memory-on-released-style-cumulative-v1"
EXPECTED_SEEDS = list(range(20))
EXPECTED_CONFIG = {
    "simulation_frequency": 20,
    "policy_frequency": 5,
    "duration": 40,
}
EXPECTED_CONTROLLED_VEHICLES = 3
EXPECTED_ACTION_ARITY = 3
DURATION_BOUNDARY = 200
DEFAULT_BATCH_ID = "released-style-merge-memory-on-formal-v1"
SUCCESS_DEFINITION = (
    "completion_status == environment_terminated AND all "
    "controlled_vehicle_arrival values are true AND all "
    "controlled_vehicle_collision values are false"
)
DATABASE_LIFECYCLE = (
    "one fresh empty Merge-specific persistent DB at batch start; "
    "same absolute DB path across seeds 0..19; cumulative writes retained; "
    "not cleared between seeds; failed-trial partial pre-step writes retained"
)


def load_seed_manifest(path):
    manifest = batch_base.load_seed_manifest(path)
    requirements = {
        "manifest_id": MANIFEST_ID,
        "scenario": SCENARIO,
        "memory_mode": "on",
        "seed_count": 20,
        "unique": True,
        "order": "ascending",
        "effective_controlled_vehicles": EXPECTED_CONTROLLED_VEHICLES,
        "expected_action_tuple_arity": EXPECTED_ACTION_ARITY,
        "duration_boundary_policy_steps": DURATION_BOUNDARY,
        "cumulative_memory_across_seeds": True,
        "fresh_empty_db_at_batch_start": True,
        "clear_db_between_seeds": False,
        "retry_policy": "none",
        "replacement_seed_policy": "none",
    }
    for field, expected in requirements.items():
        if manifest.get(field) != expected:
            raise ValueError(
                "Unexpected Merge Memory-ON manifest {}: expected {!r}, "
                "got {!r}".format(field, expected, manifest.get(field)))
    if manifest["seeds"] != EXPECTED_SEEDS:
        raise ValueError("Merge Memory-ON seeds must be exactly 0..19 ascending")
    if manifest.get("environment_config") != EXPECTED_CONFIG:
        raise ValueError("Unexpected Merge Memory-ON environment configuration")
    success = manifest.get("success_metric", {})
    if success.get("definition") != SUCCESS_DEFINITION:
        raise ValueError("Unexpected Merge derived-success definition")
    if success.get("released_independent_metric") != "unavailable":
        raise ValueError("Released independent success must remain unavailable")
    return manifest


def validate_batch_id(batch_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", batch_id or ""):
        raise ValueError("batch-id must be one safe path component")
    lowered = batch_id.lower()
    if "intersection" in lowered or "merge-preflight-memory-on" in lowered:
        raise ValueError("batch-id must not name Intersection or temporary smoke data")
    return batch_id


def validate_output_root(output_root):
    resolved = Path(output_root).resolve()
    lowered = str(resolved).lower().replace("\\", "/")
    if resolved.name != "stage1m_merge_memory_on_20seeds":
        raise ValueError(
            "Formal output root must end with stage1m_merge_memory_on_20seeds")
    if "intersection" in lowered or "merge-preflight-memory-on" in lowered:
        raise ValueError("Formal output root must not use Intersection/smoke data")
    return resolved


def planned_paths(output_root, batch_id):
    root = validate_output_root(output_root)
    batch = root / validate_batch_id(batch_id)
    database = batch / "memory-db" / SCENARIO
    lowered = str(database).lower().replace("\\", "/")
    if "intersection-multi-agent-v0" in lowered:
        raise ValueError("Intersection database namespace is forbidden")
    if "merge-preflight-memory-on" in lowered:
        raise ValueError("Temporary Merge smoke database namespace is forbidden")
    if SCENARIO not in database.parts:
        raise ValueError("Formal database must use the Merge scenario namespace")
    if database.exists():
        raise FileExistsError(
            "Formal Memory-ON database path already exists: {}".format(database))
    return batch, database


def create_batch_directory(output_root, batch_id):
    batch, database = planned_paths(output_root, batch_id)
    if batch.exists():
        raise FileExistsError("Formal batch directory already exists: {}".format(batch))
    batch.parent.mkdir(parents=True, exist_ok=True)
    batch.mkdir(exist_ok=False)
    return batch, database


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
        "--memory-mode", "on",
        "--memory-db-path", str(config["memory_db_path"]),
        "--embedding-backend", config["embedding_backend"],
        "--embedding-model", config["embedding_model"],
        "--embedding-endpoint", config["embedding_endpoint"],
        "--embedding-timeout", str(config["embedding_timeout_seconds"]),
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
        description="Run Released-style cumulative Merge Memory ON.")
    parser.add_argument(
        "--manifest", default=str(
            repository / "experiments" / "merge_memory_on_seeds.json"))
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument(
        "--embedding-backend", default="ollama", choices=["ollama"])
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument(
        "--embedding-endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--embedding-timeout", type=float, default=120)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument(
        "--output-dir", default="runs/stage1m_merge_memory_on_20seeds")
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--ollama-version", default="unavailable")
    parser.add_argument("--model-digest", default="unavailable")
    parser.add_argument("--embedding-model-digest", default="unavailable")
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args(argv)


def base_metadata(args, manifest, repository, database):
    result = {
        "experiment_protocol": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "classification": "OUR EXPERIMENT DESIGN",
        "memory_definition": "Released-code-derived Memory ON",
        "scenario": SCENARIO,
        "memory_mode": "on",
        "database_lifecycle": DATABASE_LIFECYCLE,
        "cumulative_memory_across_seeds": True,
        "fresh_empty_db_at_batch_start": True,
        "clear_db_between_seeds": False,
        "partial_failed_cycle_writes": "retained; no rollback",
        "memory_update_timing": "pre-step",
        "same_cycle_visibility": True,
        "memory_db_path": str(database),
        "seed_order": list(manifest["seeds"]),
        "backend": args.backend,
        "model": args.model,
        "model_substitution": True,
        "ollama_endpoint": args.endpoint,
        "ollama_version": args.ollama_version,
        "model_digest": args.model_digest,
        "embedding_backend": args.embedding_backend,
        "embedding_model": args.embedding_model,
        "embedding_endpoint": args.embedding_endpoint,
        "embedding_model_digest": args.embedding_model_digest,
        "timeout_seconds": args.timeout,
        "embedding_timeout_seconds": args.embedding_timeout,
        "max_steps_guard": args.max_steps,
        "guard_classification": (
            "protective only; does not redefine Released termination"),
        "environment_config": dict(EXPECTED_CONFIG),
        "duration_boundary_policy_steps": DURATION_BOUNDARY,
        "expected_controlled_vehicles": EXPECTED_CONTROLLED_VEHICLES,
        "expected_action_tuple_arity": EXPECTED_ACTION_ARITY,
        "success_metric": manifest["success_metric"],
        "expected_completed_cycle_memory_writes": (
            "3 * sum(completed Memory-ON policy cycles); storage-only "
            "invariant; failed cycles may add partial pre-step writes"),
        "retry_policy": "none",
        "replacement_seed_policy": "none",
        "fresh_process_per_seed": True,
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


def runtime_config(args, database):
    return {
        "backend": args.backend,
        "model": args.model,
        "endpoint": args.endpoint,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
        "memory_db_path": database,
        "embedding_backend": args.embedding_backend,
        "embedding_model": args.embedding_model,
        "embedding_endpoint": args.embedding_endpoint,
        "embedding_timeout_seconds": args.embedding_timeout,
    }


def main(argv=None):
    args = parse_args(argv)
    if args.max_steps < DURATION_BOUNDARY:
        raise ValueError(
            "max_steps must be at least {} so Released Merge duration "
            "termination can occur".format(DURATION_BOUNDARY))
    if args.max_steps != 250:
        raise ValueError("Formal Merge Memory-ON max_steps must be 250")
    repository = Path(__file__).resolve().parents[1]
    manifest = load_seed_manifest(args.manifest)
    planned_batch, database = planned_paths(args.output_dir, args.batch_id)
    metadata = base_metadata(args, manifest, repository, database)
    metadata["batch_directory"] = str(planned_batch)
    if args.preflight:
        metadata["preflight_status"] = "ready_for_review"
        metadata["preflight_side_effects"] = (
            "none: no directory/DB/artifact creation, backend contact, "
            "DrivingMemory/Chroma initialization, reset, step, or episode")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return 0

    batch_directory, database = create_batch_directory(
        args.output_dir, args.batch_id)
    metadata["start_time_utc"] = batch_base.utc_now()
    metadata["end_time_utc"] = None
    metadata["execution_status"] = "running"
    metadata_path = batch_directory / "batch_metadata.json"
    batch_base.write_json(metadata_path, metadata)
    try:
        records, summary = batch_base.run_batch(
            manifest, batch_directory, repository,
            runtime_config(args, database),
            execute_trial=default_trial_executor)
        metadata["execution_status"] = (
            "complete_batch_attempt" if len(records) == 20
            else "incomplete_batch_attempt")
        metadata["batch_summary"] = summary
        return 0 if len(records) == 20 else 1
    finally:
        metadata["end_time_utc"] = batch_base.utc_now()
        batch_base.write_json(metadata_path, metadata)


if __name__ == "__main__":
    sys.exit(main())
