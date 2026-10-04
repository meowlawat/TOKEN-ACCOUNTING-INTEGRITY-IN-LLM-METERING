"""Phase 3 pilot: worker extraction control, same host.

Runs the IDENTICAL B0 sequential-arrival protocol as
`experiments.run_async_accounting.run_b0()`, but settlement is performed by the
standalone `app.accounting.worker_main` PROCESS instead of the gateway's in-process
`_worker_loop` asyncio task. Everything else -- constants, request shape, timing,
budget -- is copied verbatim from the published driver so this isolates exactly one
variable: worker-as-a-separate-process vs. worker-as-an-asyncio-task, still on one
machine, still over loopback.

The gateway's own worker (`/admin/async/worker/start`) is never started during this run.

The worker process is started ONCE, before the delay sweep, and its readiness is
confirmed by reading its own startup log line rather than guessed with a fixed sleep --
see RESEARCH_LOG.md, "Phase 3, attempt 3" for why a fixed sleep and a per-condition
process restart both corrupted the measurement by racing the worker's own cold-start
latency against the thing being measured.

PASS criterion: over_served == [0, 0, 0, 1, 4] at D == [0, 10, 50, 100, 500] ms, matching
the just-reproduced baseline exactly.

Usage:
    python -m experiments.two_machine.pilot_same_host_external_worker
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
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

DELAYS_MS = [0.0, 10.0, 50.0, 100.0, 500.0]
B0_INTERARRIVAL_MS = 20.0
B0_REQUESTS = 6
WORKER_POLL_MS = 2.0
WORKER_READY_TIMEOUT_S = 30.0


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


async def new_account(c: httpx.AsyncClient, credits: float,
                      mechanism: str = "m1", architecture: str = "post_completion"):
    # NOTE: matches experiments.run_async_accounting.new_account exactly, including the
    # m1/post_completion default even for B0 calls -- the MTrial.mechanism field only
    # accepts ^(m1|m2)$ and is bookkeeping metadata here, not a behavior switch. Which
    # endpoint is called (/async/b0/complete vs /async/m1/stream) is what selects B0 vs M1
    # behavior.
    acct = (await c.post("/admin/accounts",
                         json={"name": f"pilot-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
    t = (await c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": mechanism, "architecture": architecture,
        "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
        "initial_credits": credits})).json()
    return acct["id"], acct["api_key"], t["trial_id"]


async def live_balance(c: httpx.AsyncClient, account_id: int) -> Decimal:
    return D((await c.get(f"/admin/async/balance/{account_id}")).json()["balance"])


class ExternalWorker:
    """Owns the worker CONTAINER for the whole run: one cold start, one shutdown.

    Runs as a sibling container (service "worker", profile "two-machine-pilot" in
    docker-compose.override.yml) rather than a bare host process -- required, not a
    convenience, because a host-side Windows process and the gateway's Linux container
    do not share a perf_counter_ns() clock domain (see RESEARCH_LOG.md, Phase 3 attempt
    4). Running it as a container alongside `app`, `db`, `redis` keeps it in the same
    clock domain while still being a genuinely separate OS process, which is exactly
    what Phase 3 needs to isolate.
    """

    SERVICE = "worker"

    def __init__(self, poll_ms: float, stats_every: int = 200):
        # Stop any stale instance from a previous run first.
        subprocess.run(["docker", "compose", "--profile", "two-machine-pilot",
                        "rm", "-f", "-s", self.SERVICE],
                       cwd=str(ROOT), capture_output=True, text=True)
        result = subprocess.run(
            ["docker", "compose", "--profile", "two-machine-pilot", "up", "-d",
             "--no-deps", self.SERVICE],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to start worker container:\n{result.stderr}")

    def wait_ready(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            logs = subprocess.run(
                ["docker", "compose", "logs", "--no-color", self.SERVICE],
                cwd=str(ROOT), capture_output=True, text=True,
            ).stdout
            if "worker starting" in logs:
                return
            ps = subprocess.run(
                ["docker", "compose", "ps", "-a", "--format", "json", self.SERVICE],
                cwd=str(ROOT), capture_output=True, text=True,
            ).stdout
            if '"State":"exited"' in ps or '"ExitCode":1' in ps:
                raise RuntimeError(f"worker container exited during startup; logs:\n{logs}")
            time.sleep(0.2)
        raise RuntimeError(f"worker did not report ready within {timeout_s}s")

    def stop(self) -> str:
        logs = subprocess.run(
            ["docker", "compose", "logs", "--no-color", self.SERVICE],
            cwd=str(ROOT), capture_output=True, text=True,
        ).stdout
        subprocess.run(["docker", "compose", "--profile", "two-machine-pilot",
                        "stop", self.SERVICE],
                       cwd=str(ROOT), capture_output=True, text=True)
        return logs


async def run() -> list[dict]:
    out = []
    async with httpx.AsyncClient(base_url=BASE, timeout=300.0) as c:
        st = (await c.get("/admin/async/worker/stats")).json()
        if st.get("running"):
            raise RuntimeError(
                "Gateway in-process worker is running. Stop it "
                "(POST /admin/async/worker/stop) before running this pilot.")

        print(f"\nPhase 3 pilot -- B0 sequential arrivals, external standalone worker, "
              f"same host\n  {B0_INTERARRIVAL_MS:.0f} ms apart, budget = 2 requests")
        print(f"  {'delay':>7}{'issued':>8}{'served':>8}{'affordable':>12}"
              f"{'over-served':>13}{'final bal':>12}")

        await c.post("/admin/async/reset")
        pid, pkey, ptid = await new_account(c, credits=1000.0)
        unit = D((await c.post("/async/b0/complete", headers={"X-API-Key": pkey},
                               json={"prompt": PROMPT, "trial_id": ptid, "seed": SEED,
                                     "reconcile_delay_ms": 0.0})).json()["cost"])

        worker = ExternalWorker(WORKER_POLL_MS)
        worker.wait_ready(WORKER_READY_TIMEOUT_S)
        print("  (external worker process confirmed ready)")

        try:
            for delay in DELAYS_MS:
                await c.post("/admin/async/reset")

                acct_id, key, tid = await new_account(c, credits=float(unit * 2))
                served = 0
                for _ in range(B0_REQUESTS):
                    r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                                      json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                            "reconcile_delay_ms": delay})).json()
                    served += 1 if r.get("served") else 0
                    await asyncio.sleep(B0_INTERARRIVAL_MS / 1000.0)

                await asyncio.sleep(max(0.4, (delay * 4) / 1000.0))

                final = await live_balance(c, acct_id)
                row = {"mechanism": "b0_pilot_external_worker", "delay_ms": delay,
                       "interarrival_ms": B0_INTERARRIVAL_MS, "issued": B0_REQUESTS,
                       "served": served, "affordable": 2, "over_served": max(0, served - 2),
                       "unit_cost": str(unit), "final_balance": str(final)}
                out.append(row)
                print(f"  {delay:>6.0f}ms{B0_REQUESTS:>8}{served:>8}{2:>12}"
                      f"{max(0, served - 2):>13}{str(final):>12}")
        finally:
            worker_log = worker.stop()

    for row in out:
        row["worker_log_tail"] = worker_log[-2000:]
    return out


async def main() -> None:
    rows = await run()

    expected_over_served = [0, 0, 0, 1, 4]
    actual_over_served = [r["over_served"] for r in rows]
    expected_balances = ["0.000000", "0.000000", "0.000000", "-0.081000", "-0.324000"]
    actual_balances = [r["final_balance"] for r in rows]

    match_over_served = actual_over_served == expected_over_served
    match_balances = actual_balances == expected_balances

    print(f"\nover_served match published row {expected_over_served}: {match_over_served}")
    print(f"final_balance match published row {expected_balances}: {match_balances}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"pilot_same_host_external_worker_{stamp}.json"
    out_path.write_text(json.dumps({
        "experiment": "phase3_pilot_same_host_external_worker",
        "generated_at": stamp,
        "parameters": {"delays_ms": DELAYS_MS, "b0_interarrival_ms": B0_INTERARRIVAL_MS,
                       "b0_requests": B0_REQUESTS, "worker_poll_ms": WORKER_POLL_MS},
        "expected_over_served": expected_over_served,
        "actual_over_served": actual_over_served,
        "match_over_served": match_over_served,
        "expected_final_balance": expected_balances,
        "actual_final_balance": actual_balances,
        "match_final_balance": match_balances,
        "rows": rows,
    }, indent=2, default=str), encoding="utf-8")
    print(f"-> {out_path}")

    if not (match_over_served and match_balances):
        print("\nPHASE 3 GATE: FAILED -- extraction changed behavior. STOP. Do not proceed "
              "to the clock change or physical separation until this is fixed.")
        sys.exit(1)
    print("\nPHASE 3 GATE: PASSED -- external worker process reproduces the baseline exactly.")


if __name__ == "__main__":
    asyncio.run(main())
