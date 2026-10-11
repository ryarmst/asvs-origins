"""LLM JSON completion. OpenAI-compatible HTTP, plus an in-process mock."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class ProviderError(RuntimeError):
    pass


class JsonProvider(Protocol):
    provider: str
    model_id: str

    def complete_json(self, system: str, user: str) -> dict: ...


@dataclass
class MockProvider:
    """Returns queued JSON payloads. Used in tests and offline fixtures."""

    responses: list[dict] = field(default_factory=list)
    provider: str = "mock"
    model_id: str = "mock-v1"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        if not self.responses:
            raise ProviderError("mock provider has no remaining responses")
        return self.responses.pop(0)


@dataclass
class FunctionProvider:
    """Call a local function. Used to inject this-session drafts."""

    fn: Callable[[str, str], dict]
    provider: str = "local"
    model_id: str = "session"

    def complete_json(self, system: str, user: str) -> dict:
        return self.fn(system, user)


@dataclass
class OpenAICompatProvider:
    """POST /v1/chat/completions with response_format json_object."""

    api_key: str
    model_id: str
    base_url: str = "https://api.openai.com/v1"
    provider: str = "openai-compat"
    timeout: int = 120

    def complete_json(self, system: str, user: str) -> dict:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model_id,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderError(f"LLM HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"LLM request failed: {exc}") from exc
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected LLM response shape: {body!r}"[:400]) from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"LLM did not return JSON: {text[:300]!r}") from exc


def provider_from_env(override: JsonProvider | None = None) -> JsonProvider:
    if override is not None:
        return override
    key = os.environ.get("ASVS_ORIGINS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("ASVS_ORIGINS_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4.1"
    base = os.environ.get("ASVS_ORIGINS_LLM_BASE_URL") or "https://api.openai.com/v1"
    if not key:
        raise ProviderError(
            "No LLM key. Set ASVS_ORIGINS_LLM_API_KEY or OPENAI_API_KEY, "
            "or pass a MockProvider in tests."
        )
    return OpenAICompatProvider(api_key=key, model_id=model, base_url=base)
