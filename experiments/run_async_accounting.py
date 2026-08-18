"""Asynchronous accounting: what changes when settlement is decoupled from execution?

Both existing backends settle before the response completes. This experiment adds the case
the paper could otherwise be accused of avoiding: the gateway emits a usage event and a
*continuously running* worker applies it after a controlled delay `D`.

The worker must actually run. An earlier version of this harness drained the queue
manually, which made the measurement meaningless in two ways: the "exposure window" was
just however long the experimenter waited before draining, and the reconciliation delay
had no observable effect at all because no debit ever landed while requests were in
flight. Both numbers are only meaningful against a live worker.

Three questions, each with a prediction stated before the run so the result can refute it:

  M1  Does the delay create a window in which delivered value carries no debit?
      PREDICTION: yes, with mean window ~D. The question that matters is whether correct
      reconciliation still CLOSES it -- i.e. whether async accounting is merely *late* or
      actually *lossy*.

  B0  Does decoupling change the NATURE of the shared-credit race?
      PREDICTION: yes. The synchronous race needs two transactions to overlap by
      microseconds. Here authorization reads a committed balance that is simply out of
      date for D milliseconds, so over-serving should depend on D relative to the
      inter-arrival time -- an architectural window rather than a timing race. Requests
      are therefore issued SEQUENTIALLY, spaced by a fixed interval: any over-serving
      cannot be a concurrency race, because there is no concurrency.

  M2  Does asynchrony change the effect of non-authoritative usage?
      PREDICTION: no. The billed amount is a pure function of one request's declared
      usage, computed before any balance is read, so when it is applied cannot matter.

Usage:
    python -m experiments.run_async_accounting --reps 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
BASE = "http://localhost:8000"

PROMPT = "asynchronous accounting exposure window measurement prompt for the testbed"
SEED = 1337
TIER = "medium"

DELAYS_MS = [0.0, 10.0, 50.0, 100.0, 500.0]
M1_FAULTS = ["none", "lost_event", "duplicate_event", "delayed_event", "abort_before_event"]
# Sequential arrivals, 20 ms apart: a delay below this is fully reconciled before the next
# request authorizes; a delay above it is not.
B0_INTERARRIVAL_MS = 20.0
B0_REQUESTS = 6
WORKER_POLL_MS = 2.0


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


async def new_account(c: httpx.AsyncClient, credits: float,
                      mechanism: str = "m1", architecture: str = "post_completion"):
    acct = (await c.post("/admin/accounts",
                         json={"name": f"async-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
    t = (await c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": mechanism, "architecture": architecture,
        "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
        "initial_credits": credits})).json()
    return acct["id"], acct["api_key"], t["trial_id"]


async def live_balance(c: httpx.AsyncClient, account_id: int) -> Decimal:
    return D((await c.get(f"/admin/async/balance/{account_id}")).json()["balance"])


async def worker(c: httpx.AsyncClient, on: bool, poll_ms: float = WORKER_POLL_MS) -> dict:
    path = "/admin/async/worker/start" if on else "/admin/async/worker/stop"
    r = await c.post(path, params={"poll_ms": poll_ms} if on else None)
    return r.json()


async def worker_stats(c: httpx.AsyncClient) -> dict:
    return (await c.get("/admin/async/worker/stats")).json()


async def stream_abort(c, key, trial_id, delay_ms, fault, abort_at):
    rid = uuid.uuid4().hex
    payload = {"prompt": PROMPT, "trial_id": trial_id, "seed": SEED, "request_id": rid,
               "reconcile_delay_ms": delay_ms, "fault": fault}
    read = 0
    try:
        async with c.stream("POST", "/async/m1/stream", headers={"X-API-Key": key},
                            json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: token_"):
                    read += 1
                    if abort_at is not None and read >= abort_at:
                        break
                elif line.startswith("data: [DONE]"):
                    break
    except httpx.HTTPError:
        pass
    return rid, read


async def run_m1(c: httpx.AsyncClient, reps: int) -> list[dict]:
    out = []
    print("\nM1 under asynchronous settlement (abort at 20 tokens, worker running)")
    print(f"  {'delay':>7} {'fault':<20}{'delivered$':>12}{'charged$':>11}"
          f"{'leak$':>10}{'window ms':>11}{'reconciled':>12}")
    for delay in DELAYS_MS:
        for fault in M1_FAULTS:
            await c.post("/admin/async/reset")
            await worker(c, True)
            acct_id, key, tid = await new_account(c, credits=1000.0)
            start = await live_balance(c, acct_id)

            for _ in range(reps):
                await stream_abort(c, key, tid, delay, fault, abort_at=20)

            audit = (await c.get(f"/admin/m-trials/{tid}/audit")).json()
            delivered_value = sum(D(r["authoritative_cost"]) for r in audit["rows"])

            # Give the worker generous time to converge: 4x the delay plus a floor. A
            # `delayed_event` straggler (1 s) deliberately exceeds this for the small
            # delays, which is exactly what makes it a straggler.
            await asyncio.sleep(max(0.4, (delay * 4) / 1000.0))
            st = await worker_stats(c)
            await worker(c, False)

            charged = start - await live_balance(c, acct_id)
            leak = delivered_value - charged
            w = st["exposure_window_ms"]
            win = "-" if w["mean"] is None else f"{w['mean']:.1f}"
            out.append({
                "mechanism": "m1", "delay_ms": delay, "fault": fault, "reps": reps,
                "delivered_value": str(delivered_value), "charged": str(charged),
                "leak": str(leak), "reconciled": leak == 0,
                "exposure_window_ms": w, "queue_depth_after": st["queue_depth"],
                "duplicates_suppressed": st["duplicates_suppressed"],
                "applied": st["applied"],
            })
            print(f"  {delay:>6.0f}ms {fault:<20}{str(delivered_value):>12}"
                  f"{str(charged):>11}{str(leak):>10}"
                  f"{win:>11}"
                  f"{('yes' if leak == 0 else 'NO'):>12}")
    return out


async def run_b0(c: httpx.AsyncClient) -> list[dict]:
    """Sequential arrivals: any over-serving here is architectural, not a timing race."""
    out = []
    print(f"\nB0 under asynchronous settlement -- SEQUENTIAL arrivals "
          f"{B0_INTERARRIVAL_MS:.0f} ms apart, budget = 2 requests")
    print(f"  {'delay':>7}{'issued':>8}{'served':>8}{'affordable':>12}"
          f"{'over-served':>13}{'final bal':>12}")
    # Establish the unit cost once, on a throwaway account.
    await c.post("/admin/async/reset")
    pid, pkey, ptid = await new_account(c, credits=1000.0)
    unit = D((await c.post("/async/b0/complete", headers={"X-API-Key": pkey},
                           json={"prompt": PROMPT, "trial_id": ptid, "seed": SEED,
                                 "reconcile_delay_ms": 0.0})).json()["cost"])

    for delay in DELAYS_MS:
        await c.post("/admin/async/reset")
        await worker(c, True)
        acct_id, key, tid = await new_account(c, credits=float(unit * 2))
        served = 0
        for _ in range(B0_REQUESTS):
            r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                              json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                    "reconcile_delay_ms": delay})).json()
            served += 1 if r.get("served") else 0
            await asyncio.sleep(B0_INTERARRIVAL_MS / 1000.0)
        await asyncio.sleep(max(0.4, (delay * 4) / 1000.0))
        await worker(c, False)
        final = await live_balance(c, acct_id)
        out.append({"mechanism": "b0", "delay_ms": delay, "interarrival_ms": B0_INTERARRIVAL_MS,
                    "issued": B0_REQUESTS, "served": served, "affordable": 2,
                    "over_served": max(0, served - 2), "unit_cost": str(unit),
                    "final_balance": str(final)})
        print(f"  {delay:>6.0f}ms{B0_REQUESTS:>8}{served:>8}{2:>12}"
              f"{max(0, served - 2):>13}{str(final):>12}")
    return out


async def run_m2(c: httpx.AsyncClient, reps: int) -> list[dict]:
    out = []
    print("\nM2 under asynchronous settlement (prediction: unchanged)")
    for delay in [0.0, 100.0, 500.0]:
        await c.post("/admin/async/reset")
        await worker(c, True)
        acct = (await c.post("/admin/accounts",
                             json={"name": f"a-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
        t = (await c.post("/admin/m-trials", json={
            "account_id": acct["id"], "mechanism": "m2", "architecture": "client",
            "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
            "initial_credits": 100000.0})).json()
        effs = []
        for _ in range(reps):
            b = (await c.post("/m2/complete", headers={"X-API-Key": acct["api_key"]},
                              json={"prompt": PROMPT, "trial_id": t["trial_id"],
                                    "manipulation": "under_report_output_90"})).json()
            effs.append(float(D(b["leak"]) / D(b["authoritative_cost"])))
        await worker(c, False)
        eff = sum(effs) / len(effs)
        out.append({"mechanism": "m2", "delay_ms": delay, "leakage_efficiency": eff})
        print(f"  delay={delay:>5.0f}ms  leakage efficiency={eff:+.4f}")
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=BASE, timeout=300.0) as c:
        try:
            m1 = await run_m1(c, args.reps)
            b0 = await run_b0(c)
            m2 = await run_m2(c, args.reps)
        finally:
            await worker(c, False)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"async_accounting_{stamp}.json"
    out.write_text(json.dumps({
        "experiment": "async_accounting",
        "generated_at": stamp,
        "parameters": {"prompt": PROMPT, "seed": SEED, "price_tier": TIER,
                       "reps": args.reps, "delays_ms": DELAYS_MS,
                       "m1_faults": M1_FAULTS,
                       "b0_interarrival_ms": B0_INTERARRIVAL_MS,
                       "b0_requests": B0_REQUESTS,
                       "worker_poll_ms": WORKER_POLL_MS},
        "m1": m1, "b0": b0, "m2": m2,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {out}")


if __name__ == "__main__":
    asyncio.run(main())
