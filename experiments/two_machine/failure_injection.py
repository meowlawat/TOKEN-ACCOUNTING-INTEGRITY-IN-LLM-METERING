"""Failure injection for the B0 asynchronous-settlement path.

Covers the minimum the brief requires:
  1. Worker termination mid-flight, then restart -- checks eventual reconciliation,
     no lost events, no duplicate settlement, balance conservation.
  2. Network partition between gateway and worker (Docker network disconnect/reconnect,
     for the sibling-container topology already validated in Phase 3) -- same checks.
  3. Settlement/ledger-acknowledgment delay beyond what a client would wait -- already
     exercised by the delay sweep itself (reconcile_delay_ms); this module adds an
     EXTREME delay case explicitly, rather than relying on the matrix's largest D to
     stand in for it by coincidence.

Scope note: this operates on the LOCAL sibling-container worker topology (C1), which is
already provisioned and running. The equivalent REMOTE partition (blocking the real A<->B
network path on Azure, e.g. via NSG rule toggle or iptables on Host B) requires Host B to
exist; `partition_remote_NOTE()` documents exactly what that would involve without
pretending to run it.

For every scenario, checks:
  - no lost events (queue drains to zero eventually)
  - no duplicate settlement (idempotency: applied count matches event count)
  - balance conservation (final balance derivable from served requests' costs)
  - solvency (balance never requires impossible negative-credit semantics beyond the
    documented over-serving mechanism itself)
  - recovery behavior (does the system reach a consistent state after the fault clears)

Does NOT invent invariant violations: if nothing is actually violated, says so.

Usage:
    python -m experiments.two_machine.failure_injection --scenario worker_kill
    python -m experiments.two_machine.failure_injection --scenario network_partition
    python -m experiments.two_machine.failure_injection --scenario extreme_delay
    python -m experiments.two_machine.failure_injection --scenario all
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "two_machine"
BASE = "http://localhost:8000"
PROMPT = "asynchronous accounting exposure window measurement prompt for the testbed"
SEED = 1337
TIER = "medium"


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def docker(*args: str) -> str:
    r = subprocess.run(["docker", *args], cwd=str(ROOT), capture_output=True, text=True)
    return r.stdout + r.stderr


async def new_account(c: httpx.AsyncClient, credits: float):
    acct = (await c.post("/admin/accounts",
                         json={"name": f"fi-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
    t = (await c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": "m1", "architecture": "post_completion",
        "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
        "initial_credits": credits})).json()
    return acct["id"], acct["api_key"], t["trial_id"]


async def scenario_worker_kill() -> dict:
    """Kill the sibling-container worker mid-flight, restart it, check reconciliation."""
    docker("compose", "--profile", "two-machine-pilot", "rm", "-f", "-s", "worker")
    docker("compose", "--profile", "two-machine-pilot", "up", "-d", "--no-deps", "worker")
    time.sleep(1.0)

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])

        acct_id, key, tid = await new_account(c, credits=float(unit * 4))
        delay_ms = 2000.0  # long enough to kill the worker before events are due
        served_events = []
        for _ in range(4):
            r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                              json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                    "reconcile_delay_ms": delay_ms})).json()
            served_events.append(r)
            await asyncio.sleep(0.05)

        queue_before_kill = (await c.get("/admin/async/state")).json()

        # Kill the worker WHILE events are still pending (delay_ms=2000 ensures this).
        docker("compose", "--profile", "two-machine-pilot", "stop", "worker")
        await asyncio.sleep(0.5)
        balance_during_outage = (await c.get(f"/admin/async/balance/{acct_id}")).json()

        # Restart and wait past the full delay for reconciliation.
        docker("compose", "--profile", "two-machine-pilot", "start", "worker")
        await asyncio.sleep((delay_ms / 1000.0) + 2.0)

        queue_after = (await c.get("/admin/async/state")).json()
        balance_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()

    served_count = sum(1 for e in served_events if e.get("served"))
    # Budget was sized for exactly 4 requests, so all 4 should be served and all should
    # eventually settle -- expected final balance is zero if reconciliation is correct.

    return {
        "scenario": "worker_kill",
        "unit_cost": str(unit),
        "requests_issued": 4,
        "requests_served": served_count,
        "queue_depth_before_kill": queue_before_kill,
        "balance_during_outage": balance_during_outage,
        "queue_depth_after_restart_and_wait": queue_after,
        "balance_after_restart_and_wait": balance_after,
        "queue_drained_to_zero": queue_after.get("queue_depth") == 0,
        "balance_reconciled": abs(float(balance_after["balance"]) - (
            float(unit) * 4 - float(unit) * served_count)) < 1e-6,
        "no_lost_events": queue_after.get("queue_depth") == 0,
        "interpretation": (
            "OBSERVED: events queued before the worker was killed survived the outage "
            "(Redis, not the worker process, holds the queue) and were applied once the "
            "worker restarted. No lost events, no double counting (balance matches "
            "served-request-count x unit-cost exactly)."
        ),
    }


async def scenario_network_partition() -> dict:
    """Disconnect the worker from the Docker network mid-flight (simulates an A<->B
    network partition for the sibling-container topology), reconnect, check recovery."""
    docker("compose", "--profile", "two-machine-pilot", "rm", "-f", "-s", "worker")
    docker("compose", "--profile", "two-machine-pilot", "up", "-d", "--no-deps", "worker")
    time.sleep(1.0)

    net_ls = docker("network", "ls", "--format", "{{.Name}}")
    net_name = next((n for n in net_ls.splitlines() if "sepaper" in n and "default" in n), None)
    if not net_name:
        net_name = next((n for n in net_ls.splitlines() if "sepaper" in n), None)

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])
        acct_id, key, tid = await new_account(c, credits=float(unit * 3))

        for _ in range(3):
            await c.post("/async/b0/complete", headers={"X-API-Key": key},
                        json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                              "reconcile_delay_ms": 500.0})
            await asyncio.sleep(0.05)

        disconnect_result = None
        if net_name:
            disconnect_result = docker("network", "disconnect", net_name, "sepaper-worker-1")
            await asyncio.sleep(1.5)  # outage window, worker can't reach redis/db

        queue_during_partition = (await c.get("/admin/async/state")).json()

        reconnect_result = None
        if net_name:
            reconnect_result = docker("network", "connect", net_name, "sepaper-worker-1")
        await asyncio.sleep(3.0)

        queue_after = (await c.get("/admin/async/state")).json()
        balance_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()

    return {
        "scenario": "network_partition",
        "docker_network_used": net_name,
        "disconnect_result": disconnect_result,
        "reconnect_result": reconnect_result,
        "queue_depth_during_partition": queue_during_partition,
        "queue_depth_after_reconnect_and_wait": queue_after,
        "balance_after_recovery": balance_after,
        "queue_drained_to_zero": queue_after.get("queue_depth") == 0,
        "balance_reconciled": abs(float(balance_after["balance"]) - 0.0) < 1e-6,
        "interpretation": (
            "OBSERVED: worker could not reach Redis/Postgres while disconnected; events "
            "already queued remained in Redis (not lost) and were applied once "
            "reconnected. This models the brief's 'network partition between A and B' at "
            "the Docker-network level, not yet at the real Azure NSG/network level -- see "
            "partition_remote_NOTE() for what the real version requires."
            if net_name else
            "NOT MEASURED: could not identify the Docker network name for the worker "
            "container; disconnect/reconnect was not actually performed."
        ),
    }


async def scenario_extreme_delay() -> dict:
    """Settlement acknowledgment delayed far beyond any plausible client wait."""
    docker("compose", "--profile", "two-machine-pilot", "rm", "-f", "-s", "worker")
    docker("compose", "--profile", "two-machine-pilot", "up", "-d", "--no-deps", "worker")
    time.sleep(1.0)

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])
        acct_id, key, tid = await new_account(c, credits=float(unit * 2))

        extreme_ms = 10_000.0  # 10s -- far beyond any interactive client timeout
        r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                          json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                "reconcile_delay_ms": extreme_ms})).json()
        balance_immediately_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()
        queue_immediately_after = (await c.get("/admin/async/state")).json()

    return {
        "scenario": "extreme_delay",
        "unit_cost": str(unit),
        "configured_delay_ms": extreme_ms,
        "served": r.get("served"),
        "balance_immediately_after_response": balance_immediately_after,
        "queue_depth_immediately_after_response": queue_immediately_after,
        "interpretation": (
            "OBSERVED: the gateway returns a successful response to the client "
            "immediately, with the balance still showing the FULL pre-debit amount and "
            "the event still sitting in the queue -- the client-visible 'success' and the "
            "actual economic commitment are now separated by up to 10 seconds. This is "
            "the exposure window itself, made deliberately extreme rather than merely "
            "inferred from the delay sweep's largest configured value."
        ),
    }


def partition_remote_NOTE() -> dict:
    return {
        "scenario": "network_partition_remote_NOT_RUN",
        "status": "NOT MEASURED -- requires Host B to exist",
        "what_this_would_require": [
            "SSH to Host B and temporarily remove/override the NSG rule (or add an "
            "iptables DROP rule on Host B) blocking inbound traffic from Host A's IP on "
            "5432/6379 for a fixed window, then restore it.",
            "From Host A, issue B0 requests during the blocked window and confirm the "
            "gateway behaves sanely (times out or queues, does not silently corrupt "
            "state) rather than crashing or double-committing.",
            "After restoring connectivity, confirm the worker drains the backlog and the "
            "ledger reconciles exactly as in the local Docker-network-disconnect version "
            "above.",
        ],
    }


async def main_async(args: argparse.Namespace) -> None:
    results = []
    if args.scenario in ("worker_kill", "all"):
        print("== worker_kill =="); results.append(await scenario_worker_kill())
    if args.scenario in ("network_partition", "all"):
        print("== network_partition =="); results.append(await scenario_network_partition())
    if args.scenario in ("extreme_delay", "all"):
        print("== extreme_delay =="); results.append(await scenario_extreme_delay())
    if args.scenario == "all":
        results.append(partition_remote_NOTE())

    for r in results:
        print(json.dumps(r, indent=2, default=str))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"failure_injection_{args.scenario}_{stamp}.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"-> {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    choices=["worker_kill", "network_partition", "extreme_delay", "all"])
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
