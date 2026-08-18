"""External-validity experiment: the same architectures against a REAL serving stack.

Every headline number in this study was produced against a deterministic generator we
wrote. That is the right default -- it makes the accounting arithmetic exact and the
experiments reproducible -- but it leaves one obvious reviewer objection open: are the
architectural conclusions an artifact of our own generator?

This experiment answers that by changing exactly one thing. The gateway code, the
architecture definitions, the accounting backends, the settlement logic and the integrity
gates are identical; only the token source changes, from the mock generator to
`llama.cpp`'s `llama-server` running SmolLM2-135M-Instruct on CPU (see
`app/llm/real_server.py`). The upstream is third-party serving code we did not write, it
tokenizes with a real BPE tokenizer, it decides for itself how many tokens to emit, and
it reports a real prefix-cache split.

What we expect to change: the absolute numbers. Token mixes differ, so leakage
*efficiency* differs.

What must NOT change if the paper's claims are sound: which architectures leak. A
vulnerable architecture must still leak and a safe one must still leak nothing. Anything
else is a finding against us, and is reported as such.

Usage:
    python -m experiments.run_real_stack --reps 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
BASE = "http://localhost:8000"

PROMPT = "List three primary colours and explain briefly why they are called primary."

M1_ARCHES = ["post_completion", "reserve_refund_on_abort", "reserve_reconcile", "pre_debit"]
M1_ABORTS = [("abort50", 0.5), ("abort90", 0.9), ("complete", None)]

M2_ARCHES = ["client", "client_logged", "client_total", "server_recount",
             "hybrid_reconcile", "upstream"]
M2_MANIPS = ["honest", "under_report_output_50", "under_report_output_90",
             "under_report_input_50", "rounding_shave", "total_mismatch",
             "inflate_cached", "drop_reasoning"]

SEED = 1337
MAX_TOKENS = 48
TIER = "medium"
INITIAL = "1000000"


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


async def make_account(c: httpx.AsyncClient) -> tuple[int, str]:
    r = await c.post("/admin/accounts", json={"name": f"real-{uuid.uuid4().hex[:8]}",
                                              "balance": 0.0})
    r.raise_for_status()
    d = r.json()
    return d["id"], d["api_key"]


async def make_trial(c: httpx.AsyncClient, account_id: str, mech: str, arch: str) -> str:
    r = await c.post("/admin/m-trials", json={
        "account_id": account_id, "mechanism": mech, "architecture": arch,
        "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
        "initial_credits": float(INITIAL)})
    r.raise_for_status()
    return r.json()["trial_id"]


async def stream_real(c: httpx.AsyncClient, key: str, trial_id: str,
                      abort_frac: float | None) -> tuple[str, int]:
    """Open a real SSE stream and abort after a fraction of the token budget.

    Unlike the mock harness this cannot match on a `token_` prefix -- the deltas are real
    model text -- so it counts any data frame that is not the terminator.
    """
    rid = uuid.uuid4().hex
    payload = {"prompt": PROMPT, "seed": SEED, "trial_id": trial_id, "request_id": rid,
               "generator": "real", "max_tokens": MAX_TOKENS}
    stop_at = None if abort_frac is None else max(1, int(MAX_TOKENS * abort_frac))
    read = 0
    try:
        async with c.stream("POST", "/m1/stream", headers={"X-API-Key": key},
                            json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                if line.startswith("data: [DONE]"):
                    break
                read += 1
                if stop_at is not None and read >= stop_at:
                    break  # abort: leaving the context closes the connection
    except httpx.HTTPError:
        pass
    return rid, read


async def trial_rows(c: httpx.AsyncClient, trial_id: str) -> list[dict]:
    """Per-request rows for a trial, via the same audit endpoint the mock runners use."""
    r = await c.get(f"/admin/m-trials/{trial_id}/audit")
    r.raise_for_status()
    return r.json()["rows"]


async def run_m1(c: httpx.AsyncClient, account_id: str, key: str, reps: int) -> list[dict]:
    trials = []
    for arch in M1_ARCHES:
        for label, frac in M1_ABORTS:
            tid = await make_trial(c, account_id, "m1", arch)
            issued = []
            for _ in range(reps):
                rid, read = await stream_real(c, key, tid, frac)
                issued.append((rid, read))
            await asyncio.sleep(0.4)  # let cancellation-shielded settlements land
            by_id = {rid: read for rid, read in issued}
            records = [dict(r, client_read=by_id.get(r["request_id"]))
                       for r in await trial_rows(c, tid)
                       if r["request_id"] in by_id]
            trials.append({"mechanism": "m1", "architecture": arch, "abort": label,
                           "records": records})
            served = [r for r in records if r["served"]]
            leak = sum(D(r["leak"]) for r in served)
            print(f"  M1 {arch:<26}{label:<10} n={len(records):<3} "
                  f"leak={leak} delivered={[r['tokens_delivered'] for r in records]}")
    return trials


async def run_m2(c: httpx.AsyncClient, account_id: str, key: str, reps: int) -> list[dict]:
    trials = []
    for arch in M2_ARCHES:
        tid = await make_trial(c, account_id, "m2", arch)
        for manip in M2_MANIPS:
            records = []
            for _ in range(reps):
                rid = uuid.uuid4().hex
                r = await c.post("/m2/complete", headers={"X-API-Key": key}, json={
                    "prompt": PROMPT, "seed": SEED, "trial_id": tid, "request_id": rid,
                    "manipulation": manip, "generator": "real", "max_tokens": MAX_TOKENS})
                if r.status_code == 200:
                    records.append(r.json())
            if not records:
                continue
            auth = sum(D(r["authoritative_cost"]) for r in records)
            leak = sum(D(r["leak"]) for r in records)
            eff = float(leak / auth) if auth > 0 else 0.0
            trials.append({"mechanism": "m2", "architecture": arch, "manipulation": manip,
                           "records": records, "leakage_efficiency": eff})
            print(f"  M2 {arch:<18}{manip:<26} n={len(records):<3} eff={eff:+.4f}")
    return trials


def upstream_variance(trials: list[dict]) -> dict:
    """Did the real stack report stable usage for identical requests?

    This is not a formality. A real serving stack's cached-token split depends on what
    else it has recently seen, so identical requests can carry different usage vectors --
    which is a genuine source of accounting nondeterminism the mock generator cannot
    exhibit.
    """
    outs, ins, cached = [], [], []
    for t in trials:
        for r in t["records"]:
            u = (r.get("extra") or {}).get("upstream_usage") or {}
            if u:
                ins.append(u.get("prompt_tokens"))
                outs.append(u.get("completion_tokens"))
                cached.append((u.get("prompt_tokens_details") or {}).get("cached_tokens"))

    def stat(xs):
        xs = [x for x in xs if x is not None]
        if not xs:
            return {}
        return {"n": len(xs), "distinct": sorted(set(xs)),
                "mean": round(statistics.fmean(xs), 3),
                "stdev": round(statistics.pstdev(xs), 3)}
    return {"prompt_tokens": stat(ins), "completion_tokens": stat(outs),
            "cached_tokens": stat(cached)}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=BASE, timeout=180.0) as c:
        health = (await c.get("/admin/real-stack")).json()
        if not health.get("reachable"):
            raise SystemExit(f"real serving stack unreachable: {health}")
        print(f"upstream: {health['model']} @ {health['base_url']}")

        account_id, key = await make_account(c)
        print(f"\nM1 -- commitment timing against real streaming inference")
        m1 = await run_m1(c, account_id, key, args.reps)
        print(f"\nM2 -- usage authority against real usage records")
        m2 = await run_m2(c, account_id, key, args.reps)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RAW / f"real_stack_{stamp}.json"
    RAW.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "real_stack_external_validity",
        "generated_at": stamp,
        "upstream": health,
        "parameters": {"prompt": PROMPT, "seed": SEED, "max_tokens": MAX_TOKENS,
                       "price_tier": TIER, "reps": args.reps},
        "upstream_usage_variance": upstream_variance(m1 + m2),
        "trials": m1 + m2,
    }
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nupstream usage variance: "
          f"{json.dumps(payload['upstream_usage_variance'], default=str)}")
    print(f"-> {out}")


if __name__ == "__main__":
    asyncio.run(main())
