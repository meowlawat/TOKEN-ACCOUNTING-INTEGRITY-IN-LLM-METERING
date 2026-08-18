"""Adapter to a real, third-party OpenAI-compatible inference server.

The mock generator exists so that token counts are a pure function of `(prompt, seed)`,
which makes the accounting arithmetic exact and the experiments reproducible. That is the
right default, but it means every headline number was produced against a generator we
wrote. This adapter closes that gap: the same gateway code, the same architectures, the
same accounting and the same integrity gates, driven by a serving stack we did not write.

Upstream is `llama.cpp`'s `llama-server` (a widely deployed self-hosted OpenAI-compatible
server) running SmolLM2-135M-Instruct on CPU. What matters for this study is not the model
quality but that the *usage record and the streaming behaviour are produced by real
serving code*:

  * `prompt_tokens` comes from the server's own tokenizer, not from a word count;
  * `completion_tokens` is whatever the model actually emitted -- it is NOT knowable
    before generation, so a reservation must be made against an upper bound;
  * `prompt_tokens_details.cached_tokens` is a real prefix-cache split that varies
    between otherwise identical requests -- a category the client genuinely cannot
    predict, which is exactly the K1 knowledge level in our attacker model;
  * the stream is real SSE over a real socket, so a mid-stream abort exercises the real
    cancellation path rather than a simulated one.

Everything here is read-only with respect to the accounting logic. Selecting this
generator changes *where tokens come from* and nothing else; with the default
(`generator="mock"`) not a single byte of behaviour changes, which is what lets the
existing corpus stand unmodified.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

# Host-side server reached from inside the container; overridable for local runs.
BASE_URL = os.getenv("REAL_LLM_URL", "http://host.docker.internal:8899")
MODEL = os.getenv("REAL_LLM_MODEL", "smollm2")
TIMEOUT = float(os.getenv("REAL_LLM_TIMEOUT", "120"))


@dataclass
class RealUsage:
    """A usage record as reported by the upstream server."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0  # SmolLM2 exposes none; kept for interface parity
    finish_reason: str | None = None
    raw: dict = field(default_factory=dict)


class UpstreamUnavailable(RuntimeError):
    """Raised when the real serving stack is not reachable."""


async def health() -> dict:
    async with httpx.AsyncClient(timeout=5.0) as c:
        try:
            r = await c.get(f"{BASE_URL}/health")
            r.raise_for_status()
            props = {}
            try:
                props = (await c.get(f"{BASE_URL}/props")).json()
            except Exception:  # noqa: BLE001 - /props is optional
                pass
            return {"reachable": True, "base_url": BASE_URL,
                    "model": props.get("model_path", MODEL),
                    "status": r.json()}
        except Exception as exc:  # noqa: BLE001
            raise UpstreamUnavailable(f"{BASE_URL}: {exc}") from exc


async def count_prompt_tokens(prompt: str) -> int:
    """Server-side tokenization via the upstream's own tokenizer.

    This is the authoritative input count: it never trusts a client-declared value, and
    unlike the mock's whitespace word count it is a real BPE tokenization, so the input
    token count no longer coincides with anything the client can trivially compute.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(f"{BASE_URL}/tokenize", json={"content": prompt})
        r.raise_for_status()
        return max(1, len(r.json().get("tokens", [])))


async def complete(prompt: str, seed: int, max_tokens: int) -> tuple[str, RealUsage]:
    """Non-streaming completion. Returns (text, usage-as-reported-by-the-server)."""
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0, "seed": seed}
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(f"{BASE_URL}/v1/chat/completions", json=body)
        r.raise_for_status()
        d = r.json()
    u = d.get("usage", {})
    return d["choices"][0]["message"]["content"], RealUsage(
        input_tokens=int(u.get("prompt_tokens", 0)),
        output_tokens=int(u.get("completion_tokens", 0)),
        cached_input_tokens=int((u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)),
        finish_reason=d["choices"][0].get("finish_reason"),
        raw=u,
    )


async def stream(prompt: str, seed: int, max_tokens: int) -> AsyncIterator[tuple[str, RealUsage | None]]:
    """Stream real SSE deltas.

    Yields `(text_delta, None)` per token and finally `("", usage)` once the upstream
    reports its usage record. If the consumer stops iterating (a client disconnect), the
    upstream connection is closed by the context manager and no usage record arrives --
    which is precisely the M1 condition being studied, now occurring for real rather than
    by construction.
    """
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0, "seed": seed,
            "stream": True, "stream_options": {"include_usage": True}}
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        async with c.stream("POST", f"{BASE_URL}/v1/chat/completions", json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    d = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if d.get("usage"):
                    u = d["usage"]
                    yield "", RealUsage(
                        input_tokens=int(u.get("prompt_tokens", 0)),
                        output_tokens=int(u.get("completion_tokens", 0)),
                        cached_input_tokens=int((u.get("prompt_tokens_details") or {})
                                                .get("cached_tokens", 0)),
                        raw=u)
                    continue
                for ch in d.get("choices", []):
                    delta = (ch.get("delta") or {}).get("content")
                    if delta:
                        yield delta, None
