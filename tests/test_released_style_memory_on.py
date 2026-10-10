import ast
import importlib.util
import json
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RELEASED_COMMIT = "f9e71fed08c1772cf4009ed61dfe91177019cf7d"


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_ast(source, name):
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "LlmAgent_action_module")
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name == name)
    return ast.dump(node, include_attributes=False)


class Vehicle:
    speed = 1
    crashed = False
    on_road = True

    def __init__(self, name): self.name = name
    def __str__(self): return self.name


class Memory:
    def __init__(self, events): self.events = events
    def retrieveMemory(self, query, top_k=5):
        self.events.append(("retrieve", query, top_k))
        return [{"negotiation_result": "yielded", "final_action": "[1]", "comments": "recommended"}]
    def addMemory(self, *values): self.events.append(("write", values))


class ReleasedStyleMemoryTests(unittest.TestCase):
    def test_released_retrieval_and_update_functions_unchanged(self):
        current = (ROOT / "llm_controller/llm_agent_action.py").read_text(encoding="utf-8")
        released = subprocess.check_output(
            ["git", "-c", "safe.directory={}".format(ROOT.as_posix()), "show",
             "{}:llm_controller/llm_agent_action.py".format(RELEASED_COMMIT)],
            cwd=str(ROOT), text=True, encoding="utf-8")
        for name in ("relative_memory", "memory_update"):
            self.assertEqual(function_ast(current, name), function_ast(released, name))

    def make_agent(self, mode, events):
        from types import ModuleType
        with mock.patch.dict(sys.modules, {"gym": ModuleType("gym")}):
            from llm_controller.llm_agent_action import LlmAgent_action_module
        agent = object.__new__(LlmAgent_action_module)
        agent.memory_mode = mode
        agent.get_scene_name = MethodType(lambda self, env: "intersection", agent)
        agent.transfer_negotiation_prompts_to_results = MethodType(lambda self, *args: "negotiation", agent)
        agent.prompt_engineer = MethodType(lambda self, vehicle, *args: "scene {}\n_conflict_".format(vehicle), agent)
        agent.send_to_chatgpt = MethodType(
            lambda self, vehicle, prompt, negotiation, memory: (
                self.relative_memory(memory, prompt) if self.memory_mode == "on" else "",
                events.append(("decision", str(vehicle))), [1])[-1], agent)
        agent.memory_update = MethodType(lambda self, memory, prompt, action: events.append(("update", prompt)), agent)
        return agent

    def test_off_has_no_retrieval_or_update(self):
        events = []
        agent = self.make_agent("off", events)
        actions = agent.llm_controller_run(SimpleNamespace(road=object()), "n", [], [Vehicle("c0")], Memory(events))
        self.assertEqual(actions, [[1]])
        self.assertEqual(events, [("decision", "c0")])

    def test_on_per_cav_order_and_top_k(self):
        events = []
        agent = self.make_agent("on", events)
        agent.llm_controller_run(SimpleNamespace(road=object()), "n", [], [Vehicle("c0"), Vehicle("c1")], Memory(events))
        self.assertEqual([item[0] for item in events], ["retrieve", "decision", "update", "retrieve", "decision", "update"])
        self.assertEqual(events[0][2], 2)

    def test_runner_places_update_before_one_env_step(self):
        runner = load_path("full_episode_stage1h", ROOT / "scripts/minimal_ollama_full_episode.py")
        events, memory = [], Memory([])
        memory.events = events
        class Env:
            controlled_vehicles = [Vehicle("c0")]
            config = {"duration": 50, "policy_frequency": 5, "offroad_terminal": False}
            steps = 0; vehicle = controlled_vehicles[0]
            def step(self, action, passed):
                events.append(("env.step", action)); self.steps += 1
                return SimpleNamespace(shape=(1,)), 1.0, True, {}
            def has_arrived(self, vehicle): return True
        class Negotiation:
            def llm_controller_run(self, env): events.append(("negotiation",)); return "n", []
        class Action:
            ACTIONS_ALL = {1: "IDLE"}
            def llm_controller_run(self, env, negotiation, conflicts, vehicles, memory):
                memory.retrieveMemory("query", 2); events.append(("decision",))
                memory.addMemory("s", "None", "None", "[1]", "ok")
                return [[1]]
        runner.run_episode(Env(), Negotiation, Action, 1, memory_factory=lambda: memory)
        self.assertEqual([item[0] for item in events], ["negotiation", "retrieve", "decision", "write", "env.step"])

    def test_embedding_transport_is_fake_and_separate(self):
        from llm_controller.embedding_backend import OllamaEmbeddingsAdapter
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps({"model": "nomic-embed-text:latest", "embeddings": [[0.1, 0.2]]}).encode()
        adapter = OllamaEmbeddingsAdapter("http://127.0.0.1:11435", "nomic-embed-text:latest", 17)
        with mock.patch("llm_controller.embedding_backend.request.urlopen", return_value=Response()) as call:
            self.assertEqual(adapter.embed_query("scene"), [0.1, 0.2])
        self.assertEqual(call.call_args.args[0].full_url, "http://127.0.0.1:11435/api/embed")
        self.assertEqual(adapter.last_request["model"], "nomic-embed-text:latest")

    def test_fresh_explicit_db_and_persistent_command_identity(self):
        batch = load_path("memory_on_batch_stage1h", ROOT / "scripts/run_intersection_memory_on_batch.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = batch.memory_database_path(root)
            config = {"backend": "ollama", "model": "qwen2.5:7b", "endpoint": "http://127.0.0.1:11435", "timeout_seconds": 120, "max_steps_guard": 300, "memory_db_path": db, "embedding_backend": "ollama", "embedding_model": "nomic-embed-text:latest", "embedding_endpoint": "http://127.0.0.1:11435", "embedding_timeout_seconds": 120}
            commands = [batch.trial_command(ROOT, root / "t{}".format(seed), seed, config) for seed in (0, 1)]
            paths = [command[command.index("--memory-db-path") + 1] for command in commands]
            self.assertEqual(paths, [str(db), str(db)])
            db.mkdir(parents=True)
            with self.assertRaises(FileExistsError): batch.memory_database_path(root)


if __name__ == "__main__": unittest.main()
