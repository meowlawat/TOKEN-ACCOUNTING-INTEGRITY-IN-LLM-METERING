"""Deterministic workload text generation + exact-token-length construction.

CRITICAL INVARIANT enforced here: for a given tokenizer, the produced text must
satisfy ``len(encode(text)) == target_length`` EXACTLY. The same text does *not*
produce the same token count across tokenizers, so every (tokenizer, workload,
length) cell gets its own constructed input, and construction failures are recorded
as failures rather than silently accepted.

Three workload families (all seeded, hence reproducible):
  * ``natural``      -- English prose assembled from a fixed word bank.
  * ``code``         -- structured/code-like text (Python/JSON-ish).
  * ``high_entropy`` -- random alphanumeric/byte-ish strings (worst case for BPE:
                        near-1-token-per-character, exercises byte fallback).
"""

from __future__ import annotations

import random
import string
from typing import Callable

# --- Fixed vocabularies (no external corpus download; fully reproducible) ----- #
_WORDS = (
    "the model streams a token then another under test with deterministic timing for "
    "reproducible billing and metering research on commodity hardware without gpu "
    "inference accounting integrity requires that every served response corresponds to "
    "a committed debit which the gateway must record before the client disconnects "
    "because usage based pricing depends on an authoritative count of prompt and "
    "completion tokens produced by the language model during generation"
).split()

_CODE_SNIPPETS = [
    'def compute_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:',
    '    """Return the server-side recomputed cost of a completion."""',
    '    return (D(prompt_tokens) / 1000 * price_in + D(completion_tokens) / 1000 * price_out)',
    'class UsageRecord(Base):',
    '    __tablename__ = "usage_records"',
    '    id: Mapped[int] = mapped_column(Integer, primary_key=True)',
    'if balance is None or balance < est_cost:',
    '    raise HTTPException(status_code=402, detail="insufficient credits")',
    '{"input_tokens": 128, "output_tokens": 512, "cached_input_tokens": 0}',
    'UPDATE credits SET balance = balance - :c WHERE account_id = :a AND balance >= :c;',
    'for i, token in enumerate(stream_completion(prompt, seed=1337)):',
    '    await asyncio.sleep(inter_token_delay_ms / 1000.0)',
    'SELECT balance FROM credits WHERE account_id = $1 FOR UPDATE;',
    'assert len(enc.encode(text)) == target_length, "exact-length invariant violated"',
]


def gen_natural(rng: random.Random, approx_chars: int) -> str:
    out: list[str] = []
    n = 0
    while n < approx_chars:
        w = rng.choice(_WORDS)
        out.append(w)
        n += len(w) + 1
    text = " ".join(out)
    # sentence structure
    return text[0].upper() + text[1:] + "."


def gen_code(rng: random.Random, approx_chars: int) -> str:
    out: list[str] = []
    n = 0
    while n < approx_chars:
        line = rng.choice(_CODE_SNIPPETS)
        out.append(line)
        n += len(line) + 1
    return "\n".join(out)


def gen_high_entropy(rng: random.Random, approx_chars: int) -> str:
    alphabet = string.ascii_letters + string.digits + "+/=_-"
    return "".join(rng.choice(alphabet) for _ in range(approx_chars))


_JSON_KEYS = ("request_id", "account_id", "model", "input_tokens", "output_tokens",
              "cached_input_tokens", "reasoning_tokens", "total_tokens", "cost",
              "posture", "architecture", "committed", "refunded", "created_at")
_JSON_VALS = ("gpt-mini", "llama-3.2-3b", "true", "false", "null", "server_recount",
              "client_total", "reserve_reconcile", "2026-08-16T11:00:00Z")


def gen_json(rng: random.Random, approx_chars: int) -> str:
    """Structured JSON-like payloads (punctuation/quote dense, very different BPE profile)."""
    out: list[str] = []
    n = 0
    while n < approx_chars:
        fields = []
        for _ in range(rng.randint(3, 8)):
            k = rng.choice(_JSON_KEYS)
            if rng.random() < 0.5:
                v = str(rng.randint(0, 999999))
            else:
                v = '"' + rng.choice(_JSON_VALS) + '"'
            fields.append(f'"{k}": {v}')
        obj = "{" + ", ".join(fields) + "}"
        out.append(obj)
        n += len(obj) + 2
    return "[" + ",\n".join(out) + "]"


GENERATORS: dict[str, Callable[[random.Random, int], str]] = {
    "natural": gen_natural,
    "code": gen_code,
    "json": gen_json,
    "high_entropy": gen_high_entropy,
}


class ExactLengthError(RuntimeError):
    """Raised when a text of exactly `target` tokens could not be constructed."""


def build_exact_length_text(
    workload: str,
    target: int,
    encode: Callable[[str], list],
    decode: Callable[[list], str],
    seed: int,
    max_iters: int = 400,
) -> str:
    """Construct text whose token count under ``encode`` is EXACTLY ``target``.

    Strategy: generate an over-long corpus, truncate in *token* space, decode back
    to text, then repair — decode/encode round-trips are not always stable (byte
    fallback, merge boundaries), so we iterate until the invariant holds, and finally
    fine-tune by appending/removing single characters.
    """
    rng = random.Random(f"{workload}:{target}:{seed}")
    gen = GENERATORS[workload]

    # Generous character budget: high-entropy is ~1 token/char worst case; natural
    # text is ~4 chars/token. Over-generate, then truncate in token space.
    chars_per_token = 1.6 if workload == "high_entropy" else 6.0
    corpus = gen(rng, int(target * chars_per_token) + 512)

    ids = encode(corpus)
    guard = 0
    while len(ids) < target and guard < 12:
        corpus = corpus + "\n" + gen(rng, int(target * chars_per_token) + 512)
        ids = encode(corpus)
        guard += 1
    if len(ids) < target:
        raise ExactLengthError(f"corpus too short for target={target} ({workload})")

    # Coarse convergence in token space.
    cut = target
    text = decode(ids[:cut])
    cur = len(encode(text))
    for _ in range(max_iters):
        if cur == target:
            break
        cut += (target - cur)
        cut = max(1, min(cut, len(ids)))
        text = decode(ids[:cut])
        cur = len(encode(text))

    # Fine-tune: append a filler char (usually merges to <=1 token) or trim chars.
    filler = "a" if workload == "high_entropy" else " the"
    for _ in range(max_iters):
        if cur == target:
            break
        if cur < target:
            text = text + filler
        else:
            text = text[:-1]
            if not text:
                raise ExactLengthError(f"trimmed to empty for target={target} ({workload})")
        cur = len(encode(text))

    if cur != target:
        raise ExactLengthError(
            f"could not hit exact target={target} for {workload} (got {cur})"
        )
    return text
