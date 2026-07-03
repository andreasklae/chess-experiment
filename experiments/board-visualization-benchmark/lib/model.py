"""Thin, logged client over the eX3 vLLM endpoint (and optionally others).

Reuses the same connection the chess experiment uses: an OpenAI-compatible
endpoint at SKILL_AGENT_EX3_BASE_URL serving google/gemma-4-31B-it, api_key
'dummy'. No pydantic-ai / tool-calling machinery — the benchmark only needs
plain chat completions.

Every call is timestamped and returned with metadata so the runners can write
a complete JSONL audit trail (prompt in, raw text out) from the start.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import openai

# Load the chess backend .env so SKILL_AGENT_EX3_BASE_URL etc. are available
# when this is run standalone (not under the backend process).
_BACKEND_ENV = Path(__file__).resolve().parents[3] / "backend" / ".env"


def _load_env() -> None:
    if not _BACKEND_ENV.exists():
        return
    for line in _BACKEND_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


_load_env()


@dataclass
class ModelSpec:
    id: str                 # short label used in results, e.g. 'gemma-31b'
    model_name: str         # API model id
    base_url: str | None    # None => public OpenAI
    api_key: str = "dummy"


def gemma_spec() -> ModelSpec:
    return ModelSpec(
        id="gemma-31b",
        model_name=os.getenv("SKILL_AGENT_OPENAI_MODEL", "google/gemma-4-31B-it"),
        base_url=os.getenv("SKILL_AGENT_EX3_BASE_URL", "http://localhost:11500/v1"),
    )


@dataclass
class CallResult:
    text: str
    ok: bool
    error: str | None
    latency_s: float
    finish_reason: str | None


class Client:
    def __init__(self, spec: ModelSpec):
        self.spec = spec
        self._c = openai.OpenAI(base_url=spec.base_url, api_key=spec.api_key)

    def chat(self, prompt: str, *, temperature: float, max_tokens: int,
             system: str | None = None, retries: int = 3) -> CallResult:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        last_err = None
        for attempt in range(retries):
            t0 = time.time()
            try:
                r = self._c.chat.completions.create(
                    model=self.spec.model_name, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                )
                ch = r.choices[0]
                return CallResult(
                    text=ch.message.content or "",
                    ok=True, error=None,
                    latency_s=round(time.time() - t0, 3),
                    finish_reason=ch.finish_reason,
                )
            except Exception as e:  # network / 400 / timeout
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(1.5 * (attempt + 1))
        return CallResult(text="", ok=False, error=last_err, latency_s=0.0,
                          finish_reason=None)


if __name__ == "__main__":
    c = Client(gemma_spec())
    print(c.chat("Say 'ok'.", temperature=0, max_tokens=5))
