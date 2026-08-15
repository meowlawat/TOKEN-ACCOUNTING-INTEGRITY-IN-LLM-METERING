"""Raw-data runner for M1 (metering-commit timing).

Sweeps architecture x abort_pct x price_tier x reps. Each (arch, tier) is one
MTrial that accumulates all its requests; every request aborts a real SSE stream
after a computed number of tokens. Writes machine-readable raw JSON only.

Local testbed only:  python -m experiments.run_m1
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from attacks.m1_stream_abort import stream_and_abort
from experiments import _mcommon as C

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "raw"
SCHEMA_VERSION = 1


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--prompt", default="benchmark the metering commit timing please")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--architectures", nargs="+",
                    default=["pre_debit", "reserve_reconcile", "post_completion", "reserve_refund_on_abort"])
    ap.add_argument("--abort-pcts", type=float, nargs="+", default=[0, 10, 25, 50, 75, 90, 100])
    ap.add_argument("--tiers", nargs="+", default=["low", "medium", "high"])
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--no-reset-db", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
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
                meta = await C.create_m_trial(client, account_id, "m1", arch, tier, args.prompt, args.seed)
                tid = meta["trial_id"]
                for pct in args.abort_pcts:
                    complete = pct >= 100
                    abort_after = None if complete else max(0, round(pct / 100.0 * n_out))
                    for _ in range(args.reps):
                        await stream_and_abort(client, api_key, args.prompt, args.seed, tid, abort_after)
                # settle lag: small pause so the last shielded settlement lands
                await asyncio.sleep(0.2)
                audit = await C.finalize_m_trial(client, tid)
                trials.append({
                    "trial_id": tid, "mechanism": "m1", "architecture": arch, "price_tier": tier,
                    "prices": meta["prices"], "initial_balance": C.money(audit["initial_balance"]),
                    "final_balance": C.money(audit["final_balance"]),
                    "balance_delta": C.money(audit["balance_delta"]),
                    "net_debit_total": C.money(audit["net_debit_total"]),
                    "total_leak": C.money(audit["total_leak"]),
                    "reconciled": audit["reconciled"], "record_count": audit["record_count"],
                    "invariant_violations": audit["invariant_violations"],
                    "records": [C.normalize_row(r) for r in audit["rows"]],
                })
                leaks = sum(1 for r in audit["rows"] if r["leak"] and float(r["leak"]) > 0)
                print(f"[m1 {tier:<6} {arch:<24}] records={audit['record_count']:>3} "
                      f"leaking={leaks:>3} recon={audit['reconciled']}")

    payload = {
        "experiment": "m1_metering_commit_timing", "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "parameters": {"prompt": args.prompt, "model_seed": args.seed, "n_out": n_out,
                       "architectures": args.architectures, "abort_pcts": args.abort_pcts,
                       "tiers": args.tiers, "reps": args.reps},
        "trials": trials,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = payload["generated_at"]
    out = Path(args.out) if args.out else RESULTS_DIR / f"m1_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw M1 results -> {out}  ({len(trials)} trials)")


if __name__ == "__main__":
    asyncio.run(main())
