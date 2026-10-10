import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_helper():
    path = ROOT / "scripts" / "archive_stage1i_text_artifacts.py"
    spec = importlib.util.spec_from_file_location("stage1i_archive", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_formal_fixture(root):
    root.mkdir()
    records = []
    for seed in range(20):
        trial_name = "trial-{:02d}-seed-{}".format(seed, seed)
        run_name = "run-{:02d}".format(seed)
        trial_root = root / trial_name
        run_root = trial_root / run_name
        run_root.mkdir(parents=True)
        (trial_root / "runner_stdout.txt").write_bytes(
            "stdout {}\r\n".format(seed).encode("utf-8"))
        (trial_root / "runner_stderr.txt").write_bytes(
            "stderr {}\n".format(seed).encode("utf-8"))
        (run_root / "episode_summary.json").write_text(
            json.dumps({"seed": seed, "total_steps": seed + 1}), encoding="utf-8")
        (run_root / "run_metadata.json").write_text(
            json.dumps({"seed": seed, "memory_mode": "on"}), encoding="utf-8")
        (run_root / "steps.jsonl").write_text(
            json.dumps({"step_index": 0}) + "\n", encoding="utf-8")
        records.append({
            "trial_index": seed,
            "seed": seed,
            "trial_result_directory": "{}/{}".format(trial_name, run_name),
        })
    (root / "batch_metadata.json").write_text(
        json.dumps({"memory_mode": "on"}), encoding="utf-8")
    (root / "batch_summary.json").write_text(
        json.dumps({"attempted_trials": 20}), encoding="utf-8")
    (root / "trials.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8")
    database = root / "memory-db" / "intersection-multi-agent-v0"
    database.mkdir(parents=True)
    (database / "chroma.sqlite3").write_bytes(b"sqlite")
    (database / "index.bin").write_bytes(b"binary")
    (database / "state.pickle").write_bytes(b"pickle")


class Stage1IArtifactArchiveTests(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()

    def test_copies_exact_allowlist_byte_for_byte_and_excludes_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "formal"
            destination = root / "archive"
            build_formal_fixture(source)
            source_hashes = {
                path.relative_to(source): digest(path)
                for path in source.rglob("*") if path.is_file()
            }

            result = self.helper.archive(source, destination)

            self.assertEqual(result["file_count"], 103)
            self.assertEqual(result["extension_counts"], {
                ".json": 42, ".jsonl": 21, ".txt": 40})
            self.assertFalse(result["memory_db_copied"])
            self.assertFalse((destination / "memory-db").exists())
            copied = [path for path in destination.rglob("*") if path.is_file()]
            self.assertEqual(len(copied), 103)
            for path in copied:
                relative = path.relative_to(destination)
                self.assertEqual(digest(path), source_hashes[relative])
            self.assertEqual(
                source_hashes,
                {path.relative_to(source): digest(path)
                 for path in source.rglob("*") if path.is_file()})

    def test_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "formal"
            destination = root / "archive"
            build_formal_fixture(source)
            destination.mkdir()
            with self.assertRaises(FileExistsError):
                self.helper.archive(source, destination)

    def test_rejects_missing_required_artifact_and_wrong_seed_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "formal"
            build_formal_fixture(source)
            missing = next(source.glob("trial-00-seed-0/*/steps.jsonl"))
            missing.unlink()
            with self.assertRaises(FileNotFoundError):
                self.helper.selected_artifacts(source)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "formal"
            build_formal_fixture(source)
            trials = (source / "trials.jsonl").read_text(encoding="utf-8").splitlines()
            (source / "trials.jsonl").write_text(
                "\n".join([trials[1], trials[0], *trials[2:]]) + "\n",
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "indices"):
                self.helper.selected_artifacts(source)


if __name__ == "__main__":
    unittest.main()
