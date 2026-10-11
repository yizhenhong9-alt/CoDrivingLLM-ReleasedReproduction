import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments" / "merge_memory_off_seeds.json"


def load_runner():
    path = ROOT / "scripts" / "run_merge_memory_off_batch.py"
    spec = importlib.util.spec_from_file_location(
        "run_merge_memory_off_batch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed_summary(arrivals, collisions, reason="released_duration_limit"):
    return {
        "completion_status": "environment_terminated",
        "termination_reason": reason,
        "total_steps": 200,
        "total_reward": 1.0,
        "controlled_vehicle_arrival": arrivals,
        "controlled_vehicle_collision": collisions,
        "success": {
            "value": None,
            "status": "unavailable",
        },
    }


class MergeMemoryOffBatchTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner()

    def test_manifest_freezes_exact_merge_contract(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        self.assertEqual(manifest["scenario"], self.runner.SCENARIO)
        self.assertEqual(manifest["memory_mode"], "off")
        self.assertEqual(manifest["seeds"], list(range(20)))
        self.assertEqual(len(set(manifest["seeds"])), 20)
        self.assertIs(manifest["unique"], True)
        self.assertEqual(manifest["order"], "ascending")
        self.assertIs(manifest["paper_seed_claim"], False)
        self.assertEqual(
            manifest["environment_config"], self.runner.EXPECTED_CONFIG)
        self.assertEqual(manifest["effective_controlled_vehicles"], 3)
        self.assertEqual(manifest["expected_action_tuple_arity"], 3)
        self.assertEqual(manifest["duration_boundary_policy_steps"], 200)
        self.assertEqual(manifest["retry_policy"], "none")
        self.assertEqual(manifest["replacement_seed_policy"], "none")

    def test_manifest_rejects_wrong_order_scenario_or_topology(self):
        original = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cases = []
        wrong_order = copy.deepcopy(original)
        wrong_order["seeds"] = list(reversed(range(20)))
        cases.append(wrong_order)
        wrong_scenario = copy.deepcopy(original)
        wrong_scenario["scenario"] = "intersection-multi-agent-v0"
        cases.append(wrong_scenario)
        wrong_topology = copy.deepcopy(original)
        wrong_topology["effective_controlled_vehicles"] = 4
        cases.append(wrong_topology)
        wrong_memory = copy.deepcopy(original)
        wrong_memory["memory_mode"] = "on"
        cases.append(wrong_memory)

        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "manifest.json"
                    path.write_text(json.dumps(case), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        self.runner.load_seed_manifest(path)

    def test_trial_command_is_merge_off_and_contains_no_memory_backend(self):
        config = {
            "backend": "ollama",
            "model": "qwen2.5:7b",
            "endpoint": "http://127.0.0.1:11435",
            "timeout_seconds": 120,
            "max_steps_guard": 250,
        }
        command = self.runner.trial_command(
            ROOT, Path("trial"), 7, config)
        self.assertEqual(command[0:3], [
            self.runner.sys.executable, "-m",
            "scripts.minimal_ollama_full_episode"])
        self.assertEqual(command[command.index("--scenario") + 1],
                         "merge-multi-agent-v0")
        self.assertEqual(command[command.index("--memory-mode") + 1], "off")
        self.assertEqual(command[command.index("--seed") + 1], "7")
        self.assertEqual(command[command.index("--max-steps") + 1], "250")
        joined = " ".join(command).lower()
        self.assertNotIn("drivingmemory", joined)
        self.assertNotIn("embedding", joined)
        self.assertNotIn("memory-db", joined)

    def test_guard_rejects_below_200_without_executing(self):
        with mock.patch.object(
                self.runner, "default_trial_executor") as executor:
            with self.assertRaisesRegex(ValueError, "at least 200"):
                self.runner.main(["--max-steps", "199", "--preflight"])
        executor.assert_not_called()

    def test_preflight_metadata_is_merge_specific_and_does_not_execute(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        args = self.runner.parse_args(["--preflight"])
        with mock.patch.object(
                self.runner.batch_base, "collect_git_metadata",
                return_value={"git_commit": "abc", "branch": "test"}):
            metadata = self.runner.base_metadata(args, manifest, ROOT)
        self.assertEqual(metadata["scenario"], "merge-multi-agent-v0")
        self.assertEqual(metadata["memory_mode"], "off")
        self.assertEqual(metadata["environment_config"], {
            "simulation_frequency": 20,
            "policy_frequency": 5,
            "duration": 40,
        })
        self.assertEqual(metadata["duration_boundary_policy_steps"], 200)
        self.assertEqual(metadata["expected_controlled_vehicles"], 3)
        self.assertEqual(metadata["expected_action_tuple_arity"], 3)
        self.assertEqual(metadata["seed_order"], list(range(20)))
        self.assertEqual(metadata["retry_policy"], "none")

        with mock.patch.object(
                self.runner, "default_trial_executor") as executor:
            result = self.runner.main(["--preflight"])
        self.assertEqual(result, 0)
        executor.assert_not_called()

    def test_batch_attempts_each_seed_once_and_preserves_failures(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        calls = []

        def execute(repository, trial_root, seed, config):
            calls.append(seed)
            if seed == 3:
                raise RuntimeError("process failed")
            if seed == 4:
                raise json.JSONDecodeError("malformed", "{", 1)
            if seed == 0:
                summary = completed_summary(
                    [True, True, True], [False, False, False])
            elif seed == 1:
                summary = completed_summary(
                    [True, True, True], [False, True, False],
                    reason="controlled_vehicle_collision")
            else:
                summary = completed_summary(
                    [True, False, True], [False, False, False])
            result = trial_root / "result"
            result.mkdir()
            return summary, result

        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory)
            records, summary = self.runner.batch_base.run_batch(
                manifest, batch, ROOT, {}, execute_trial=execute)
            persisted = [json.loads(line) for line in
                         (batch / "trials.jsonl").read_text(
                             encoding="utf-8").splitlines()]

        self.assertEqual(calls, list(range(20)))
        self.assertEqual(len(records), 20)
        self.assertEqual(len(persisted), 20)
        self.assertEqual(summary["attempted_trials"], 20)
        self.assertEqual(summary["failed_trials"], 2)
        self.assertEqual(summary["successful_trials"], 1)
        self.assertTrue(records[0]["derived_success"])
        self.assertFalse(records[1]["derived_success"])
        self.assertFalse(records[2]["derived_success"])
        self.assertEqual(records[3]["status"], "failed")
        self.assertEqual(records[4]["status"], "failed")
        self.assertIsNone(records[3]["total_steps"])
        self.assertIsNone(records[4]["total_reward"])

    def test_executor_preserves_stdout_stderr_and_rejects_bad_artifacts(self):
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="out", stderr="err")
        config = {
            "backend": "ollama", "model": "qwen2.5:7b",
            "endpoint": "http://127.0.0.1:11435",
            "timeout_seconds": 120, "max_steps_guard": 250,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trial = root / "missing"
            trial.mkdir()
            (trial / "result").mkdir()
            with mock.patch.object(
                    self.runner.batch_base.subprocess, "run",
                    return_value=completed):
                with self.assertRaisesRegex(RuntimeError, "did not write"):
                    self.runner.default_trial_executor(
                        ROOT, trial, 0, config)
            self.assertEqual(
                (trial / "runner_stdout.txt").read_text(encoding="utf-8"),
                "out")
            self.assertEqual(
                (trial / "runner_stderr.txt").read_text(encoding="utf-8"),
                "err")

            malformed = root / "malformed"
            malformed.mkdir()
            result = malformed / "result"
            result.mkdir()
            (result / "episode_summary.json").write_text(
                "{", encoding="utf-8")
            with mock.patch.object(
                    self.runner.batch_base.subprocess, "run",
                    return_value=completed):
                with self.assertRaises(json.JSONDecodeError):
                    self.runner.default_trial_executor(
                        ROOT, malformed, 1, config)

    def test_unique_batch_and_trial_directories_do_not_overwrite(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.runner.batch_base.create_unique_directory(
                root, self.runner.PROTOCOL_NAME)
            marker = first / "preserve.txt"
            marker.write_text("preserve", encoding="utf-8")
            self.assertTrue(marker.exists())

            seen = []

            def execute(repository, trial_root, seed, config):
                seen.append(trial_root.name)
                result = trial_root / "result"
                result.mkdir()
                return completed_summary(
                    [False, False, False], [False, False, False]), result

            second = self.runner.batch_base.create_unique_directory(
                root, self.runner.PROTOCOL_NAME)
            self.runner.batch_base.run_batch(
                manifest, second, ROOT, {}, execute_trial=execute)
            self.assertEqual(len(seen), 20)
            self.assertEqual(len(set(seen)), 20)
            self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
