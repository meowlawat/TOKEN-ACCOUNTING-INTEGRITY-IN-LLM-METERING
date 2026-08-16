"""Benchmark-only endpoints for measuring gateway-level recount overhead.

Isolates ONE question: what does adding a real server-side tokenizer recount to the
metered request path cost end-to-end (throughput/latency), versus trusting a
client-declared count?

`/bench/complete` runs the same accounting path in both postures:

    read balance -> [optional REAL tokenizer recount] -> atomic debit -> respond

with `recount_engine="none"` (posture A: client-declared, no recount) or a real
engine name (posture B: server-authoritative recount). The response reports the
server-measured tokenization time so it can be separated from total latency.

Tokenizers are loaded lazily from a mounted, pre-populated cache so the container
performs no network access at request time. Engines that do not resolve are simply
absent from `/bench/engines`.
"""

from __future__ import annotations

import time
from decimal import Decimal
from functools import lru_cache

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .accounting import ledger
from .db import get_session
from .models.models import Account

router = APIRouter()

_PRICE_PER_1K = Decimal("1.5")
_CENTS = Decimal("0.000001")


class BenchRequest(BaseModel):
    text: str = Field(..., min_length=1)
    declared_tokens: int = Field(0, ge=0)
    recount_engine: str = "none"   # "none" | tiktoken/cl100k_base | hf/llama | sentencepiece/llama
    do_debit: bool = True


class BenchResponse(BaseModel):
    billed_tokens: int
    recounted: bool
    engine: str
    tokenize_ms: float
    total_server_ms: float
    cost: Decimal


@lru_cache(maxsize=8)
def _get_encoder(name: str):
    """Return an `encode(str)->list` for `name`, or raise. Cached per process."""
    if name.startswith("tiktoken/"):
        import tiktoken
        enc = tiktoken.get_encoding(name.split("/", 1)[1])
        return enc.encode
    if name.startswith("hf/"):
        # Load the FAST (Rust) tokenizer straight from tokenizer.json in the mounted
        # cache: no hub resolution, no network, and it is the backend a production
        # gateway would actually run.
        import glob
        from tokenizers import Tokenizer as RsTokenizer
        hits = glob.glob("/tokcache/hf/hub/models--*/snapshots/*/tokenizer.json")
        if not hits:
            raise FileNotFoundError("tokenizer.json not found in mounted /tokcache")
        rs = RsTokenizer.from_file(sorted(hits)[0])
        return lambda s: rs.encode(s, add_special_tokens=False).ids
    if name.startswith("sentencepiece/"):
        import sentencepiece as spm
        from huggingface_hub import hf_hub_download
        path = hf_hub_download("hf-internal-testing/llama-tokenizer", "tokenizer.model")
        sp = spm.SentencePieceProcessor(model_file=str(path))
        return lambda s: sp.encode(s, out_type=int)
    raise ValueError(f"unknown engine {name}")


@router.get("/bench/engines")
async def bench_engines() -> dict:
    """Report which recount engines actually resolve inside the container."""
    out = {}
    for name in ["tiktoken/cl100k_base", "tiktoken/o200k_base", "hf/llama", "sentencepiece/llama"]:
        try:
            enc = _get_encoder(name)
            n = len(enc("warmup text for engine probe"))
            out[name] = {"available": True, "probe_tokens": n}
        except Exception as e:  # noqa: BLE001
            out[name] = {"available": False, "reason": f"{type(e).__name__}: {str(e)[:120]}"}
    return out


@router.post("/bench/complete", response_model=BenchResponse)
async def bench_complete(
    req: BenchRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> BenchResponse:
    t_start = time.perf_counter()
    account = (
        await session.execute(select(Account).where(Account.api_key == x_api_key))
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(401, "invalid api key")

    tokenize_ms = 0.0
    recounted = False
    if req.recount_engine and req.recount_engine != "none":
        try:
            enc = _get_encoder(req.recount_engine)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"engine unavailable: {e}") from e
        t0 = time.perf_counter()
        billed_tokens = len(enc(req.text))       # SERVER-AUTHORITATIVE recount
        tokenize_ms = (time.perf_counter() - t0) * 1000.0
        recounted = True
    else:
        billed_tokens = req.declared_tokens      # client-declared (posture A)

    cost = (Decimal(billed_tokens) / 1000 * _PRICE_PER_1K).quantize(_CENTS)
    if req.do_debit:
        await ledger.debit_unchecked(session, account.id, cost)
        await session.commit()

    return BenchResponse(
        billed_tokens=billed_tokens, recounted=recounted,
        engine=req.recount_engine, tokenize_ms=tokenize_ms,
        total_server_ms=(time.perf_counter() - t_start) * 1000.0, cost=cost,
    )
