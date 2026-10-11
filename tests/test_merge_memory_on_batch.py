import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments" / "merge_memory_on_seeds.json"


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
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
    }


class MergeMemoryOnBatchTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_path(
            "run_merge_memory_on_batch_test",
            ROOT / "scripts" / "run_merge_memory_on_batch.py")

    def stage_root(self, parent):
        return Path(parent) / "stage1m_merge_memory_on_20seeds"

    def args(self, *extra):
        return ["--embedding-model", "nomic-embed-text:latest", *extra]

    def test_manifest_freezes_exact_on_contract(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        self.assertEqual(
            manifest["manifest_id"],
            "merge-memory-on-released-style-cumulative-v1")
        self.assertEqual(manifest["classification"], "OUR EXPERIMENT DESIGN")
        self.assertIs(manifest["paper_seed_claim"], False)
        self.assertEqual(manifest["scenario"], "merge-multi-agent-v0")
        self.assertEqual(manifest["memory_mode"], "on")
        self.assertEqual(manifest["seeds"], list(range(20)))
        self.assertEqual(len(set(manifest["seeds"])), 20)
        self.assertEqual(manifest["order"], "ascending")
        self.assertEqual(manifest["environment_config"], {
            "simulation_frequency": 20,
            "policy_frequency": 5,
            "duration": 40,
        })
        self.assertEqual(manifest["duration_boundary_policy_steps"], 200)
        self.assertEqual(manifest["effective_controlled_vehicles"], 3)
        self.assertEqual(manifest["expected_action_tuple_arity"], 3)
        self.assertIs(manifest["cumulative_memory_across_seeds"], True)
        self.assertIs(manifest["fresh_empty_db_at_batch_start"], True)
        self.assertIs(manifest["clear_db_between_seeds"], False)
        self.assertEqual(manifest["retry_policy"], "none")
        self.assertEqual(manifest["replacement_seed_policy"], "none")

    def test_manifest_rejects_wrong_scenario_mode_order_or_lifecycle(self):
        original = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for field, value in (
                ("scenario", "intersection-multi-agent-v0"),
                ("memory_mode", "off"),
                ("clear_db_between_seeds", True)):
            case = copy.deepcopy(original)
            case[field] = value
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "manifest.json"
                    path.write_text(json.dumps(case), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        self.runner.load_seed_manifest(path)
        reversed_case = copy.deepcopy(original)
        reversed_case["seeds"] = list(reversed(range(20)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(reversed_case), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.runner.load_seed_manifest(path)

    def test_formal_namespace_and_existing_db_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.stage_root(directory)
            batch, database = self.runner.planned_paths(root, "formal-v1")
            self.assertEqual(database, batch / "memory-db" / "merge-multi-agent-v0")
            self.assertFalse(database.exists())
            database.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                self.runner.planned_paths(root, "formal-v1")

    def test_batch_directories_are_distinct_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.stage_root(directory)
            first, first_db = self.runner.create_batch_directory(
                root, "formal-v1")
            second, second_db = self.runner.create_batch_directory(
                root, "formal-v2")
            self.assertNotEqual(first, second)
            self.assertNotEqual(first_db, second_db)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())
            self.assertFalse(first_db.exists())
            self.assertFalse(second_db.exists())
            with self.assertRaises(FileExistsError):
                self.runner.create_batch_directory(root, "formal-v1")

    def test_rejects_intersection_and_temporary_smoke_namespaces(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "end with"):
                self.runner.planned_paths(
                    Path(directory) / "intersection-memory", "formal-v1")
            root = self.stage_root(directory)
            with self.assertRaisesRegex(ValueError, "Intersection|temporary"):
                self.runner.planned_paths(root, "intersection-formal")
            with self.assertRaisesRegex(ValueError, "Intersection|temporary"):
                self.runner.planned_paths(root, "merge-preflight-memory-on")

    def test_preflight_has_no_files_db_backend_or_memory_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.stage_root(directory)
            argv = self.args(
                "--output-dir", str(root), "--batch-id", "formal-v1",
                "--preflight")
            with mock.patch.object(
                    self.runner.batch_base, "collect_git_metadata",
                    return_value={"git_commit": "abc", "branch": "test"}), \
                    mock.patch.object(
                        self.runner, "default_trial_executor") as executor, \
                    mock.patch.object(
                        self.runner.batch_base.subprocess, "run") as process:
                result = self.runner.main(argv)
            self.assertEqual(result, 0)
            self.assertFalse(root.exists())
            executor.assert_not_called()
            process.assert_not_called()
            self.assertNotIn("llm_controller.memory", sys.modules)

    def test_guard_and_required_embedding_configuration(self):
        with self.assertRaises(SystemExit):
            self.runner.parse_args(["--preflight"])
        with tempfile.TemporaryDirectory() as directory:
            root = self.stage_root(directory)
            with self.assertRaisesRegex(ValueError, "at least 200"):
                self.runner.main(self.args(
                    "--output-dir", str(root), "--max-steps", "199",
                    "--preflight"))
            with self.assertRaisesRegex(ValueError, "must be 250"):
                self.runner.main(self.args(
                    "--output-dir", str(root), "--max-steps", "200",
                    "--preflight"))

    def test_command_uses_same_db_for_ordered_fresh_subprocesses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.stage_root(directory)
            _, database = self.runner.planned_paths(root, "formal-v1")
            args = self.runner.parse_args(self.args("--output-dir", str(root)))
            config = self.runner.runtime_config(args, database)
            commands = [self.runner.trial_command(
                ROOT, Path(directory) / "trial-{:02d}".format(seed),
                seed, config) for seed in range(20)]
        self.assertEqual(
            [command[command.index("--seed") + 1] for command in commands],
            [str(seed) for seed in range(20)])
        self.assertEqual(
            {command[command.index("--memory-db-path") + 1]
             for command in commands}, {str(database)})
        for command in commands:
            self.assertEqual(command[0:3], [
                self.runner.sys.executable, "-m",
                "scripts.minimal_ollama_full_episode"])
            self.assertEqual(command[command.index("--scenario") + 1],
                             "merge-multi-agent-v0")
            self.assertEqual(command[command.index("--memory-mode") + 1], "on")
            self.assertEqual(command[command.index("--model") + 1], "qwen2.5:7b")
            self.assertEqual(
                command[command.index("--embedding-model") + 1],
                "nomic-embed-text:latest")

    def test_metadata_records_cumulative_lifecycle_and_no_rollback(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        args = self.runner.parse_args(self.args())
        database = Path("C:/evidence/memory-db/merge-multi-agent-v0")
        with mock.patch.object(
                self.runner.batch_base, "collect_git_metadata",
                return_value={"git_commit": "abc", "branch": "test"}):
            metadata = self.runner.base_metadata(args, manifest, ROOT, database)
        self.assertEqual(metadata["memory_mode"], "on")
        self.assertTrue(metadata["cumulative_memory_across_seeds"])
        self.assertFalse(metadata["clear_db_between_seeds"])
        self.assertEqual(metadata["memory_update_timing"], "pre-step")
        self.assertTrue(metadata["same_cycle_visibility"])
        self.assertIn("no rollback", metadata["partial_failed_cycle_writes"])
        self.assertEqual(metadata["memory_db_path"], str(database))
        self.assertEqual(metadata["expected_controlled_vehicles"], 3)
        self.assertEqual(metadata["expected_action_tuple_arity"], 3)
        self.assertEqual(metadata["max_steps_guard"], 250)

    def test_success_rule_is_identical_to_off_and_collision_wins(self):
        cases = [
            (completed_summary([True, True, True], [False, False, False]), True),
            (completed_summary([True, False, True], [False, False, False]), False),
            (completed_summary(
                [True, True, True], [False, True, False],
                "controlled_vehicle_collision"), False),
        ]
        for summary, expected in cases:
            with self.subTest(summary=summary):
                self.assertEqual(
                    self.runner.batch_base.classify_success(summary), expected)

    def test_failed_or_malformed_result_is_recorded_not_fabricated(self):
        manifest = self.runner.load_seed_manifest(MANIFEST)
        calls = []
        def execute(repository, trial_root, seed, config):
            calls.append(seed)
            if seed == 0:
                raise RuntimeError("missing result")
            if seed == 1:
                raise json.JSONDecodeError("malformed", "{", 1)
            result = trial_root / "result"
            result.mkdir()
            return completed_summary(
                [False, False, False], [False, False, False]), result
        with tempfile.TemporaryDirectory() as directory:
            records, summary = self.runner.batch_base.run_batch(
                manifest, Path(directory), ROOT, {}, execute_trial=execute)
        self.assertEqual(calls, list(range(20)))
        self.assertEqual(summary["failed_trials"], 2)
        self.assertEqual(records[0]["status"], "failed")
        self.assertIsNone(records[0]["total_steps"])
        self.assertEqual(records[1]["status"], "failed")

    def test_executor_preserves_stdout_stderr_on_bad_artifacts(self):
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=1, stdout="saved-out", stderr="saved-err")
        with tempfile.TemporaryDirectory() as directory:
            trial = Path(directory) / "trial"
            trial.mkdir()
            (trial / "result").mkdir()
            config = {
                "backend": "ollama", "model": "qwen2.5:7b",
                "endpoint": "http://127.0.0.1:11435",
                "timeout_seconds": 120, "max_steps_guard": 250,
                "memory_db_path": Path(directory) / "db",
                "embedding_backend": "ollama",
                "embedding_model": "nomic-embed-text:latest",
                "embedding_endpoint": "http://127.0.0.1:11435",
                "embedding_timeout_seconds": 120,
            }
            with mock.patch.object(
                    self.runner.batch_base.subprocess, "run",
                    return_value=completed):
                with self.assertRaisesRegex(RuntimeError, "did not write"):
                    self.runner.default_trial_executor(ROOT, trial, 0, config)
            self.assertEqual(
                (trial / "runner_stdout.txt").read_text(encoding="utf-8"),
                "saved-out")
            self.assertEqual(
                (trial / "runner_stderr.txt").read_text(encoding="utf-8"),
                "saved-err")

    def test_fake_merge_cycle_has_top_k_visibility_three_writes_one_step(self):
        episode = load_path(
            "full_episode_stage1m_test",
            ROOT / "scripts" / "minimal_ollama_full_episode.py")
        events = []
        class Vehicle:
            crashed = False
            on_road = True
            def __init__(self, name): self.name = name
        vehicles = [Vehicle("c0"), Vehicle("c1"), Vehicle("c2")]
        class Memory:
            def __init__(self): self.values = []
            def retrieveMemory(self, query, top_k=2):
                events.append(("retrieve", query, top_k, len(self.values)))
                return list(self.values[-top_k:])
            def addMemory(self, value):
                self.values.append(value); events.append(("write", value))
        memory = Memory()
        class Env:
            controlled_vehicles = vehicles
            config = {"duration": 40, "policy_frequency": 5,
                      "offroad_terminal": False}
            steps = 0
            vehicle = vehicles[0]
            def step(self, action, passed):
                events.append(("env.step", action)); self.steps += 1
                return SimpleNamespace(shape=(1,)), 1.0, True, {}
            def has_arrived(self, vehicle): return True
        class Negotiation:
            def llm_controller_run(self, env):
                events.append(("negotiation",)); return "n", []
        class Action:
            ACTIONS_ALL = {1: "IDLE"}
            def llm_controller_run(self, env, negotiation, conflicts,
                                   controlled, memory=None):
                actions = []
                for vehicle in controlled:
                    visible = memory.retrieveMemory(vehicle.name, top_k=2)
                    events.append(("decision", vehicle.name, len(visible)))
                    memory.addMemory(vehicle.name)
                    actions.append([1])
                return actions
        result = episode.run_episode(
            Env(), Negotiation, Action, 250,
            memory_factory=lambda: memory)
        self.assertEqual(result["total_steps"], 1)
        self.assertEqual(
            [event[3] for event in events if event[0] == "retrieve"],
            [0, 1, 2])
        self.assertEqual(
            [event[2] for event in events if event[0] == "retrieve"],
            [2, 2, 2])
        self.assertEqual(sum(event[0] == "write" for event in events), 3)
        self.assertEqual(sum(event[0] == "env.step" for event in events), 1)
        self.assertLess(
            max(index for index, event in enumerate(events)
                if event[0] == "write"),
            next(index for index, event in enumerate(events)
                 if event[0] == "env.step"))


if __name__ == "__main__":
    unittest.main()
