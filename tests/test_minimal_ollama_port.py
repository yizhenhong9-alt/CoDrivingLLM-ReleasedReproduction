import ast
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock


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


if __name__ == "__main__":
    unittest.main()
