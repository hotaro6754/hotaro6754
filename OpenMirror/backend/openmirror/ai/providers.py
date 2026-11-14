"""Language-model providers.

OpenMirror never requires a model. When one is configured it is, by default,
a *local* Ollama server on 127.0.0.1. Any provider whose host is not a loopback
address is treated as **external**: the UI must show a warning and the user
must explicitly allow it for each run, because chat excerpts leave the machine.

Configuration (environment variables):

* ``OPENMIRROR_AI_PROVIDER``  ``ollama`` (default) | ``openai_compat`` | ``none``
* ``OPENMIRROR_AI_BASE_URL``  default ``http://127.0.0.1:11434`` for Ollama
* ``OPENMIRROR_AI_MODEL``     default ``qwen3:4b``
* ``OPENMIRROR_AI_API_KEY``   only for ``openai_compat`` (never logged or returned)
* ``OPENMIRROR_AI_NUM_CTX``   context window requested from Ollama (default 8192)
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

THINK_RE = re.compile(r"<think>.*?</think>", re.S)


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    name: str
    model: str
    base_url: str

    @property
    def external(self) -> bool: ...

    def chat(self, system: str, user: str, *, json_mode: bool = True, max_tokens: int = 1200, temperature: float = 0.2) -> str: ...

    def status(self) -> dict: ...


def is_loopback_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"content-type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL is user configuration
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise ProviderError(f"model server returned HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise ProviderError(f"cannot reach the model server at {url}: {exc}") from None


def _get_json(url: str, headers: dict[str, str] | None = None, timeout: float = 5) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def clean_output(text: str) -> str:
    """Strip reasoning blocks and code fences some models wrap around JSON."""
    text = THINK_RE.sub("", text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    return text


@dataclass
class OllamaProvider:
    model: str = "qwen3:4b"
    base_url: str = "http://127.0.0.1:11434"
    num_ctx: int = 8192
    timeout: float = 600
    name: str = "ollama"

    @property
    def external(self) -> bool:
        return not is_loopback_url(self.base_url)

    def chat(self, system: str, user: str, *, json_mode: bool = True, max_tokens: int = 1200, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "num_ctx": self.num_ctx, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        data = _post_json(f"{self.base_url.rstrip('/')}/api/chat", payload, {}, self.timeout)
        return clean_output(data.get("message", {}).get("content", ""))

    def status(self) -> dict:
        try:
            tags = _get_json(f"{self.base_url.rstrip('/')}/api/tags")
            models = sorted(m["name"] for m in tags.get("models", []))
            return {"reachable": True, "models": models, "model_installed": self.model in models}
        except Exception as exc:  # noqa: BLE001
            return {"reachable": False, "models": [], "model_installed": False, "error": str(exc)[:200]}


@dataclass
class OpenAICompatProvider:
    """Any server speaking the OpenAI chat-completions API (LM Studio, llama.cpp
    server, vLLM, or a hosted service)."""

    model: str
    base_url: str
    api_key: str | None = field(default=None, repr=False)
    timeout: float = 600
    name: str = "openai_compat"

    @property
    def external(self) -> bool:
        return not is_loopback_url(self.base_url)

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def chat(self, system: str, user: str, *, json_mode: bool = True, max_tokens: int = 1200, temperature: float = 0.2) -> str:
        payload: dict = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _post_json(f"{self.base_url.rstrip('/')}/chat/completions", payload, self._headers(), self.timeout)
        try:
            return clean_output(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError) as exc:
            raise ProviderError("unexpected response from the model server") from exc

    def status(self) -> dict:
        try:
            data = _get_json(f"{self.base_url.rstrip('/')}/models", self._headers())
            models = sorted(m.get("id", "") for m in data.get("data", []))
            return {"reachable": True, "models": models, "model_installed": self.model in models or not models}
        except Exception as exc:  # noqa: BLE001
            return {"reachable": False, "models": [], "model_installed": False, "error": str(exc)[:200]}


def provider_from_env(model_override: str | None = None) -> Provider | None:
    kind = os.environ.get("OPENMIRROR_AI_PROVIDER", "ollama").strip().lower()
    model = model_override or os.environ.get("OPENMIRROR_AI_MODEL", "qwen3:4b")
    if kind in ("", "none", "off"):
        return None
    if kind == "ollama":
        return OllamaProvider(
            model=model,
            base_url=os.environ.get("OPENMIRROR_AI_BASE_URL", "http://127.0.0.1:11434"),
            num_ctx=int(os.environ.get("OPENMIRROR_AI_NUM_CTX", "8192")),
        )
    if kind == "openai_compat":
        base = os.environ.get("OPENMIRROR_AI_BASE_URL")
        if not base:
            raise ValueError("OPENMIRROR_AI_BASE_URL is required for openai_compat")
        return OpenAICompatProvider(model=model, base_url=base, api_key=os.environ.get("OPENMIRROR_AI_API_KEY"))
    raise ValueError(f"unknown OPENMIRROR_AI_PROVIDER {kind!r}")
