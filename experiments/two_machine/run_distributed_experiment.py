"""Unified two-machine / multi-condition B0 asynchronous-settlement experiment runner.

Supersedes the ad hoc Phase 3 pilot (pilot_same_host_external_worker.py, kept as-is for
its own historical record) with the full harness Phase 7 requires: per-request JSONL
(not only aggregates), run metadata (git commit, host identifiers, config hash), explicit
condition labeling, both arrival patterns kept distinct, and repetitions that are never
silently retried or overwritten.

CONDITIONS (labels only -- this script always talks to whatever gateway is listening at
--base; it is the deployment, driven by scripts/azure/*.sh and the docker-compose.machine*
files, that actually determines which topology a condition label corresponds to):

  C0  single-process / in-process worker (the original published architecture)
  C1  separate worker PROCESS, same host, same clock domain (Phase 3's validated pilot)
  C2  worker on a real separate host (Azure), vulnerable /async/b0/complete
  C3  worker on a real separate host (Azure), ATOMIC /async/b0/complete-atomic

Pass --condition to label the run; this script does not start/stop containers itself,
because which containers need to be running differs by condition in ways that belong to
the deployment scripts, not the measurement code.

ARRIVAL PATTERNS, kept explicit and never conflated:

  sequential  the validated protocol: 6 requests, 20ms apart, budget=2 (B0_REQUESTS,
              B0_INTERARRIVAL_MS unchanged from experiments/run_async_accounting.py)
  concurrent  the same 6-request/budget=2 shape, but fired via asyncio.gather with no
              inter-arrival spacing -- a genuinely different, separately-identified
              workload, never silently substituted for the historical condition

Usage:
    python -m experiments.two_machine.run_distributed_experiment \\
        --condition C0 --arrival sequential --delays 0,10,50,100,500 --reps 10 \\
        --base http://localhost:8000 --endpoint /async/b0/complete
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "experiments" / "two_machine" / "raw"
SUMMARY_DIR = ROOT / "results" / "two_machine"

PROMPT = "asynchronous accounting exposure window measurement prompt for the testbed"
SEED_BASE = 1337
TIER = "medium"

# Historical, validated protocol -- do not change without a documented reason.
B0_INTERARRIVAL_MS = 20.0
B0_REQUESTS = 6
B0_BUDGET_UNITS = 2


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "UNKNOWN"


def git_dirty() -> bool:
    try:
        out = subprocess.run(["git", "status", "--short"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return True  # fail safe: assume dirty if we can't tell


def config_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


async def new_account(c: httpx.AsyncClient, credits: float, seed: int):
    acct = (await c.post("/admin/accounts",
                         json={"name": f"dist-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
    t = (await c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": "m1", "architecture": "post_completion",
        "price_tier": TIER, "seed": seed, "prompt": PROMPT,
        "initial_credits": credits})).json()
    return acct["id"], acct["api_key"], t["trial_id"]


async def live_balance(c: httpx.AsyncClient, account_id: int) -> Decimal:
    return D((await c.get(f"/admin/async/balance/{account_id}")).json()["balance"])


async def queue_state(c: httpx.AsyncClient) -> dict:
    try:
        r = await c.get("/admin/async/state")
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


async def fire_request(c: httpx.AsyncClient, endpoint: str, key: str, trial_id: str,
                       seed: int, delay_ms: float, fault: str) -> dict:
    """One request against the given B0 endpoint. Returns a fully-populated event record."""
    request_id = uuid.uuid4().hex
    t_send = datetime.now(timezone.utc).isoformat()
    try:
        resp = await c.post(endpoint, headers={"X-API-Key": key},
                            json={"prompt": PROMPT, "trial_id": trial_id, "seed": seed,
                                  "request_id": request_id, "reconcile_delay_ms": delay_ms,
                                  "fault": fault})
        t_recv = datetime.now(timezone.utc).isoformat()
        body = resp.json()
        return {
            "request_id": request_id, "http_status": resp.status_code,
            "sent_at_utc": t_send, "received_at_utc": t_recv,
            "served": body.get("served"), "reason": body.get("reason"),
            "cost": body.get("cost"), "balance_seen": body.get("balance_seen"),
            "balance_after": body.get("balance_after"), "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "request_id": request_id, "http_status": None,
            "sent_at_utc": t_send, "received_at_utc": datetime.now(timezone.utc).isoformat(),
            "served": None, "reason": None, "cost": None, "balance_seen": None,
            "balance_after": None, "error": repr(exc),
        }


async def run_cell(c: httpx.AsyncClient, *, endpoint: str, delay_ms: float, arrival: str,
                   rep: int, seed: int, fault: str, run_id: str, jsonl_fh,
                   requests: int = B0_REQUESTS, budget_units: int = B0_BUDGET_UNITS) -> dict:
    """One (delay, arrival, repetition) cell. Writes per-request lines to jsonl_fh as it
    goes (not buffered to the end), and returns the cell summary.

    `requests`/`budget_units` default to the historical validated protocol's values
    (B0_REQUESTS=6, B0_BUDGET_UNITS=2) and only differ when the caller explicitly passes
    --concurrency/--budget (added for the experimental-strengthening phase's Tier 2
    robustness matrix) -- every pre-existing invocation gets byte-identical behavior."""
    await c.post("/admin/async/reset")

    # Establish unit cost via a throwaway, GENEROUSLY funded probe account against the
    # SAME endpoint under test, at D=0, outside the timed sequence -- mirrors
    # experiments/run_async_accounting.py's own probe pattern. A zero/low-balance probe
    # cannot work: /async/b0/complete and /async/b0/complete-atomic only return `cost` in
    # their response when the request is actually served (insufficient-balance responses
    # carry no cost field at all), so the probe account must be funded enough to be served.
    _, probe_key, probe_tid = await new_account(c, credits=1000.0, seed=seed)
    probe = await fire_request(c, endpoint, probe_key, probe_tid, seed, 0.0, "none")
    unit_cost = D(probe.get("cost"))
    if unit_cost == 0:
        raise RuntimeError(f"could not establish unit cost (probe={probe})")
    # Fresh, separately-funded account for the actual timed sequence -- the probe's own
    # effect on its own throwaway account is irrelevant and discarded.
    acct_id, key, tid = await new_account(c, credits=float(unit_cost * budget_units), seed=seed)

    events = []
    if arrival == "sequential":
        for _ in range(requests):
            ev = await fire_request(c, endpoint, key, tid, seed, delay_ms, fault)
            ev["condition_delay_ms"] = delay_ms
            ev["arrival"] = arrival
            ev["run_id"] = run_id
            events.append(ev)
            jsonl_fh.write(json.dumps(ev) + "\n")
            jsonl_fh.flush()
            await asyncio.sleep(B0_INTERARRIVAL_MS / 1000.0)
    elif arrival == "concurrent":
        results = await asyncio.gather(*[
            fire_request(c, endpoint, key, tid, seed, delay_ms, fault)
            for _ in range(requests)
        ])
        for ev in results:
            ev["condition_delay_ms"] = delay_ms
            ev["arrival"] = arrival
            ev["run_id"] = run_id
            events.append(ev)
            jsonl_fh.write(json.dumps(ev) + "\n")
        jsonl_fh.flush()
    else:
        raise ValueError(f"unknown arrival pattern: {arrival}")

    # Convergence wait: generous, scaled to delay, matching the validated protocol.
    await asyncio.sleep(max(0.4, (delay_ms * 4) / 1000.0))

    final_balance = await live_balance(c, acct_id)
    qstate = await queue_state(c)
    served_count = sum(1 for e in events if e.get("served") is True)
    error_count = sum(1 for e in events if e.get("error") is not None)

    return {
        "run_id": run_id, "delay_ms": delay_ms, "arrival": arrival, "rep": rep,
        "seed": seed, "fault": fault, "endpoint": endpoint,
        "unit_cost": str(unit_cost), "issued": requests,
        "served": served_count, "affordable": budget_units,
        "over_served": max(0, served_count - budget_units),
        "final_balance": str(final_balance),
        "queue_state_after": qstate,
        "error_count": error_count,
        "valid": error_count == 0,
        "invalid_reason": None if error_count == 0 else f"{error_count} request(s) errored",
    }


async def main_async(args: argparse.Namespace) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    delays = [float(x) for x in args.delays.split(",")]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_batch_id = f"{args.condition}_{args.arrival}_{stamp}"

    commit = git_commit()
    dirty = git_dirty()
    hostname = socket.gethostname()
    cfg_hash = config_hash(args.condition, args.arrival, args.endpoint, str(delays),
                           str(args.reps), commit)

    manifest = {
        "run_batch_id": run_batch_id,
        "git_commit": commit,
        "git_dirty": dirty,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_a_identifier": hostname,
        "host_a_platform": platform.platform(),
        "python_version": platform.python_version(),
        "condition": args.condition,
        "arrival": args.arrival,
        "endpoint": args.endpoint,
        "base_url": args.base,
        "delays_ms": delays,
        "repetitions_requested": args.reps,
        "b0_interarrival_ms": B0_INTERARRIVAL_MS,
        "b0_requests": args.concurrency,
        "b0_budget_units": args.budget,
        "requests_is_default": args.concurrency == B0_REQUESTS,
        "budget_is_default": args.budget == B0_BUDGET_UNITS,
        "fault": args.fault,
        "config_hash": cfg_hash,
        "notes": args.notes,
    }
    if dirty:
        print("WARNING: working tree is dirty. This run's provenance is weaker -- "
              "recorded honestly in the manifest (git_dirty=true), not hidden.",
              file=sys.stderr)

    jsonl_path = RAW_DIR / f"{run_batch_id}.jsonl"
    manifest_path = RAW_DIR / f"{run_batch_id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Run batch: {run_batch_id}")
    print(f"  condition={args.condition} arrival={args.arrival} endpoint={args.endpoint}")
    print(f"  delays={delays} reps={args.reps} fault={args.fault}")
    print(f"  git_commit={commit}{' (DIRTY)' if dirty else ''}")
    print(f"  raw events -> {jsonl_path}")

    cells: list[dict] = []
    async with httpx.AsyncClient(base_url=args.base, timeout=300.0) as c:
        with open(jsonl_path, "w", encoding="utf-8") as jsonl_fh:
            for delay in delays:
                for rep in range(args.reps):
                    seed = SEED_BASE + rep  # explicit, deterministic, recorded
                    run_id = f"{run_batch_id}_D{delay:g}_rep{rep}"
                    try:
                        cell = await run_cell(
                            c, endpoint=args.endpoint, delay_ms=delay, arrival=args.arrival,
                            rep=rep, seed=seed, fault=args.fault, run_id=run_id,
                            jsonl_fh=jsonl_fh, requests=args.concurrency, budget_units=args.budget,
                        )
                    except Exception as exc:  # noqa: BLE001
                        cell = {
                            "run_id": run_id, "delay_ms": delay, "arrival": args.arrival,
                            "rep": rep, "seed": seed, "valid": False,
                            "invalid_reason": f"cell raised: {exc!r}",
                        }
                        print(f"  [INVALID] D={delay}ms rep={rep}: {exc!r}", file=sys.stderr)
                    cells.append(cell)
                    tag = "OK" if cell.get("valid") else "INVALID"
                    print(f"  D={delay:>6g}ms rep={rep:>2} [{tag}] "
                          f"served={cell.get('served')} over_served={cell.get('over_served')} "
                          f"final_balance={cell.get('final_balance')}")

    manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["cells_total"] = len(cells)
    manifest["cells_valid"] = sum(1 for c_ in cells if c_.get("valid"))
    manifest["cells_invalid"] = sum(1 for c_ in cells if not c_.get("valid"))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary_path = SUMMARY_DIR / f"{run_batch_id}.summary.json"
    summary_path.write_text(json.dumps({"manifest": manifest, "cells": cells}, indent=2,
                                       default=str), encoding="utf-8")
    print(f"\nSummary -> {summary_path}")
    print(f"Manifest -> {manifest_path}")
    print(f"Cells: {manifest['cells_valid']} valid / {manifest['cells_total']} total")
    if manifest["cells_invalid"]:
        print(f"WARNING: {manifest['cells_invalid']} invalid cell(s) -- see raw JSONL/summary "
              f"for reasons. NOT silently discarded.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", required=True, choices=["C0", "C1", "C2", "C3"])
    ap.add_argument("--arrival", required=True, choices=["sequential", "concurrent"])
    ap.add_argument("--delays", default="0,10,50,100,500",
                    help="comma-separated delay list in ms")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--endpoint", default="/async/b0/complete",
                    help="use /async/b0/complete-atomic for condition C3")
    ap.add_argument("--fault", default="none", choices=["none", "lost_event", "duplicate_event"])
    ap.add_argument("--concurrency", type=int, default=B0_REQUESTS,
                    help="requests per cell (default matches the validated historical "
                         "protocol; added for Tier-2 concurrency-scaling experiments)")
    ap.add_argument("--budget", type=int, default=B0_BUDGET_UNITS,
                    help="affordable units per cell (default matches the validated "
                         "historical protocol; added for Tier-2 budget-scaling experiments)")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if args.condition == "C3" and args.endpoint == "/async/b0/complete":
        print("NOTE: condition C3 is the atomic/hardened condition; defaulting --endpoint "
              "to /async/b0/complete-atomic (override with --endpoint if intentional).",
              file=sys.stderr)
        args.endpoint = "/async/b0/complete-atomic"

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
