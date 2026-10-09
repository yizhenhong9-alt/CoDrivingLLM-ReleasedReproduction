import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "be89080b5f8e26dcb7ad0b887a0e3113730061cd"


def load_runner():
    path = ROOT / "scripts" / "minimal_ollama_full_episode.py"
    spec = importlib.util.spec_from_file_location(
        "minimal_ollama_full_episode", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVehicle:
    crashed = False
    on_road = True


class FakeEnv:
    def __init__(self, terminate_at=None):
        self.controlled_vehicles = [FakeVehicle(), FakeVehicle()]
        self.vehicle = self.controlled_vehicles[0]
        self.config = {
            "duration": 50,
            "policy_frequency": 5,
            "offroad_terminal": False,
        }
        self.steps = 0
        self.step_calls = []
        self.terminate_at = terminate_at
        self.arrived = False

    def step(self, action, passed_env):
        self.step_calls.append((action, passed_env))
        self.steps += 1
        terminated = self.steps == self.terminate_at
        if terminated:
            self.arrived = True
        return np.zeros((2, 2)), np.float32(1.5), terminated, {
            "counter": np.int32(self.steps),
        }

    def has_arrived(self, vehicle):
        return self.arrived


class FakeNegotiationAgent:
    def __init__(self, events, error=None):
        self.events = events
        self.error = error

    def llm_controller_run(self, env):
        self.events.append("negotiation")
        if self.error is not None:
            raise self.error
        return "negotiation", ["conflict"]


class FakeActionAgent:
    ACTIONS_ALL = {1: "IDLE", 3: "FASTER", 4: "SLOWER"}

    def __init__(self, events, actions=None, error=None):
        self.events = events
        self.actions = actions or [[np.int32(4)], [np.int32(1)]]
        self.error = error

    def llm_controller_run(self, env, negotiation_prompt, conflicting_info,
                           controlled_vehicles, memory):
        self.events.append(("decision", memory))
        if self.error is not None:
            raise self.error
        return self.actions


def run_fake(runner, env, max_steps, events, action_error=None,
             actions=None, records=None):
    tick = iter(float(index) for index in range(1000))
    return runner.run_episode(
        env,
        negotiation_agent_factory=lambda: FakeNegotiationAgent(events),
        action_agent_factory=lambda: FakeActionAgent(
            events, actions=actions, error=action_error),
        max_steps=max_steps,
        record_step=None if records is None else records.append,
        clock=lambda: next(tick),
    )


class FullEpisodeRunnerTests(unittest.TestCase):
    def test_order_one_step_per_cycle_joint_action_and_memory_off(self):
        runner = load_runner()
        env = FakeEnv(terminate_at=2)
        events = []
        records = []

        with tempfile.TemporaryDirectory() as directory:
            old_cwd = Path.cwd()
            try:
                os.chdir(directory)
                result = run_fake(
                    runner, env, max_steps=10, events=events, records=records)
                self.assertFalse((Path(directory) / "db").exists())
            finally:
                os.chdir(old_cwd)

        self.assertNotIn("llm_controller.memory", sys.modules)
        self.assertEqual(events, [
            "negotiation", ("decision", None),
            "negotiation", ("decision", None),
        ])
        self.assertEqual(len(env.step_calls), 2)
        self.assertTrue(all(passed_env is env
                            for _, passed_env in env.step_calls))
        self.assertEqual(
            [[int(item) for item in action]
             for action, _ in env.step_calls], [[4, 1], [4, 1]])
        self.assertTrue(all(isinstance(action[0], np.int32)
                            for action, _ in env.step_calls))
        self.assertEqual([record["joint_action"] for record in records],
                         [[4, 1], [4, 1]])
        self.assertEqual(result["completion_status"],
                         "environment_terminated")
        self.assertEqual(result["termination_reason"],
                         "all_controlled_vehicles_arrived")

    def test_max_steps_is_a_distinct_nonterminal_stop(self):
        runner = load_runner()
        env = FakeEnv()
        result = run_fake(runner, env, max_steps=3, events=[])

        self.assertEqual(len(env.step_calls), 3)
        self.assertEqual(result["completion_status"], "max_steps_reached")
        self.assertEqual(result["termination_reason"], "max_steps_guard")
        self.assertEqual(result["status"], "stopped")

    def test_backend_or_parser_error_is_not_hidden(self):
        runner = load_runner()
        env = FakeEnv()
        expected = RuntimeError("raw backend failure")

        with self.assertRaisesRegex(RuntimeError, "raw backend failure"):
            run_fake(
                runner, env, max_steps=3, events=[], action_error=expected)
        self.assertEqual(env.step_calls, [])

        invalid_env = FakeEnv()
        with self.assertRaisesRegex(ValueError, "invalid action ID"):
            run_fake(
                runner, invalid_env, max_steps=3, events=[],
                actions=[[np.int32(-1)], [np.int32(1)]])
        self.assertEqual(invalid_env.step_calls, [])

    def test_runtime_error_summary_keeps_completed_progress(self):
        runner = load_runner()
        error = RuntimeError("original failure")
        summary = runner.runtime_error_summary(
            error,
            [{"reward": 1.25}, {"reward": -0.5}],
            7.5,
            "Traceback: original failure",
        )

        self.assertEqual(summary["completion_status"], "runtime_error")
        self.assertEqual(summary["termination_reason"], "runtime_error")
        self.assertEqual(summary["total_steps"], 2)
        self.assertEqual(summary["total_reward"], 0.75)
        self.assertEqual(summary["error_message"], "original failure")
        self.assertIn("original failure", summary["traceback"])

    def test_numpy_records_are_json_safe(self):
        runner = load_runner()
        safe = runner.json_safe({
            "action": np.int32(4),
            "reward": np.float32(1.5),
            "array": np.array([4, 1, 1, 1], dtype=np.int32),
        })
        encoded = json.dumps(safe)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["action"], 4)
        self.assertEqual(decoded["array"], [4, 1, 1, 1])

    def test_run_directory_never_overwrites_existing_result(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            first = runner.create_run_directory(directory, run_id="fixed-run")
            marker = first / "marker.txt"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                runner.create_run_directory(directory, run_id="fixed-run")
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_stage_1c_does_not_modify_protected_released_code(self):
        paths = [
            "Run_multi_CAV_LLM.py",
            "llm_controller",
            "highway_env",
            "requirements.txt",
        ]
        completed = subprocess.run(
            ["git", "-c", "safe.directory={}".format(ROOT.as_posix()),
             "diff", "--exit-code", BASELINE_COMMIT, "--", *paths],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
