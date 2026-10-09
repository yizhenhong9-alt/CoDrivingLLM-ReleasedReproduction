import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RELEASED_COMMIT = "f9e71fed08c1772cf4009ed61dfe91177019cf7d"


def released_source(path):
    return subprocess.check_output(
        ["git", "-c", "safe.directory={}".format(ROOT.as_posix()),
         "show", "{}:{}".format(RELEASED_COMMIT, path)],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
    )


def current_source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def load_smoke_runner():
    script_path = ROOT / "scripts" / "minimal_ollama_single_step.py"
    spec = importlib.util.spec_from_file_location(
        "minimal_ollama_single_step", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_node(source, class_name, function_name):
    tree = ast.parse(source)
    scope = tree.body
    if class_name is not None:
        scope = next(
            node.body for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
    return next(
        node for node in scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )


def prompt_expression(source, class_name):
    function = function_node(source, class_name, "send_to_chatgpt")
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "prompt"
                   for target in node.targets):
                return ast.dump(node.value, include_attributes=False)
    raise AssertionError("prompt assignment not found")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OllamaTransportTests(unittest.TestCase):
    def test_native_ollama_payload_and_response(self):
        from llm_controller.llm_backend import ChatBackend

        messages = [{"role": "system", "content": "unchanged prompt"}]
        backend = ChatBackend(
            backend="ollama",
            model="qwen2.5:7b",
            endpoint="http://127.0.0.1:11435/",
            timeout=17,
        )
        response = FakeResponse({"message": {"content": "raw model content"}})

        with mock.patch("llm_controller.llm_backend.request.urlopen",
                        return_value=response) as urlopen:
            content = backend.complete(messages)

        self.assertEqual(content, "raw model content")
        self.assertEqual(backend.last_messages, messages)
        self.assertEqual(backend.last_request, {
            "model": "qwen2.5:7b",
            "messages": messages,
            "stream": False,
        })
        request_object = urlopen.call_args.args[0]
        self.assertEqual(request_object.full_url,
                         "http://127.0.0.1:11435/api/chat")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 17)

    def test_rejects_non_ollama_backend(self):
        from llm_controller.llm_backend import ChatBackend

        with self.assertRaises(ValueError):
            ChatBackend(backend="openai")


class ReleasedSemanticsTests(unittest.TestCase):
    def test_action_prompt_expression_is_identical(self):
        path = "llm_controller/llm_agent_action.py"
        self.assertEqual(
            prompt_expression(released_source(path), "LlmAgent_action_module"),
            prompt_expression(current_source(path), "LlmAgent_action_module"),
        )

    def test_negotiation_prompt_expression_is_identical(self):
        path = "llm_controller/llm_agent_negotiation_system.py"
        self.assertEqual(
            prompt_expression(released_source(path), "LlmAgent_negotiation_module"),
            prompt_expression(current_source(path), "LlmAgent_negotiation_module"),
        )

    def test_parser_and_action_mapping_functions_are_identical(self):
        path = "llm_controller/llm_agent_action.py"
        released = released_source(path)
        current = current_source(path)
        for function_name in (
                "get_action_id_from_name", "extract_decision",
                "extract_vehicle_conflicts"):
            with self.subTest(function=function_name):
                released_node = function_node(
                    released, "LlmAgent_action_module", function_name)
                current_node = function_node(
                    current, "LlmAgent_action_module", function_name)
                self.assertEqual(
                    ast.dump(released_node, include_attributes=False),
                    ast.dump(current_node, include_attributes=False),
                )

    def test_no_proxy_api_key_retry_or_fallback_was_added(self):
        combined = "\n".join([
            current_source("llm_controller/llm_backend.py"),
            current_source("llm_controller/llm_agent_action.py"),
            current_source("llm_controller/llm_agent_negotiation_system.py"),
        ])
        self.assertNotIn("127.0.0.1:7890", combined)
        self.assertNotIn("OPENAI_API_KEY", combined)
        self.assertNotIn("api_key", combined)
        self.assertNotIn("retry", combined.lower())
        self.assertNotIn("fallback", combined.lower())


class MemoryOffOrderingTests(unittest.TestCase):
    def test_memory_off_single_step_order_and_no_database(self):
        module = load_smoke_runner()

        events = []

        class FakeEnv:
            controlled_vehicles = ["cav-0", "cav-1"]

            def step(self, action, passed_env):
                events.append(("env.step", action, passed_env is self))
                return "observation", 1.25, False, {"ok": True}

        class FakeNegotiationAgent:
            def llm_controller_run(self, env):
                events.append(("negotiation", env))
                return "released negotiation response", ["conflict"]

        class FakeActionAgent:
            def llm_controller_run(self, env, negotiation_prompt,
                                   conflicting_info, controlled_vehicles,
                                   memory):
                events.append((
                    "decisions", env, negotiation_prompt, conflicting_info,
                    controlled_vehicles, memory))
                return [[1], [3]]

        with tempfile.TemporaryDirectory() as temporary_directory:
            old_cwd = Path.cwd()
            try:
                # If the runner accidentally initializes released Memory, its
                # default relative database would appear below this directory.
                import os
                os.chdir(temporary_directory)
                result = module.run_policy_step(
                    FakeEnv(), FakeNegotiationAgent(), FakeActionAgent())
                self.assertFalse((Path(temporary_directory) / "db").exists())
            finally:
                os.chdir(old_cwd)

        self.assertNotIn("llm_controller.memory", sys.modules)
        self.assertEqual([event[0] for event in events], [
            "negotiation", "decisions", "env.step"])
        self.assertIsNone(events[1][-1])
        self.assertEqual(events[2][1], (1, 3))
        self.assertTrue(events[2][2])
        self.assertEqual(result["joint_action"], (1, 3))

    def test_numpy_joint_action_summary_is_json_safe_and_ordered(self):
        module = load_smoke_runner()
        backend = SimpleNamespace(
            backend="ollama",
            model="qwen2.5:7b",
            endpoint="http://127.0.0.1:11435",
        )
        args = SimpleNamespace(seed=0)
        result = {
            "joint_action": (
                np.int32(4), np.int32(1), np.int32(1), np.int32(1)),
            "reward": np.float32(1.25),
            "terminated": np.bool_(False),
        }

        summary = module.build_summary(backend, args, result)
        encoded = json.dumps(summary)

        self.assertEqual(summary["joint_action"], [4, 1, 1, 1])
        self.assertTrue(all(type(action) is int
                            for action in summary["joint_action"]))
        self.assertEqual(json.loads(encoded)["joint_action"], [4, 1, 1, 1])


if __name__ == "__main__":
    unittest.main()
