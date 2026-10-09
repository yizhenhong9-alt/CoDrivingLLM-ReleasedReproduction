import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "743e563c8d540922db5a9cf5a3dc5d30d4ef0485"


def load_batch_runner():
    path = ROOT / "scripts" / "run_intersection_memory_off_batch.py"
    spec = importlib.util.spec_from_file_location(
        "run_intersection_memory_off_batch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def successful_summary(seed):
    return {
        "completion_status": "environment_terminated",
        "termination_reason": "all_controlled_vehicles_arrived",
        "total_steps": seed + 1,
        "total_reward": float(seed),
        "controlled_vehicle_arrival": [True, True, True, True],
        "controlled_vehicle_collision": [False, False, False, False],
    }


class ControlledBatchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_batch_runner()
        self.manifest_path = (
            ROOT / "experiments" / "intersection_memory_off_seeds.json")

    def test_manifest_has_exactly_twenty_unique_deterministic_seeds(self):
        first = self.runner.load_seed_manifest(self.manifest_path)
        second = self.runner.load_seed_manifest(self.manifest_path)
        self.assertEqual(first, second)
        self.assertEqual(first["seeds"], list(range(20)))
        self.assertEqual(len(first["seeds"]), 20)
        self.assertEqual(len(set(first["seeds"])), 20)
        self.assertEqual(first["classification"], "OUR EXPERIMENT DESIGN")
        self.assertIs(first["paper_seed_claim"], False)

    def test_each_seed_once_fresh_boundary_and_no_memory_import(self):
        manifest = self.runner.load_seed_manifest(self.manifest_path)
        calls = []

        def fake_executor(repository, trial_root, seed, config):
            calls.append((seed, trial_root))
            return successful_summary(seed), trial_root

        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "batch"
            batch.mkdir()
            records, summary = self.runner.run_batch(
                manifest, batch, ROOT, {}, execute_trial=fake_executor)

        self.assertEqual([seed for seed, _ in calls], list(range(20)))
        self.assertEqual(len({path for _, path in calls}), 20)
        self.assertEqual(len(records), 20)
        self.assertEqual(summary["attempted_trials"], 20)
        self.assertNotIn("llm_controller.memory", sys.modules)

    def test_failure_is_recorded_without_replacement_and_batch_continues(self):
        manifest = self.runner.load_seed_manifest(self.manifest_path)
        calls = []

        def fake_executor(repository, trial_root, seed, config):
            calls.append(seed)
            if seed == 7:
                raise RuntimeError("deliberate backend failure")
            return successful_summary(seed), trial_root

        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "batch"
            batch.mkdir()
            records, summary = self.runner.run_batch(
                manifest, batch, ROOT, {}, execute_trial=fake_executor)
            lines = (batch / "trials.jsonl").read_text(
                encoding="utf-8").splitlines()

        self.assertEqual(calls, list(range(20)))
        self.assertEqual(len(lines), 20)
        self.assertEqual(len(records), 20)
        failed = records[7]
        self.assertEqual(failed["seed"], 7)
        self.assertEqual(failed["status"], "failed")
        self.assertFalse(failed["derived_success"])
        self.assertIn("deliberate backend failure", failed["error_message"])
        self.assertIn("deliberate backend failure", failed["traceback"])
        self.assertEqual(summary["failed_trials"], 1)
        self.assertEqual(summary["successful_trials"], 19)

    def test_success_requires_termination_all_arrived_and_no_collision(self):
        valid = successful_summary(0)
        self.assertTrue(self.runner.classify_success(valid))

        cases = []
        max_steps = dict(valid, completion_status="max_steps_reached")
        cases.append(max_steps)
        not_arrived = dict(valid, controlled_vehicle_arrival=[True, False])
        cases.append(not_arrived)
        collision = dict(valid, controlled_vehicle_collision=[False, True])
        cases.append(collision)
        runtime = dict(valid, completion_status="runtime_error")
        cases.append(runtime)
        for case in cases:
            self.assertFalse(self.runner.classify_success(case))

    def test_summary_counts_and_both_denominators(self):
        records = [
            {"derived_success": True, "environment_completed": True,
             "status": "completed", "termination_reason": "arrived"},
            {"derived_success": False, "environment_completed": False,
             "status": "completed", "termination_reason": "max_steps"},
            {"derived_success": False, "environment_completed": False,
             "status": "failed", "termination_reason": "runtime_error"},
        ]
        summary = self.runner.build_summary(records, 3, 12.5)
        self.assertEqual(summary["planned_trials"], 3)
        self.assertEqual(summary["attempted_trials"], 3)
        self.assertEqual(summary["completed_trials"], 2)
        self.assertEqual(summary["environment_completed_trials"], 1)
        self.assertEqual(summary["failed_trials"], 1)
        self.assertEqual(summary["successful_trials"], 1)
        self.assertEqual(summary["unsuccessful_completed_trials"], 1)
        self.assertAlmostEqual(
            summary["success_rate_planned_denominator"]["value"], 1 / 3)
        self.assertAlmostEqual(
            summary["success_rate_environment_completed_denominator"][
                "value"], 1.0)

    def test_output_directory_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(
                    self.runner.uuid, "uuid4") as fake_uuid:
                fake_uuid.return_value.hex = "12345678abcdef"
                with mock.patch.object(
                        self.runner, "datetime") as fake_datetime:
                    fake_datetime.now.return_value.strftime.return_value = (
                        "20260101T000000000000Z")
                    first = self.runner.create_unique_directory(root, "batch")
                    marker = first / "preserve.txt"
                    marker.write_text("preserve", encoding="utf-8")
                    with self.assertRaises(FileExistsError):
                        self.runner.create_unique_directory(root, "batch")
                    self.assertEqual(marker.read_text(encoding="utf-8"),
                                     "preserve")

    def test_preflight_does_not_call_trial_executor(self):
        with mock.patch.object(
                self.runner, "default_trial_executor") as executor:
            result = self.runner.main([
                "--manifest", str(self.manifest_path),
                "--preflight",
                "--max-steps", "300",
            ])
        self.assertEqual(result, 0)
        executor.assert_not_called()

    def test_protected_sources_unchanged_from_stage_1d(self):
        protected = [
            "Run_multi_CAV_LLM.py", "llm_controller", "highway_env",
            "requirements.txt", "scripts/minimal_ollama_full_episode.py",
        ]
        completed = subprocess.run(
            ["git", "-c", "safe.directory={}".format(ROOT.as_posix()),
             "diff", "--exit-code", BASELINE_COMMIT, "--", *protected],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
