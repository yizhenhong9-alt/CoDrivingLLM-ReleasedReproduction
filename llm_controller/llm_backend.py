import json
import time
from urllib import request


class ChatBackend:
    """Minimal native Ollama chat transport.

    Prompt construction, message roles, response parsing, and action mapping stay
    in the released controller modules. This class only converts messages to an
    Ollama /api/chat request and returns message.content unchanged.
    """

    def __init__(self, backend="ollama", model="qwen2.5:7b",
                 endpoint="http://127.0.0.1:11435", timeout=120):
        if backend != "ollama":
            raise ValueError("Only the explicit Ollama backend is supported")
        if not model:
            raise ValueError("An explicit Ollama model is required")
        if not endpoint:
            raise ValueError("An explicit Ollama endpoint is required")

        self.backend = backend
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.last_messages = None
        self.last_request = None
        self.last_raw_response = None
        self.last_content = None
        self.last_latency_seconds = None

    def complete(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self.endpoint + "/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        self.last_messages = messages
        self.last_request = payload
        started = time.perf_counter()
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        finally:
            self.last_latency_seconds = time.perf_counter() - started

        message = raw_response.get("message") if isinstance(raw_response, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("Ollama response is missing message.content")

        self.last_raw_response = raw_response
        self.last_content = message["content"]
        return self.last_content
