from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
from urllib import request


class LLMBackend(Protocol):
    name: str

    def generate(self, prompt: str) -> str:
        ...


@dataclass
class MockLLMBackend:
    response_text: str = "Mock local model answer"
    name: str = "mock"

    def generate(self, prompt: str) -> str:
        return self.response_text


@dataclass
class OllamaBackend:
    model: str
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 120
    name: str = "ollama"

    def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = _post_json(
            f"{self.base_url.rstrip('/')}/api/generate",
            payload,
            timeout_seconds=self.timeout_seconds,
        )
        text = response.get("response")
        if not isinstance(text, str):
            raise RuntimeError("Ollama response did not include a string 'response' field")
        return text


@dataclass
class OpenAICompatibleBackend:
    model: str
    base_url: str
    api_key: str | None = None
    timeout_seconds: int = 120
    name: str = "openai-compatible"

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer using only the provided Jira and spec evidence.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = _post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            headers=headers,
            timeout_seconds=self.timeout_seconds,
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI-compatible response did not include choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("OpenAI-compatible response did not include message content")
        return content


def build_llm_backend(
    *,
    backend: str = "none",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    mock_response: str | None = None,
    timeout_seconds: int = 120,
) -> LLMBackend | None:
    if backend == "none":
        return None
    if backend == "mock":
        return MockLLMBackend(response_text=mock_response or "Mock local model answer")
    if backend == "ollama":
        if not model:
            raise ValueError("--llm-model is required when --llm-backend=ollama")
        return OllamaBackend(
            model=model,
            base_url=base_url or "http://localhost:11434",
            timeout_seconds=timeout_seconds,
        )
    if backend == "openai-compatible":
        if not model:
            raise ValueError("--llm-model is required when --llm-backend=openai-compatible")
        if not base_url:
            raise ValueError("--llm-base-url is required when --llm-backend=openai-compatible")
        return OpenAICompatibleBackend(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM backend: {backend}")


def _post_json(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: int,
) -> dict:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=encoded, headers=request_headers, method="POST")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))
