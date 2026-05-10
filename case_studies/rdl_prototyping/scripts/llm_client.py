#!/usr/bin/env python3
"""Front-end-agnostic LLM client used by run_llm_trial.py.

Two providers are supported:

* ``mock``      — deterministic, reads pre-recorded turns from
                  ``mock_dir/<frontend>/turn_NN.txt``. Used by the
                  self-check (``Phase 5``) and CI; never touches the
                  network.
* ``openai``    — talks to the OpenAI Chat Completions endpoint. Only
                  imported when actually needed; ``openai`` is optional.
* ``anthropic`` — talks to Anthropic Messages endpoint, same idea.

The client exposes a single method:

    chat(messages: list[dict]) -> str

where ``messages`` is the OpenAI-style ``[{role, content}, ...]`` list.

Real-LLM providers will refuse to run unless the corresponding API key
env var is set (so the harness fails fast on a misconfigured trial).
"""
from __future__ import annotations

import abc
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------
# Tiny tolerant YAML reader (avoids depending on PyYAML).
# Supports flat key: value pairs only. We do not need nested maps.
# --------------------------------------------------------------------------
def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None

    if yaml is not None:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise SystemExit(f"{path}: top-level YAML must be a mapping")
        return data

    cfg: dict[str, Any] = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip() or ":" not in line:
                continue
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if not k or not v:
                continue
            if v.lower() in {"true", "false"}:
                cfg[k] = v.lower() == "true"
            else:
                try:
                    cfg[k] = int(v)
                except ValueError:
                    cfg[k] = v.strip('"').strip("'")
    return cfg


# --------------------------------------------------------------------------
# Abstract base.
# --------------------------------------------------------------------------
class LLMClient(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def chat(self, messages: list[dict]) -> str:
        ...


# --------------------------------------------------------------------------
# Mock client.
# --------------------------------------------------------------------------
class MockClient(LLMClient):
    """Reads ``<mock_dir>/<frontend>/turn_<N>.txt`` deterministically.

    The turn index is determined by counting how many ``role=='assistant'``
    messages already appear in the conversation: 0 turns yet -> serve
    turn_0; one assistant turn already -> serve turn_1; etc. Missing
    turn files cause the client to fall through to a uniform "I have
    nothing more to add" response so the trial loop terminates cleanly.
    """
    name = "mock"

    def __init__(self, mock_dir: Path, frontend: str):
        self.mock_dir = mock_dir
        self.frontend = frontend
        if not mock_dir.is_dir():
            raise SystemExit(f"mock_dir {mock_dir} not found")
        self.frontend_dir = mock_dir / frontend
        if not self.frontend_dir.is_dir():
            raise SystemExit(
                f"mock fixture for frontend={frontend} missing: {self.frontend_dir}")

    def chat(self, messages: list[dict]) -> str:
        turn = sum(1 for m in messages if m.get("role") == "assistant")
        candidate = self.frontend_dir / f"turn_{turn}.txt"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        return ("[mock-llm] No more pre-recorded turns; returning empty "
                "response so the trial harness terminates.")


# --------------------------------------------------------------------------
# Real provider stubs (optional dependencies).
# --------------------------------------------------------------------------
class OpenAIClient(LLMClient):
    name = "openai"

    def __init__(self, model: str, api_key: str, base_url: str | None,
                 temperature: float = 0.0, max_tokens: int = 8192):
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise SystemExit(
                "provider=openai requires `pip install openai>=1.0`") from e
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def chat(self, messages: list[dict]) -> str:
        rsp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return rsp.choices[0].message.content or ""


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, model: str, api_key: str, base_url: str | None,
                 temperature: float = 0.0, max_tokens: int = 8192):
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as e:
            raise SystemExit(
                "provider=anthropic requires `pip install anthropic>=0.40`") from e
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = Anthropic(**kwargs)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def chat(self, messages: list[dict]) -> str:
        # Anthropic separates system from user messages.
        system_chunks = [m["content"] for m in messages if m.get("role") == "system"]
        user_msgs = [m for m in messages if m.get("role") != "system"]
        rsp = self._client.messages.create(
            model=self._model,
            system="\n\n".join(system_chunks) or None,
            messages=user_msgs,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        # Each content block is a TextBlock; concatenate.
        return "".join(getattr(b, "text", "") for b in rsp.content)


# --------------------------------------------------------------------------
# Factory.
# --------------------------------------------------------------------------
def make_client(config: dict[str, Any], frontend: str, case_dir: Path) -> LLMClient:
    provider = str(config.get("provider", "mock")).lower()
    if provider == "mock":
        mock_dir = case_dir / str(config.get("mock_dir", "scripts/mock_llm"))
        return MockClient(mock_dir, frontend)
    if provider in {"openai", "anthropic"}:
        api_key_env = str(config.get("api_key_env", "OPENAI_API_KEY"))
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise SystemExit(
                f"provider={provider} requires env var {api_key_env}; "
                f"set it or switch to provider=mock in llm.yaml")
        base_url_env = str(config.get("api_base_env", "")) or None
        base_url = os.environ.get(base_url_env) if base_url_env else None
        model = str(config.get("model", ""))
        if not model:
            raise SystemExit(f"provider={provider} requires `model` in llm.yaml")
        kwargs = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": float(config.get("temperature", 0.0)),
            "max_tokens": int(config.get("max_tokens", 8192)),
        }
        if provider == "openai":
            return OpenAIClient(**kwargs)
        return AnthropicClient(**kwargs)
    raise SystemExit(f"unknown provider {provider!r}")


# --------------------------------------------------------------------------
# Helpers used by the trial harness.
# --------------------------------------------------------------------------
FILE_BLOCK_RE = re.compile(
    r'<file\s+path\s*=\s*"([^"\n]+)"\s*>\n(.*?)\n</file>',
    re.DOTALL,
)


def extract_files(response: str) -> list[tuple[str, str]]:
    """Extract <file path="..."> ... </file> blocks from an LLM response.

    Returns a list of (relpath, content) pairs, in source order.
    Empty list if the response contains no file blocks (the harness then
    treats the turn as "no progress" and stops the loop).
    """
    out: list[tuple[str, str]] = []
    for m in FILE_BLOCK_RE.finditer(response):
        out.append((m.group(1).strip(), m.group(2)))
    return out


def approx_token_count(text: str) -> int:
    """Cheap heuristic: 1 token ≈ 4 chars or 0.75 words, whichever is bigger.

    Used only to enforce ``prompt_token_budget`` in the harness; not a
    billing-grade estimate.
    """
    n_chars = len(text)
    n_words = len(re.findall(r"\S+", text))
    return max(n_chars // 4, int(n_words * 0.75) + 1)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--smoke":
        # Minimal smoke for the mock route.
        cfg_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        if cfg_path is None:
            print("usage: llm_client.py --smoke <path-to-llm.yaml>", file=sys.stderr)
            sys.exit(2)
        cfg = load_config(cfg_path)
        case_dir = cfg_path.resolve().parent.parent
        client = make_client(cfg, "pysmt", case_dir)
        print(f"client = {client.name}")
        rsp = client.chat([{"role": "user", "content": "hi"}])
        print(f"first 200 chars of response: {rsp[:200]!r}")
        files = extract_files(rsp)
        print(f"file blocks: {[name for name, _ in files]}")
        sys.exit(0)
    print("llm_client is a library; use --smoke to test the mock route.",
          file=sys.stderr)
    sys.exit(2)
