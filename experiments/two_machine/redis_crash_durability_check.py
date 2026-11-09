"""Direct test of Redis crash-durability for the B0-async settlement queue.

Not a simulation (`fault=lost_event` already covers the simulated case, and the
manuscript already reports it honestly: a lost event leaks permanently at every delay).
This queues a REAL event against a REAL local Redis container, and the reproduction steps
below actually SIGKILL that container and restart it, to check whether a queued-but-
not-yet-due event survives a hard crash of the queue itself -- a question the existing
failure-injection suite never asked, because its worker-kill scenarios killed the WORKER
container, never Redis.

Usage (local topology, `docker compose up -d app worker` already running):

    python -m experiments.two_machine.redis_crash_durability_check
    # note the account_id and balance printed, then in a separate shell:
    docker kill -s SIGKILL sepaper-redis-1
    docker start sepaper-redis-1
    # then check:
    curl http://localhost:8000/admin/async/state            # queue_depth
    curl http://localhost:8000/admin/async/balance/<account_id>

Result observed and recorded in FINAL_HARDENING_AUDIT.md Section 5 (one run, this
session): queue_depth went from 1 to 0 across the crash, and the account balance was
never debited -- the queued event was permanently lost. Redis's default persistence
(`appendonly no`, `save 3600 1 300 100 60 10000`, confirmed via
`redis-cli CONFIG GET appendonly`/`save`) does not snapshot on every write, so anything
queued since the last snapshot point does not survive a hard crash.
"""

from __future__ import annotations

import httpx

BASE = "http://localhost:8000"
PROMPT = "durability test prompt"
SEED = 1337
DELAY_MS = 30_000.0  # long enough to queue a durable window for manual crash testing


def main() -> None:
    c = httpx.Client(base_url=BASE, timeout=30.0)
    acct = c.post("/admin/accounts", json={"name": "durability-test", "balance": 0.0}).json()
    trial = c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": "m1", "architecture": "post_completion",
        "price_tier": "medium", "seed": SEED, "prompt": PROMPT,
        "initial_credits": 1000.0,
    }).json()
    result = c.post("/async/b0/complete", headers={"X-API-Key": acct["api_key"]}, json={
        "prompt": PROMPT, "trial_id": trial["trial_id"], "seed": SEED,
        "reconcile_delay_ms": DELAY_MS,
    }).json()
    print("request result:", result)
    print("queue state before crash:", c.get("/admin/async/state").json())
    print("account_id:", acct["id"])
    print(f"\nNow run, in order: docker kill -s SIGKILL <redis container>; "
          f"docker start <redis container>; then recheck /admin/async/state and "
          f"/admin/async/balance/{acct['id']}.")


if __name__ == "__main__":
    main()
