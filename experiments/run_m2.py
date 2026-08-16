"""Raw-data runner for M2 (usage-record authority), with controlled concurrency.

Sweeps architecture x manipulation x concurrency x price_tier. Each cell issues a
FIXED number of requests through a pool of exactly ``concurrency`` workers (same
rationale as run_m1: hold volume constant so concurrency effects are per-request
effects, not workload scaling).

PRIMARY QUESTION: does concurrency change accounting-integrity failure, or the cost
of the defense? Throughput/timeout behaviour is recorded as a SECONDARY capacity
observation, not as a denial-of-service study.

Client types (Priority-6 control matrix): ``honest`` (manipulation="honest") vs
``attacker`` (any manipulation strategy), each against vulnerable and
server-authoritative architectures.

Local testbed only:  python -m experiments.run_m2 --concurrency 1 5 20 50 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from attacks.m2_usage_authority import send
from experiments import _mcommon as C

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "raw"
SCHEMA_VERSION = 2

ARCHES = ["client", "client_logged", "client_total", "upstream", "server_recount", "hybrid_reconcile"]
MANIPS = ["honest", "under_report_output_50", "under_report_output_90", "under_report_input_50",
          "drop_reasoning", "inflate_cached", "total_mismatch", "rounding_shave"]


async def _issue_pool(client, api_key, prompt, seed, trial_id, manip, n_requests, concurrency):
    """Issue exactly n_requests through a pool of `concurrency` workers."""
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(n_requests):
        queue.put_nowait(i)
    lat: list[float] = []
    errors = 0
    timeouts = 0

    async def worker():
        nonlocal errors, timeouts
        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            t0 = time.perf_counter()
            try:
                await send(client, api_key, prompt, seed, trial_id, manip)
                lat.append((time.perf_counter() - t0) * 1000.0)
            except httpx.TimeoutException:
                timeouts += 1
            except Exception:  # noqa: BLE001
                errors += 1

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(concurrency)])
    return lat, errors, timeouts


def _pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[i]


async def main() -> None:
    ap = argparse.ArgumentParser(description="M2 runner with controlled concurrency.")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--prompt", default="benchmark the usage record authority boundary please now")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--architectures", nargs="+", default=ARCHES)
    ap.add_argument("--manipulations", nargs="+", default=MANIPS)
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1])
    ap.add_argument("--tiers", nargs="+", default=["medium"])
    ap.add_argument("--requests-per-cell", type=int, default=20)
    ap.add_argument("--no-reset-db", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    max_c = max(args.concurrency)
    limits = httpx.Limits(max_connections=max_c + 20, max_keepalive_connections=max_c + 20)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0, limits=limits) as client:
        (await client.get("/health")).raise_for_status()
        if not args.no_reset_db:
            await C.reset_db(client)
        db = await C.db_info(client)
        q = await C.quote(client, args.prompt, args.seed)
        account_id, api_key = await C.create_account(client, "m2-attacker")

        trials = []
        for tier in args.tiers:
            for arch in args.architectures:
                for conc in args.concurrency:
                    for manip in args.manipulations:
                        meta = await C.create_m_trial(client, account_id, "m2", arch, tier,
                                                      args.prompt, args.seed)
                        tid = meta["trial_id"]
                        t0 = time.perf_counter()
                        lat, errs, tos = await _issue_pool(client, api_key, args.prompt, args.seed,
                                                           tid, manip, args.requests_per_cell, conc)
                        wall_s = time.perf_counter() - t0
                        audit = await C.finalize_m_trial(client, tid)

                        trials.append({
                            "trial_id": tid, "mechanism": "m2", "architecture": arch,
                            "price_tier": tier, "concurrency": conc, "manipulation": manip,
                            "client_type": "honest" if manip == "honest" else "attacker",
                            "requests_issued": args.requests_per_cell,
                            "wall_seconds": wall_s,
                            "throughput_rps": args.requests_per_cell / wall_s if wall_s else None,
                            "errors": errs, "timeouts": tos,
                            "error_rate": (errs + tos) / args.requests_per_cell,
                            "latency_ms": {
                                "mean": statistics.fmean(lat) if lat else 0.0,
                                "p50": _pct(lat, 50), "p95": _pct(lat, 95), "p99": _pct(lat, 99)},
                            "prices": meta["prices"],
                            "initial_balance": C.money(audit["initial_balance"]),
                            "final_balance": C.money(audit["final_balance"]),
                            "balance_delta": C.money(audit["balance_delta"]),
                            "net_debit_total": C.money(audit["net_debit_total"]),
                            "total_leak": C.money(audit["total_leak"]),
                            "reconciled": audit["reconciled"],
                            "record_count": audit["record_count"],
                            "invariant_violations": audit["invariant_violations"],
                            "records": [C.normalize_row(r) for r in audit["rows"]],
                        })
                        leaks = sum(1 for r in audit["rows"] if r["leak"] and float(r["leak"]) > 0)
                        print(f"[m2 {arch:<16} c={conc:>3} {manip:<22}] "
                              f"recs={audit['record_count']:>3} leaking={leaks:>3} "
                              f"rps={args.requests_per_cell/wall_s:7.1f} "
                              f"p95={_pct(lat,95):7.1f}ms err={errs+tos} recon={audit['reconciled']}")

    payload = {
        "experiment": "m2_usage_record_authority", "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "design_note": ("requests_per_cell FIXED across concurrency; primary question is "
                        "whether concurrency changes accounting-integrity failure or defense "
                        "overhead. Timeout/throughput data is a secondary capacity note."),
        "parameters": {"prompt": args.prompt, "model_seed": args.seed,
                       "prompt_tokens": q["prompt_tokens"], "completion_tokens": q["completion_tokens"],
                       "architectures": args.architectures, "manipulations": args.manipulations,
                       "concurrency": args.concurrency, "tiers": args.tiers,
                       "requests_per_cell": args.requests_per_cell},
        "trials": trials,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RESULTS_DIR / f"m2_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw M2 results -> {out}  ({len(trials)} cells)")


if __name__ == "__main__":
    asyncio.run(main())
