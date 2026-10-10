"""Copy only the audited Stage 1I text-artifact contract.

This helper never modifies the source. It validates the formal 20-trial
layout, copies a fixed 103-file allowlist byte-for-byte, excludes Chroma state,
and verifies every destination hash against its source.
"""

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


EXPECTED_SEEDS = list(range(20))
ROOT_FILES = ("batch_metadata.json", "batch_summary.json", "trials.jsonl")
TRIAL_ROOT_FILES = ("runner_stdout.txt", "runner_stderr.txt")
RUN_FILES = ("episode_summary.json", "run_metadata.json", "steps.jsonl")
EXPECTED_COUNTS = {".json": 42, ".jsonl": 21, ".txt": 40}
FORBIDDEN_SUFFIXES = {".bin", ".pickle", ".sqlite", ".sqlite3", ".db"}


def is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_trials(path):
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError("Blank trials.jsonl line {}".format(line_number))
            records.append(json.loads(line))
    if len(records) != 20:
        raise ValueError("Expected 20 trial records, found {}".format(len(records)))
    indices = [record.get("trial_index") for record in records]
    seeds = [record.get("seed") for record in records]
    if indices != EXPECTED_SEEDS:
        raise ValueError("Trial indices must be exactly ordered 0..19")
    if seeds != EXPECTED_SEEDS:
        raise ValueError("Seeds must be exactly ordered 0..19")
    return records


def selected_artifacts(source):
    source = Path(source).resolve()
    if not source.is_dir():
        raise FileNotFoundError("Stage 1I source directory does not exist: {}".format(source))

    selected = [source / name for name in ROOT_FILES]
    records = load_trials(source / "trials.jsonl")
    for index, record in enumerate(records):
        seed = record["seed"]
        expected_trial_root = "trial-{:02d}-seed-{}".format(index, seed)
        relative_result = Path(record.get("trial_result_directory", ""))
        if relative_result.is_absolute() or not relative_result.parts:
            raise ValueError("Invalid trial_result_directory for seed {}".format(seed))
        if relative_result.parts[0] != expected_trial_root:
            raise ValueError("Unexpected trial directory for seed {}: {}".format(seed, relative_result))
        result_directory = (source / relative_result).resolve()
        if not is_within(result_directory, source) or not result_directory.is_dir():
            raise ValueError("Trial result escapes or is missing: {}".format(relative_result))
        trial_root = source / expected_trial_root
        selected.extend(trial_root / name for name in TRIAL_ROOT_FILES)
        selected.extend(result_directory / name for name in RUN_FILES)

    missing = [path for path in selected if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required artifacts: {}".format(
            ", ".join(str(path.relative_to(source)) for path in missing)))
    relative = [path.relative_to(source) for path in selected]
    if len(relative) != 103 or len(set(relative)) != 103:
        raise ValueError("Artifact allowlist must contain 103 unique files")
    counts = Counter(path.suffix.lower() for path in relative)
    if dict(counts) != EXPECTED_COUNTS:
        raise ValueError("Unexpected extension counts: {}".format(dict(counts)))
    for path in relative:
        if "memory-db" in path.parts or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError("Forbidden database artifact selected: {}".format(path))
    return source, relative


def archive(source, destination):
    source, relative_paths = selected_artifacts(source)
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Archive destination already exists: {}".format(destination))
    if is_within(destination, source) or is_within(source, destination):
        raise ValueError("Source and destination must not contain one another")

    destination.mkdir(parents=True, exist_ok=False)
    copied = []
    try:
        for relative in relative_paths:
            source_file = source / relative
            destination_file = destination / relative
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source_file), str(destination_file))
            if sha256(source_file) != sha256(destination_file):
                raise RuntimeError("Hash mismatch after copy: {}".format(relative))
            copied.append(relative)
    except Exception:
        # Preserve partial output for diagnosis; never alter or delete source.
        raise

    actual = sorted(path.relative_to(destination) for path in destination.rglob("*") if path.is_file())
    if actual != sorted(relative_paths):
        raise RuntimeError("Destination contains missing or unexpected files")
    return {
        "status": "archive_copy_verified",
        "source": str(source),
        "destination": str(destination),
        "file_count": len(copied),
        "extension_counts": dict(sorted(Counter(path.suffix.lower() for path in copied).items())),
        "seed_order": EXPECTED_SEEDS,
        "memory_db_copied": False,
        "source_modified": False,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Archive only Stage 1I text artifacts")
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print(json.dumps(archive(args.source, args.destination), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
