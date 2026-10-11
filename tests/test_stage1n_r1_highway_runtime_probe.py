import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_probe():
    path = ROOT / "scripts" / "stage1n_r1_highway_runtime_probe.py"
    spec = importlib.util.spec_from_file_location("stage1n_r1_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVehicle:
    def __init__(self, index):
        self.index = index
        self.lane_index = ("0", "1", index % 4)
        self.position = [float(index), float(index % 4)]
        self.speed = 25.0
        self.crashed = False
        self.on_road = True
        self.route = None

    @property
    def destination(self):
        return list(self.position)

    def __str__(self):
        return "veh{}: fake".format(self.index)


class FakeEnv:
    def __init__(self, events=None):
        self.events = events if events is not None else []
        self.controlled_vehicles = [FakeVehicle(index) for index in range(4)]
        self.road = SimpleNamespace(
            vehicles=self.controlled_vehicles
            + [FakeVehicle(index + 4) for index in range(20)])
        self.action_space = SimpleNamespace(n=5)
        self.spec = SimpleNamespace(id="highway-v0")
        self.config = {
            "simulation_frequency": 15,
            "policy_frequency": 5,
            "duration": 40,
            "controlled_vehicles": 4,
            "vehicles_count": 20,
            "offroad_terminal": False,
        }
        self.steps = 0
        self.seed = None

    def reset(self, is_training=False, testing_seeds=0):
        self.seed = testing_seeds
        for vehicle in self.road.vehicles:
            vehicle.position[0] = float(vehicle.index + testing_seeds % 11)

    def step(self, action, passed_env):
        self.events.append(("env_step", tuple(action)))
        self.steps += 1
        first = action[0] if isinstance(action, tuple) else action
        self.controlled_vehicles[0].speed += float(first)
        return [], 0.0, self.steps >= 40, {}

    def close(self):
        pass


class FakeNegotiation:
    def __init__(self, env, events=None):
        self.events = events
        self.env = env

    def detect_conflicts(self, env):
        return {vehicle: {} for vehicle in env.road.vehicles}

    def llm_controller_run(self, env):
        if self.events is not None:
            self.events.append("negotiation")
        return "negotiation", []


class FakeBackingMemory:
    def __init__(self, store, events):
        self.store = store
        self.events = events

    def retrieveMemory(self, query, top_k=5):
        self.events.append(("retrieve", top_k, len(self.store)))
        return []

    def addMemory(self, *args, **kwargs):
        self.store.append({"record": len(self.store) + 1})
        self.events.append(("write", len(self.store)))


class FakeActionAgent:
    def __init__(self, events):
        self.events = events

    def llm_controller_run(self, env, negotiation_prompt, conflicting_info,
                           controlled_vehicles, memory):
        actions = []
        for index, _vehicle in enumerate(controlled_vehicles):
            self.events.append(("decision", index))
            memory.retrieveMemory("query-{}".format(index), top_k=2)
            memory.addMemory("scene", "question", "negotiation", 1, "comment")
            actions.append([1])
        return actions


class Stage1NR1ProbeTests(unittest.TestCase):
    def test_module_import_has_no_runtime_dependencies_or_artifacts(self):
        probe = load_probe()
        self.assertEqual(probe.HIGHWAY_ENV_ID, "highway-v0")
        self.assertFalse((ROOT / probe.MEMORY_NAMESPACE).exists())

    def test_runtime_requires_explicit_rdp_confirmation_before_imports(self):
        probe = load_probe()
        with self.assertRaisesRegex(RuntimeError, "--confirm-rdp"):
            probe.main(["--probe", "reset"])

    def test_diagnostic_seeds_exclude_formal_range(self):
        probe = load_probe()
        self.assertGreater(probe.DIAGNOSTIC_SEED, 19)
        self.assertGreater(probe.ALTERNATE_DIAGNOSTIC_SEED, 19)
        for seed in range(20):
            with self.assertRaises(ValueError):
                probe.validate_diagnostic_seed(seed)
        self.assertEqual(
            probe.validate_diagnostic_seed(987654), 987654)

    def test_bounds_prevent_formal_or_unbounded_execution(self):
        probe = load_probe()
        self.assertTrue(probe.validate_probe_bounds("termination", 45, 2))
        with self.assertRaises(ValueError):
            probe.validate_probe_bounds("termination", 46, 2)
        with self.assertRaises(ValueError):
            probe.validate_probe_bounds("memory-on", 45, 3)

    def test_output_namespace_rejects_formal_and_batch(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as directory:
            safe = Path(directory) / "runs" / "stage1n-r1-probes"
            self.assertEqual(probe.validate_output_root(safe), safe.resolve())
            for name in ("stage1n-r1-formal", "stage1n-r1-batch"):
                with self.assertRaises(ValueError):
                    probe.validate_output_root(
                        Path(directory) / "runs" / name)

    def test_database_guard_requires_fresh_isolated_namespace(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "runs"
            valid = (base / "highway-stage1n-r1-preflight-memory-on"
                     / "memory-db" / "highway-v0")
            self.assertEqual(
                probe.validate_fresh_diagnostic_db(valid), valid.resolve())
            valid.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                probe.validate_fresh_diagnostic_db(valid)
            for prohibited in (
                    "intersection-multi-agent-v0", "merge-multi-agent-v0",
                    "formal-highway-v0"):
                path = (base / "highway-stage1n-r1-preflight-memory-on"
                        / "memory-db" / prohibited / "highway-v0")
                with self.assertRaises(ValueError):
                    probe.validate_fresh_diagnostic_db(path)

    def test_seed_probe_recreates_environments_and_reports_fields(self):
        probe = load_probe()
        created = []

        def factory():
            env = FakeEnv()
            created.append(env)
            return env

        result = probe.run_seed_probe(factory)
        self.assertEqual(len(created), 3)
        self.assertTrue(result["same_seed_identical"])
        self.assertTrue(result["different_seed_state_differs"])
        self.assertTrue(result["different_seed_differing_fields"])

    def test_action_probe_uses_fresh_identically_seeded_environments(self):
        probe = load_probe()
        created = []

        def factory():
            env = FakeEnv()
            created.append(env)
            return env

        result = probe.run_action_probe(factory)
        self.assertEqual(len(created), 4)
        self.assertEqual({env.seed for env in created}, {987654})
        self.assertTrue(result["same_first_transition_identical"])
        self.assertTrue(result["changed_first_transition_differs"])

    def test_memory_probe_orders_four_queries_writes_before_one_step(self):
        probe = load_probe()
        events = []
        store = []
        env = FakeEnv(events)

        def memory_factory():
            return FakeBackingMemory(store, events)

        result = probe.run_memory_cycles(
            env,
            negotiation_factory=lambda current: FakeNegotiation(
                current, events),
            action_factory=lambda current: FakeActionAgent(events),
            memory_factory=memory_factory,
            count_records=lambda memory: len(memory.store),
            cycles=2,
        )
        self.assertEqual(
            [record["record_count_after_four_writes"]
             for record in result["cycle_records"]], [4, 8])
        self.assertEqual(
            [record["retrieval_count"] for record in result["cycle_records"]],
            [4, 4])
        self.assertEqual(
            [record["write_count"] for record in result["cycle_records"]],
            [4, 4])
        self.assertEqual(
            [event for event in events if event[0] == "env_step"],
            [("env_step", (1, 1, 1, 1)),
             ("env_step", (1, 1, 1, 1))])
        first_step_index = events.index(("env_step", (1, 1, 1, 1)))
        self.assertEqual(
            len([event for event in events[:first_step_index]
                 if event[0] == "retrieve"]), 4)
        self.assertEqual(
            len([event for event in events[:first_step_index]
                 if event[0] == "write"]), 4)
        retrieval_visibility = [
            event[2] for event in events if event[0] == "retrieve"]
        self.assertEqual(retrieval_visibility, list(range(8)))

    def test_no_retry_replacement_or_success_rate_contract(self):
        probe = load_probe()
        source = (ROOT / "scripts" / "stage1n_r1_highway_runtime_probe.py").read_text(
            encoding="utf-8")
        self.assertNotIn("success_rate =", source)
        self.assertNotIn("replacement_seed", source)
        self.assertNotIn("retry", source.lower())
        self.assertEqual(probe.MEMORY_CYCLES, 2)


if __name__ == "__main__":
    unittest.main()
