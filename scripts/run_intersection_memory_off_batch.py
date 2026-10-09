"""Controlled 20-seed Intersection Memory-OFF batch orchestrator.

This is OUR EXPERIMENT DESIGN.  It delegates every trial to the existing
single-episode runner in a fresh Python process and contains no CoDrivingLLM
decision logic.
"""

import argparse
import json
import platform
import subprocess
import sys
import time
import traceback
import uuid
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


PROTOCOL_NAME = "controlled-intersection-memory-off"
PROTOCOL_VERSION = 1
EXPECTED_MANIFEST_SCHEMA = "codrivingllm.seed-manifest"
EXPECTED_MANIFEST_VERSION = 1


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def load_seed_manifest(path):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema") != EXPECTED_MANIFEST_SCHEMA:
        raise ValueError("Unexpected seed manifest schema")
    if manifest.get("schema_version") != EXPECTED_MANIFEST_VERSION:
        raise ValueError("Unexpected seed manifest version")
    if manifest.get("classification") != "OUR EXPERIMENT DESIGN":
        raise ValueError("Seed manifest must identify OUR EXPERIMENT DESIGN")
    if manifest.get("paper_seed_claim") is not False:
        raise ValueError("Seed manifest must not claim author-provided seeds")
    seeds = manifest.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != 20:
        raise ValueError("Seed manifest must contain exactly 20 seeds")
    if any(isinstance(seed, bool) or not isinstance(seed, int)
           for seed in seeds):
        raise ValueError("Every seed must be an integer")
    if len(set(seeds)) != len(seeds):
        raise ValueError("Every seed must be unique")
    return manifest


def create_unique_directory(output_root, prefix):
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    identifier = "{}_{}_{}".format(
        prefix,
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        uuid.uuid4().hex[:8],
    )
    directory = root / identifier
    directory.mkdir(exist_ok=False)
    return directory


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def git_command(repository, *arguments):
    return subprocess.check_output(
        ["git", "-c", "safe.directory={}".format(repository.as_posix()),
         *arguments],
        cwd=str(repository), text=True, encoding="utf-8").strip()


def collect_git_metadata(repository):
    result = {}
    for field, arguments in {
            "git_commit": ("rev-parse", "HEAD"),
            "branch": ("branch", "--show-current")}.items():
        try:
            result[field] = git_command(repository, *arguments)
        except Exception as error:
            result[field] = {
                "status": "unavailable",
                "value": None,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
    try:
        result["git_dirty"] = bool(
            git_command(repository, "status", "--porcelain"))
    except Exception as error:
        result["git_dirty"] = {
            "status": "unavailable",
            "value": None,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    return result


def classify_success(summary):
    if summary.get("completion_status") != "environment_terminated":
        return False
    arrivals = summary.get("controlled_vehicle_arrival")
    collisions = summary.get("controlled_vehicle_collision")
    return (
        isinstance(arrivals, list)
        and bool(arrivals)
        and all(value is True for value in arrivals)
        and isinstance(collisions, list)
        and len(collisions) == len(arrivals)
        and all(value is False for value in collisions)
    )


def default_trial_executor(repository, trial_root, seed, config):
    command = [
        sys.executable, "-m", "scripts.minimal_ollama_full_episode",
        "--backend", config["backend"],
        "--model", config["model"],
        "--endpoint", config["endpoint"],
        "--timeout", str(config["timeout_seconds"]),
        "--seed", str(seed),
        "--max-steps", str(config["max_steps_guard"]),
        "--output-dir", str(trial_root),
    ]
    completed = subprocess.run(
        command, cwd=str(repository), capture_output=True, text=True)
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
        raise TrialExecutionError(
            "Single-episode runner exited with code {}".format(
                completed.returncode),
            summary=summary,
            run_directory=run_directory,
        )
    return summary, run_directory


class TrialExecutionError(RuntimeError):
    def __init__(self, message, summary=None, run_directory=None):
        super().__init__(message)
        self.summary = summary or {}
        self.run_directory = run_directory


def trial_record(index, seed, summary, relative_directory,
                 wall_clock_seconds, error=None, error_traceback=None):
    environment_completed = (
        summary.get("completion_status") == "environment_terminated")
    record = {
        "trial_index": index,
        "seed": seed,
        "status": "failed" if error is not None else "completed",
        "completion_status": summary.get(
            "completion_status", "runtime_error"),
        "termination_reason": summary.get(
            "termination_reason", "runtime_error"),
        "total_steps": summary.get("total_steps"),
        "total_reward": summary.get("total_reward"),
        "derived_success": classify_success(summary),
        "controlled_vehicle_collision": summary.get(
            "controlled_vehicle_collision", "unavailable"),
        "controlled_vehicle_arrival": summary.get(
            "controlled_vehicle_arrival", "unavailable"),
        "environment_completed": environment_completed,
        "wall_clock_seconds": wall_clock_seconds,
        "trial_result_directory": relative_directory,
        "error_type": None,
        "error_message": None,
    }
    if error is not None:
        record["error_type"] = type(error).__name__
        record["error_message"] = str(error)
        record["traceback"] = error_traceback
    return record


def build_summary(records, planned_trials, wall_clock_seconds):
    successful = sum(record["derived_success"] for record in records)
    completed_records = [
        record for record in records if record["status"] == "completed"]
    environment_completed_records = [
        record for record in records if record["environment_completed"]]
    unsuccessful_completed = sum(
        not record["derived_success"] for record in completed_records)
    planned_rate = successful / planned_trials if planned_trials else None
    completed_rate = (
        successful / len(environment_completed_records)
        if environment_completed_records else None)
    return {
        "planned_trials": planned_trials,
        "attempted_trials": len(records),
        "completed_trials": len(completed_records),
        "environment_completed_trials": len(environment_completed_records),
        "failed_trials": sum(
            record["status"] == "failed" for record in records),
        "successful_trials": successful,
        "unsuccessful_completed_trials": unsuccessful_completed,
        "success_rate_planned_denominator": {
            "definition": "successful trials / all manifest-planned trials",
            "value": planned_rate,
        },
        "success_rate_environment_completed_denominator": {
            "definition": "successful trials / trials with completion_status=environment_terminated",
            "value": completed_rate,
        },
        "paper_failure_denominator_equivalence": "unresolved",
        "termination_reason_counts": dict(Counter(
            record["termination_reason"] for record in records)),
        "total_wall_clock_seconds": wall_clock_seconds,
    }


def run_batch(manifest, batch_directory, repository, config,
              execute_trial=default_trial_executor, clock=time.perf_counter):
    trials_path = batch_directory / "trials.jsonl"
    records = []
    batch_started = clock()
    for index, seed in enumerate(manifest["seeds"]):
        trial_started = clock()
        trial_root = batch_directory / "trial-{:02d}-seed-{}".format(
            index, seed)
        trial_root.mkdir(exist_ok=False)
        summary = {}
        run_directory = trial_root
        error = None
        error_traceback = None
        try:
            summary, run_directory = execute_trial(
                repository, trial_root, seed, config)
        except Exception as caught:
            error = caught
            error_traceback = traceback.format_exc()
            summary = getattr(caught, "summary", {})
            run_directory = getattr(caught, "run_directory", None) or trial_root
        relative_directory = str(
            run_directory.relative_to(batch_directory)).replace("\\", "/")
        record = trial_record(
            index, seed, summary, relative_directory,
            clock() - trial_started, error=error,
            error_traceback=error_traceback)
        append_jsonl(trials_path, record)
        records.append(record)
    summary = build_summary(
        records, len(manifest["seeds"]), clock() - batch_started)
    write_json(batch_directory / "batch_summary.json", summary)
    return records, summary


def parse_args(argv=None):
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the controlled Intersection Memory-OFF batch.")
    parser.add_argument(
        "--manifest",
        default=str(repository / "experiments" /
                    "intersection_memory_off_seeds.json"))
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--output-dir", default="runs/controlled-batches")
    parser.add_argument("--ollama-version", default="unavailable")
    parser.add_argument("--model-digest", default="unavailable")
    parser.add_argument(
        "--preflight", action="store_true",
        help="Validate and print the protocol without running trials.")
    return parser.parse_args(argv)


def base_metadata(args, manifest, repository):
    result = {
        "experiment_protocol": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "classification": "OUR EXPERIMENT DESIGN",
        "scenario": "intersection-multi-agent-v0",
        "memory_mode": "off",
        "backend": args.backend,
        "model": args.model,
        "model_substitution": True,
        "ollama_endpoint": args.endpoint,
        "ollama_version": args.ollama_version,
        "model_digest": args.model_digest,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
        "seed_manifest_path": str(Path(args.manifest).resolve()),
        "seed_manifest_id": manifest["manifest_id"],
        "seed_manifest_version": manifest["schema_version"],
        "planned_trials": len(manifest["seeds"]),
        "python_version": platform.python_version(),
        "packages": {
            "gym": package_version("gym"),
            "numpy": package_version("numpy"),
            "pandas": package_version("pandas"),
            "highway_env": "repository-local",
        },
    }
    result.update(collect_git_metadata(repository))
    return result


def main(argv=None):
    args = parse_args(argv)
    if args.max_steps < 250:
        raise ValueError(
            "max_steps must be at least 250 so the Released duration "
            "termination can occur")
    repository = Path(__file__).resolve().parents[1]
    manifest = load_seed_manifest(args.manifest)
    metadata_record = base_metadata(args, manifest, repository)
    if args.preflight:
        metadata_record["preflight_status"] = "ready"
        print(json.dumps(metadata_record, indent=2, ensure_ascii=False))
        return 0

    batch_directory = create_unique_directory(
        args.output_dir, PROTOCOL_NAME)
    metadata_record["start_time_utc"] = utc_now()
    metadata_record["end_time_utc"] = None
    metadata_record["execution_status"] = "running"
    metadata_path = batch_directory / "batch_metadata.json"
    write_json(metadata_path, metadata_record)
    config = {
        "backend": args.backend,
        "model": args.model,
        "endpoint": args.endpoint,
        "timeout_seconds": args.timeout,
        "max_steps_guard": args.max_steps,
    }
    try:
        records, summary = run_batch(
            manifest, batch_directory, repository, config)
        metadata_record["execution_status"] = (
            "complete_batch_attempt" if len(records) == 20
            else "incomplete_batch_attempt")
        metadata_record["batch_summary"] = summary
        return 0 if len(records) == 20 else 1
    finally:
        metadata_record["end_time_utc"] = utc_now()
        write_json(metadata_path, metadata_record)


if __name__ == "__main__":
    sys.exit(main())
