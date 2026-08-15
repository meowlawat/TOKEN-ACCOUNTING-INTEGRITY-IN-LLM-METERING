"""Raw-data runner for M2 (usage-record authority).

Sweeps architecture x manipulation x price_tier x reps. Each (arch, tier) is one
MTrial; every request declares a manipulation strategy. Writes raw JSON only.

Local testbed only:  python -m experiments.run_m2
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from attacks.m2_usage_authority import send
from experiments import _mcommon as C

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "raw"
SCHEMA_VERSION = 1

ARCHES = ["client", "client_logged", "client_total", "upstream", "server_recount", "hybrid_reconcile"]
MANIPS = ["honest", "under_report_output_50", "under_report_output_90", "under_report_input_50",
          "drop_reasoning", "inflate_cached", "total_mismatch", "rounding_shave"]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--prompt", default="benchmark the usage record authority boundary please now")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--architectures", nargs="+", default=ARCHES)
    ap.add_argument("--manipulations", nargs="+", default=MANIPS)
    ap.add_argument("--tiers", nargs="+", default=["low", "medium", "high"])
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--no-reset-db", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        (await client.get("/health")).raise_for_status()
        if not args.no_reset_db:
            await C.reset_db(client)
        db = await C.db_info(client)
        q = await C.quote(client, args.prompt, args.seed)
        account_id, api_key = await C.create_account(client, "m2-attacker")

        trials = []
        for tier in args.tiers:
            for arch in args.architectures:
                meta = await C.create_m_trial(client, account_id, "m2", arch, tier, args.prompt, args.seed)
                tid = meta["trial_id"]
                for manip in args.manipulations:
                    for _ in range(args.reps):
                        await send(client, api_key, args.prompt, args.seed, tid, manip)
                audit = await C.finalize_m_trial(client, tid)
                trials.append({
                    "trial_id": tid, "mechanism": "m2", "architecture": arch, "price_tier": tier,
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
                print(f"[m2 {tier:<6} {arch:<16}] records={audit['record_count']:>3} "
                      f"leaking={leaks:>3} recon={audit['reconciled']}")

    payload = {
        "experiment": "m2_usage_record_authority", "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "parameters": {"prompt": args.prompt, "model_seed": args.seed,
                       "prompt_tokens": q["prompt_tokens"], "completion_tokens": q["completion_tokens"],
                       "architectures": args.architectures, "manipulations": args.manipulations,
                       "tiers": args.tiers, "reps": args.reps},
        "trials": trials,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = payload["generated_at"]
    out = Path(args.out) if args.out else RESULTS_DIR / f"m2_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw M2 results -> {out}  ({len(trials)} trials)")


if __name__ == "__main__":
    asyncio.run(main())
