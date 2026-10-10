"""Released-style Intersection Memory-ON ordered batch orchestrator."""

import argparse
import json
import sys
from pathlib import Path

from scripts import run_intersection_memory_off_batch as batch_base


PROTOCOL_NAME = "released-style-intersection-memory-on"
PROTOCOL_VERSION = 1


def memory_database_path(batch_directory):
    database = (Path(batch_directory) / "memory-db" / "intersection-multi-agent-v0").resolve()
    if database.exists():
        raise FileExistsError(
            "Memory-ON batch requires a fresh absent database path: {}".format(database))
    return database


def trial_command(repository, trial_root, seed, config):
    return [
        sys.executable, "-m", "scripts.minimal_ollama_full_episode",
        "--backend", config["backend"], "--model", config["model"],
        "--endpoint", config["endpoint"], "--timeout", str(config["timeout_seconds"]),
        "--seed", str(seed), "--max-steps", str(config["max_steps_guard"]),
        "--output-dir", str(trial_root), "--memory-mode", "on",
        "--memory-db-path", str(config["memory_db_path"]),
        "--embedding-backend", config["embedding_backend"],
        "--embedding-model", config["embedding_model"],
        "--embedding-endpoint", config["embedding_endpoint"],
        "--embedding-timeout", str(config["embedding_timeout_seconds"]),
    ]


def default_trial_executor(repository, trial_root, seed, config):
    completed = batch_base.subprocess.run(
        trial_command(repository, trial_root, seed, config),
        cwd=str(repository), capture_output=True, text=True)
    (trial_root / "runner_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (trial_root / "runner_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    run_directories = sorted(path for path in trial_root.iterdir() if path.is_dir())
    if len(run_directories) != 1:
        raise RuntimeError("Single-episode runner produced {} result directories".format(len(run_directories)))
    run_directory = run_directories[0]
    summary_path = run_directory / "episode_summary.json"
    if not summary_path.exists():
        raise RuntimeError("Single-episode runner did not write a summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if completed.returncode != 0:
        raise batch_base.TrialExecutionError(
            "Single-episode runner exited with code {}".format(completed.returncode),
            summary=summary, run_directory=run_directory)
    return summary, run_directory


def parse_args(argv=None):
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run released-style Intersection Memory ON.")
    parser.add_argument("--manifest", default=str(repository / "experiments" / "intersection_memory_off_seeds.json"))
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--embedding-backend", default="ollama", choices=["ollama"])
    parser.add_argument("--embedding-model", default="nomic-embed-text:latest")
    parser.add_argument("--embedding-endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--embedding-timeout", type=float, default=120)
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--output-dir", default="runs/controlled-batches")
    parser.add_argument("--ollama-version", default="unavailable")
    parser.add_argument("--model-digest", default="unavailable")
    parser.add_argument("--embedding-model-digest", default="unavailable")
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args(argv)


def base_metadata(args, manifest, repository):
    result = {
        "experiment_protocol": PROTOCOL_NAME, "protocol_version": PROTOCOL_VERSION,
        "classification": "OUR EXPERIMENT DESIGN",
        "memory_definition": "Released-code-derived Memory ON",
        "scenario": "intersection-multi-agent-v0", "memory_mode": "on",
        "database_lifecycle": "fresh empty at batch start; persistent across policy cycles and ordered episode subprocesses; not cleared between seeds",
        "seed_order": manifest["seeds"], "backend": args.backend, "model": args.model,
        "model_substitution": True, "ollama_endpoint": args.endpoint,
        "ollama_version": args.ollama_version, "model_digest": args.model_digest,
        "embedding_backend": args.embedding_backend, "embedding_model": args.embedding_model,
        "embedding_endpoint": args.embedding_endpoint,
        "embedding_model_digest": args.embedding_model_digest,
        "timeout_seconds": args.timeout, "embedding_timeout_seconds": args.embedding_timeout,
        "max_steps_guard": args.max_steps,
        "seed_manifest_path": str(Path(args.manifest).resolve()),
        "seed_manifest_id": manifest["manifest_id"],
        "seed_manifest_version": manifest["schema_version"],
        "planned_trials": len(manifest["seeds"]),
    }
    result.update(batch_base.collect_git_metadata(repository))
    return result


def main(argv=None):
    args = parse_args(argv)
    if args.max_steps < 250:
        raise ValueError("max_steps must be at least 250 so Released duration termination can occur")
    repository = Path(__file__).resolve().parents[1]
    manifest = batch_base.load_seed_manifest(args.manifest)
    metadata = base_metadata(args, manifest, repository)
    if args.preflight:
        metadata["preflight_status"] = "ready"
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return 0
    batch_directory = batch_base.create_unique_directory(args.output_dir, PROTOCOL_NAME)
    database = memory_database_path(batch_directory)
    metadata.update({"memory_db_path": str(database), "execution_status": "running"})
    metadata_path = batch_directory / "batch_metadata.json"
    batch_base.write_json(metadata_path, metadata)
    config = {
        "backend": args.backend, "model": args.model, "endpoint": args.endpoint,
        "timeout_seconds": args.timeout, "max_steps_guard": args.max_steps,
        "memory_db_path": database, "embedding_backend": args.embedding_backend,
        "embedding_model": args.embedding_model, "embedding_endpoint": args.embedding_endpoint,
        "embedding_timeout_seconds": args.embedding_timeout,
    }
    try:
        records, summary = batch_base.run_batch(
            manifest, batch_directory, repository, config,
            execute_trial=default_trial_executor)
        metadata["execution_status"] = "complete_batch_attempt" if len(records) == 20 else "incomplete_batch_attempt"
        metadata["batch_summary"] = summary
        return 0 if len(records) == 20 else 1
    finally:
        batch_base.write_json(metadata_path, metadata)


if __name__ == "__main__":
    sys.exit(main())
