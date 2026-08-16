"""Raw-data runner for M1 (metering-commit timing), with controlled concurrency.

Sweeps architecture x abort_pct x concurrency x price_tier. Each cell issues a
FIXED number of requests (``--requests-per-cell``) through a pool of exactly
``concurrency`` worker tasks, so offered load is a genuine sustained concurrency
rather than a one-shot ``gather`` of N tasks with uncontrolled start timing.

WHY FIXED REQUESTS PER CELL: holding request volume constant across concurrency
levels separates *workload scaling* (more requests attempted => more absolute
leakage, mechanically) from *vulnerability scaling* (more leakage **per request**
or higher per-request ASR). Absolute leakage is still reported, but the headline
comparisons are normalized (leak/request, leakage efficiency, request-ASR).

Client types (Priority-6 control matrix): ``attacker`` aborts mid-stream;
``honest`` reads the stream to completion. Both are run against vulnerable and
hardened architectures.

Local testbed only:  python -m experiments.run_m1 --concurrency 1 5 20 50 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from attacks.m1_stream_abort import stream_and_abort
from experiments import _mcommon as C

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "raw"
SCHEMA_VERSION = 2


async def _issue_pool(client, api_key, prompt, seed, trial_id, abort_after, n_requests, concurrency):
    """Issue exactly ``n_requests`` through a pool of ``concurrency`` workers.

    Returns per-request client-side records. Sustained concurrency: a worker starts
    its next request only when its previous one finishes, so in-flight count stays
    at ``concurrency`` (not a thundering herd).
    """
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(n_requests):
        queue.put_nowait(i)
    out: list[dict] = []

    async def worker():
        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            t0 = time.perf_counter()
            rid, read = await stream_and_abort(client, api_key, prompt, seed, trial_id, abort_after)
            out.append({"request_id": rid, "client_tokens_read": read,
                        "client_latency_ms": (time.perf_counter() - t0) * 1000.0})

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(concurrency)])
    return out


async def main() -> None:
    ap = argparse.ArgumentParser(description="M1 runner with controlled concurrency.")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--prompt", default="benchmark the metering commit timing please")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--architectures", nargs="+",
                    default=["pre_debit", "reserve_reconcile", "post_completion",
                             "reserve_refund_on_abort"])
    ap.add_argument("--abort-pcts", type=float, nargs="+", default=[0, 25, 50, 75, 90, 100])
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1])
    ap.add_argument("--tiers", nargs="+", default=["medium"])
    ap.add_argument("--requests-per-cell", type=int, default=20,
                    help="FIXED per cell so concurrency does not change request volume")
    ap.add_argument("--no-reset-db", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    max_c = max(args.concurrency)
    limits = httpx.Limits(max_connections=max_c + 20, max_keepalive_connections=max_c + 20)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=180.0, limits=limits) as client:
        (await client.get("/health")).raise_for_status()
        if not args.no_reset_db:
            await C.reset_db(client)
        db = await C.db_info(client)
        q = await C.quote(client, args.prompt, args.seed)
        n_out = int(q["completion_tokens"])
        account_id, api_key = await C.create_account(client, "m1-attacker")

        trials = []
        for tier in args.tiers:
            for arch in args.architectures:
                for conc in args.concurrency:
                    for pct in args.abort_pcts:
                        complete = pct >= 100
                        abort_after = None if complete else max(0, round(pct / 100.0 * n_out))
                        client_type = "honest" if complete else "attacker"

                        meta = await C.create_m_trial(client, account_id, "m1", arch, tier,
                                                      args.prompt, args.seed)
                        tid = meta["trial_id"]
                        t0 = time.perf_counter()
                        cli = await _issue_pool(client, api_key, args.prompt, args.seed, tid,
                                                abort_after, args.requests_per_cell, conc)
                        wall_s = time.perf_counter() - t0
                        await asyncio.sleep(0.3)  # let shielded settlements land
                        audit = await C.finalize_m_trial(client, tid)

                        by_id = {c["request_id"]: c for c in cli}
                        recs = []
                        for r in audit["rows"]:
                            row = C.normalize_row(r)
                            row.update(by_id.get(r["request_id"], {}))
                            recs.append(row)

                        trials.append({
                            "trial_id": tid, "mechanism": "m1", "architecture": arch,
                            "price_tier": tier, "concurrency": conc, "abort_pct": pct,
                            "client_type": client_type,
                            "requests_issued": args.requests_per_cell,
                            "wall_seconds": wall_s,
                            "throughput_rps": args.requests_per_cell / wall_s if wall_s else None,
                            "prices": meta["prices"],
                            "initial_balance": C.money(audit["initial_balance"]),
                            "final_balance": C.money(audit["final_balance"]),
                            "balance_delta": C.money(audit["balance_delta"]),
                            "net_debit_total": C.money(audit["net_debit_total"]),
                            "total_leak": C.money(audit["total_leak"]),
                            "reconciled": audit["reconciled"],
                            "record_count": audit["record_count"],
                            "invariant_violations": audit["invariant_violations"],
                            "records": recs,
                        })
                        leaks = sum(1 for r in audit["rows"] if r["leak"] and float(r["leak"]) > 0)
                        print(f"[m1 {arch:<24} c={conc:>3} abort={pct:>5.0f}% {client_type:<8}] "
                              f"recs={audit['record_count']:>3} leaking={leaks:>3} "
                              f"rps={args.requests_per_cell/wall_s:6.1f} recon={audit['reconciled']}")

    payload = {
        "experiment": "m1_metering_commit_timing", "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "design_note": ("requests_per_cell is FIXED across concurrency levels so that "
                        "absolute leakage differences are attributable to per-request "
                        "vulnerability, not to workload volume."),
        "parameters": {"prompt": args.prompt, "model_seed": args.seed, "n_out": n_out,
                       "architectures": args.architectures, "abort_pcts": args.abort_pcts,
                       "concurrency": args.concurrency, "tiers": args.tiers,
                       "requests_per_cell": args.requests_per_cell},
        "trials": trials,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RESULTS_DIR / f"m1_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw M1 results -> {out}  ({len(trials)} cells)")


if __name__ == "__main__":
    asyncio.run(main())
