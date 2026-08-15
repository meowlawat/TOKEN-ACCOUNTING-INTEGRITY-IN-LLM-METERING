"""Deterministic mock LLM: streams fake tokens with realistic timing.

Design goals (per CLAUDE.md):
  * Zero GPU, fully reproducible: token counts and text are a pure function of
    ``(prompt, seed)``, so identical requests cost identically -> clean attack math.
  * Realistic timing: tokens are emitted one at a time with an inter-token delay,
    which is exactly the window a stream-abort / credit-race attacker exploits.

``plan_completion`` and ``stream_completion`` share the same deterministic length
function, so the pre-serve cost estimate always equals the post-serve recount for
a given prompt.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator

# Tiny fixed vocabulary; token identity is deterministic, content is irrelevant
# to the accounting experiments (only counts and timing matter).
_VOCAB: tuple[str, ...] = (
    "the", "model", "streams", "a", "token", "then", "another", "under",
    "test", "with", "deterministic", "timing", "for", "reproducible", "billing",
    "and", "metering", "research", "on", "commodity", "hardware", "without", "gpu",
)


def _det_int(text: str, seed: int, lo: int, hi: int) -> int:
    """Deterministic integer in ``[lo, hi]`` derived from ``(seed, text)``."""
    if hi < lo:
        raise ValueError("hi must be >= lo")
    digest = hashlib.sha256(f"{seed}:{text}".encode("utf-8")).hexdigest()
    span = hi - lo + 1
    return lo + (int(digest[:16], 16) % span)


def count_prompt_tokens(prompt: str) -> int:
    """Deterministic mock server-side tokenizer for the prompt.

    Whitespace word count is used as a stand-in for a real BPE tokenizer; it is
    stable and server-side (never trusts a client-declared count).
    """
    return max(1, len(prompt.split()))


def plan_completion(prompt: str, seed: int, min_tokens: int, max_tokens: int) -> int:
    """Return the number of completion tokens this prompt/seed will produce."""
    return _det_int(prompt, seed, min_tokens, max_tokens)


async def stream_completion(
    prompt: str,
    seed: int,
    inter_token_delay_ms: float,
    min_tokens: int,
    max_tokens: int,
) -> AsyncIterator[str]:
    """Yield completion tokens one at a time with a per-token delay.

    The number of tokens equals ``plan_completion(...)`` for the same arguments.
    """
    n = plan_completion(prompt, seed, min_tokens, max_tokens)
    delay_s = max(0.0, inter_token_delay_ms) / 1000.0
    for i in range(n):
        if delay_s:
            await asyncio.sleep(delay_s)
        word = _VOCAB[_det_int(f"{prompt}:{i}", seed, 0, len(_VOCAB) - 1)]
        yield word + " "
