import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_path(name, relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_path(
    "stage1k_full_episode", "scripts/minimal_ollama_full_episode.py")
sys.modules.setdefault("scripts.minimal_ollama_full_episode", runner)
preflight = load_path("stage1k_merge_preflight", "scripts/merge_preflight.py")


class Vehicle:
    def __init__(self, name, index, crashed=False, arrived=False):
        self.name = name
        self.id = index
        self.lane_index = ("a", "b", 0) if index == 0 else ("j", "k", 0)
        self.position = [float(index), float(index + 1)]
        self.speed = 15.0 + index
        self.crashed = crashed
        self.arrived = arrived

    def __str__(self):
        return self.name


class MergeEnv:
    def __init__(self):
        self.spec = SimpleNamespace(id=runner.MERGE_SCENARIO)
        self.config = dict(runner.MERGE_CONFIG)
        self.controlled_vehicles = [
            Vehicle("c0", 0), Vehicle("c1", 1), Vehicle("c2", 2)]
        self.road = SimpleNamespace(
            vehicles=self.controlled_vehicles + [
                Vehicle("h0", 3), Vehicle("h1", 4), Vehicle("h2", 5)])
        self.action_space = SimpleNamespace(
            spaces=[object(), object(), object()])
        self.vehicle = self.controlled_vehicles[0]
        self.steps = 0
        self.step_calls = []
        self.reset_calls = []

    def reset(self, is_training=False, testing_seeds=0):
        self.reset_calls.append((is_training, testing_seeds))
        self.steps = 0
        return []

    def has_arrived(self, vehicle):
        return vehicle.arrived

    def step(self, action, passed_env):
        self.step_calls.append((action, passed_env))
        self.steps += 1
        return SimpleNamespace(shape=(3,)), 1.0, True, {}


class Memory:
    def __init__(self, events):
        self.events = events
        self.records = []

    def retrieveMemory(self, query, top_k=5):
        self.events.append(("retrieve", len(self.records), top_k))
        return list(self.records[-top_k:])

    def addMemory(self, vehicle):
        self.records.append(vehicle)
        self.events.append(("write", vehicle))


class MergePreflightTests(unittest.TestCase):
    def test_intersection_defaults_remain_unchanged(self):
        args = runner.parse_args([])
        self.assertEqual(args.scenario, runner.INTERSECTION_SCENARIO)
        self.assertIsNone(runner.scenario_config(args.scenario))
        self.assertEqual(
            runner.default_output_directory(args.scenario, "off"),
            "runs/intersection-memory-off")

    def test_merge_config_and_output_are_scenario_correct(self):
        args = runner.parse_args(["--scenario", runner.MERGE_SCENARIO])
        self.assertEqual(runner.scenario_config(args.scenario), {
            "simulation_frequency": 20,
            "policy_frequency": 5,
            "duration": 40,
        })
        self.assertEqual(
            runner.default_output_directory(args.scenario, "off"),
            "runs/merge-memory-off")

    def test_post_reset_topology_is_recorded_and_enforced(self):
        env = MergeEnv()
        record = runner.validate_post_reset_topology(
            env, runner.MERGE_SCENARIO, 987654)
        self.assertEqual(record["controlled_vehicle_count"], 3)
        self.assertEqual(record["road_vehicle_count"], 6)
        self.assertEqual(record["action_tuple_arity"], 3)
        self.assertEqual(record["testing_seed"], 987654)
        self.assertEqual(
            [item["index"] for item in record["controlled_vehicle_order"]],
            [0, 1, 2])

        env.controlled_vehicles.pop()
        with self.assertRaisesRegex(RuntimeError, "exactly 3"):
            runner.validate_post_reset_topology(
                env, runner.MERGE_SCENARIO, 987654)
        env = MergeEnv()
        env.action_space.spaces.pop()
        with self.assertRaisesRegex(RuntimeError, "arity 3"):
            runner.validate_post_reset_topology(
                env, runner.MERGE_SCENARIO, 987654)

    def test_merge_termination_contract_and_precedence(self):
        env = MergeEnv()
        for vehicle in env.controlled_vehicles:
            vehicle.arrived = True
        env.steps = 199
        self.assertFalse(runner.merge_environment_terminated(env))
        self.assertEqual(
            runner.environment_terminal_reason(env),
            "unresolved_environment_terminal_condition")

        env.steps = 200
        self.assertTrue(runner.merge_environment_terminated(env))
        self.assertEqual(
            runner.environment_terminal_reason(env),
            "released_duration_limit")

        env.steps = 10
        env.controlled_vehicles[1].crashed = True
        self.assertTrue(runner.merge_environment_terminated(env))
        self.assertEqual(
            runner.environment_terminal_reason(env),
            "controlled_vehicle_collision")

    def test_frozen_derived_success_rule(self):
        base = {
            "completion_status": "environment_terminated",
            "controlled_vehicle_arrival": [True, True, True],
            "controlled_vehicle_collision": [False, False, False],
        }
        self.assertTrue(runner.classify_derived_success(base))
        self.assertFalse(runner.classify_derived_success(dict(
            base, controlled_vehicle_arrival=[True, False, True])))
        self.assertFalse(runner.classify_derived_success(dict(
            base, controlled_vehicle_collision=[True, False, False])))
        self.assertFalse(runner.classify_derived_success(dict(
            base, completion_status="max_steps_reached")))

    def test_merge_memory_off_policy_cycle(self):
        env = MergeEnv()
        events = []
        observed_memory = []
        sys.modules.pop("llm_controller.memory", None)

        class Negotiation:
            def llm_controller_run(self, passed_env):
                events.append("negotiation")
                return "negotiation", []

        class Action:
            ACTIONS_ALL = {1: "IDLE", 3: "FASTER", 4: "SLOWER"}

            def llm_controller_run(self, passed_env, negotiation, conflicts,
                                   vehicles, memory):
                observed_memory.append(memory)
                actions = []
                for index, _ in enumerate(vehicles):
                    events.append("decision-c{}".format(index))
                    actions.append([[4], [1], [3]][index])
                return actions

        result = runner.run_episode(
            env, Negotiation, Action, 1, memory_factory=None)
        events.append("env.step")
        self.assertEqual(events, [
            "negotiation", "decision-c0", "decision-c1", "decision-c2",
            "env.step"])
        self.assertEqual(len(env.step_calls), 1)
        self.assertEqual(env.step_calls[0][0], (4, 1, 3))
        self.assertIs(env.step_calls[0][1], env)
        self.assertEqual(observed_memory, [None])
        self.assertEqual(result["total_steps"], 1)
        self.assertNotIn("llm_controller.memory", sys.modules)

    def test_merge_released_style_memory_on_three_writes_before_step(self):
        env = MergeEnv()
        events = []
        memory = Memory(events)

        class Negotiation:
            def llm_controller_run(self, passed_env):
                events.append(("negotiation",))
                return "negotiation", []

        class Action:
            ACTIONS_ALL = {1: "IDLE"}

            def llm_controller_run(self, passed_env, negotiation, conflicts,
                                   vehicles, memory):
                actions = []
                for index, vehicle in enumerate(vehicles):
                    prior = memory.retrieveMemory("query", top_k=2)
                    events.append(("decision", index, len(prior)))
                    memory.addMemory(str(vehicle))
                    actions.append([1])
                return actions

        original_step = env.step

        def step(action, passed_env):
            events.append(("env.step", action))
            return original_step(action, passed_env)

        env.step = step
        runner.run_episode(
            env, Negotiation, Action, 1, memory_factory=lambda: memory)
        self.assertEqual([item[0] for item in events], [
            "negotiation", "retrieve", "decision", "write",
            "retrieve", "decision", "write",
            "retrieve", "decision", "write", "env.step"])
        self.assertEqual(
            [item[2] for item in events if item[0] == "retrieve"],
            [2, 2, 2])
        self.assertEqual(
            [item[2] for item in events if item[0] == "decision"],
            [0, 1, 2])
        self.assertEqual(len(memory.records), 3)
        self.assertEqual(env.step_calls[0][0], (1, 1, 1))

    def test_merge_database_namespace_isolated_without_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "memory-db" / runner.MERGE_SCENARIO
            resolved = runner.validate_memory_database_path(
                runner.MERGE_SCENARIO, good)
            self.assertEqual(resolved, good.resolve())
            self.assertFalse(good.exists())
            self.assertEqual(
                runner.require_fresh_memory_database_path(
                    runner.MERGE_SCENARIO, good),
                good.resolve())
            good.mkdir(parents=True)
            with self.assertRaisesRegex(FileExistsError, "fresh absent"):
                runner.require_fresh_memory_database_path(
                    runner.MERGE_SCENARIO, good)
            with self.assertRaisesRegex(ValueError, "another scenario"):
                runner.validate_memory_database_path(
                    runner.MERGE_SCENARIO,
                    root / "memory-db" / runner.INTERSECTION_SCENARIO)
            with self.assertRaisesRegex(ValueError, "namespace"):
                runner.validate_memory_database_path(
                    runner.MERGE_SCENARIO, root / "memory-db" / "shared")

    def test_preflight_repeats_reset_without_llm_or_memory(self):
        env = MergeEnv()
        report = preflight.run_reset_checks(env, 987654, 2)
        self.assertEqual(env.reset_calls, [(False, 987654), (False, 987654)])
        self.assertTrue(report["same_seed_state_reproducible"])
        self.assertFalse(report["llm_invoked"])
        self.assertFalse(report["memory_invoked"])
        self.assertEqual(len(env.step_calls), 0)


if __name__ == "__main__":
    unittest.main()
