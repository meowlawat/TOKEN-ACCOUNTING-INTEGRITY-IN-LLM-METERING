"""Architectural ablation (Phase D): which enforcement primitive actually closes the
invariant violation?

"Server recount works" is a weaker claim than "these exact architectural properties
are sufficient". This runner removes one primitive at a time and measures the effect,
producing a factorial table per mechanism.

M1 factorial — {reservation} x {abort-inclusive finalization}:
    reserve + finalize      -> reserve_reconcile
    reserve + NO finalize   -> reserve_refund_on_abort   (refunds the whole hold)
    NO reserve + finalize   -> no_reserve_settle         (ablation cell)
    NO reserve + NO finalize-> post_completion
  plus pre_debit (commit-before-inference) as a separate design point.

M2 factorial — {server recount performed} x {recount used as billing basis}:
    recount + used          -> server_recount
    recount + NOT used      -> client_logged   (recount computed, billing ignores it)
    NO recount + n/a        -> client
    recount + reconcile     -> hybrid_reconcile
  plus client_total (different pricing basis) and upstream (honest third party).

Also records a SECOND property that integrity alone does not capture: whether the
architecture provides a FUNDS GUARANTEE (can the balance go negative?). This matters
because the ablation shows integrity and solvency are closed by *different* primitives.

Local testbed only:  python -m experiments.run_ablation
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from attacks.m1_stream_abort import stream_and_abort
from attacks.m2_usage_authority import send
from experiments import _mcommon as C

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
PROMPT_M1 = "ablation probe for metering commit timing primitives"
PROMPT_M2 = "ablation probe for usage record authority primitives now"
SEED = 1337

M1_FACTORS = {
    "pre_debit":               {"reservation": True,  "abort_finalization": "n/a (pre-committed)"},
    "reserve_reconcile":       {"reservation": True,  "abort_finalization": True},
    "reserve_refund_on_abort": {"reservation": True,  "abort_finalization": False},
    "no_reserve_settle":       {"reservation": False, "abort_finalization": True},
    "post_completion":         {"reservation": False, "abort_finalization": False},
}
M2_FACTORS = {
    "client":           {"recount_performed": False, "recount_used_for_billing": False},
    "client_logged":    {"recount_performed": True,  "recount_used_for_billing": False},
    "client_total":     {"recount_performed": False, "recount_used_for_billing": False},
    "server_recount":   {"recount_performed": True,  "recount_used_for_billing": True},
    "hybrid_reconcile": {"recount_performed": True,  "recount_used_for_billing": True},
    "upstream":         {"recount_performed": False, "recount_used_for_billing": False},
}


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


async def m1_cell(client, aid, key, arch, abort_pct, n_out, reps, credits):
    """Run `reps` aborting streams; also probe solvency with a tight budget."""
    meta = (await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m1", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT_M1, "seed": SEED, "initial_credits": credits})).json()
    tid = meta["trial_id"]
    abort_after = None if abort_pct >= 100 else max(1, round(abort_pct / 100 * n_out))
    for _ in range(reps):
        await stream_and_abort(client, key, PROMPT_M1, SEED, tid, abort_after)
    await asyncio.sleep(0.35)
    audit = (await client.post(f"/admin/m-trials/{tid}/finalize")).json()
    served = [r for r in audit["rows"] if r["served"]]
    auth = sum(D(r["authoritative_cost"]) for r in served)
    return {
        "architecture": arch, "abort_pct": abort_pct, "requests": reps,
        "served": len(served),
        "total_leak": str(D(audit["total_leak"])),
        "leak_per_request": str((D(audit["total_leak"]) / len(served)) if served else Decimal(0)),
        "leakage_efficiency": float(D(audit["total_leak"]) / auth) if auth > 0 else 0.0,
        "invariant_violations": audit["invariant_violations"],
        "attack_success": audit["invariant_violations"] > 0,
        "reconciled": audit["reconciled"],
        "final_balance": str(D(audit["final_balance"])),
        "went_negative": D(audit["final_balance"]) < 0,
        **M1_FACTORS.get(arch, {}),
    }


async def m2_cell(client, aid, key, arch, manip, reps):
    meta = (await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m2", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT_M2, "seed": SEED, "initial_credits": 1e8})).json()
    tid = meta["trial_id"]
    lat = []
    for _ in range(reps):
        await send(client, key, PROMPT_M2, SEED, tid, manip)
    audit = (await client.post(f"/admin/m-trials/{tid}/finalize")).json()
    served = [r for r in audit["rows"] if r["served"]]
    auth = sum(D(r["authoritative_cost"]) for r in served)
    dets = {r["detection_level"] for r in served if D(r["leak"]) > 0}
    return {
        "architecture": arch, "manipulation": manip, "requests": reps, "served": len(served),
        "total_leak": str(D(audit["total_leak"])),
        "leakage_efficiency": float(D(audit["total_leak"]) / auth) if auth > 0 else 0.0,
        "invariant_violations": audit["invariant_violations"],
        "attack_success": audit["invariant_violations"] > 0,
        "detection": (sorted(dets)[0] if dets else "n/a"),
        "reconciled": audit["reconciled"],
        **M2_FACTORS.get(arch, {}),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--abort-pcts", type=float, nargs="+", default=[50, 90])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=180.0) as client:
        (await client.get("/health")).raise_for_status()
        db = await C.db_info(client)
        q = (await client.get("/admin/quote", params={"prompt": PROMPT_M1, "seed": SEED})).json()
        n_out = int(q["completion_tokens"])
        unit = Decimal(str(q["cost"]))
        aid, key = await C.create_account(client, "ablation")

        m1_rows = []
        print("M1 ablation (reservation x abort-inclusive finalization)")
        for arch in M1_FACTORS:
            for pct in args.abort_pcts:
                r = await m1_cell(client, aid, key, arch, pct, n_out, args.reps, 1e8)
                m1_rows.append(r)
                print(f"  [{arch:<24} abort={pct:>3.0f}%] leak/req={float(r['leak_per_request']):.4f} "
                      f"viol={r['invariant_violations']:>2} success={r['attack_success']}")

        # Solvency probe: budget for exactly 2 requests, then issue `reps` requests.
        print("M1 solvency probe (budget for 2 requests, 6 issued, abort at 90%)")
        m1_solvency = []
        for arch in M1_FACTORS:
            r = await m1_cell(client, aid, key, arch, 90, n_out, 6, float(unit * 2))
            r["probe"] = "solvency"
            m1_solvency.append(r)
            print(f"  [{arch:<24}] served={r['served']}/6 final_balance={r['final_balance']} "
                  f"negative={r['went_negative']}")

        m2_rows = []
        print("M2 ablation (recount performed x recount used for billing)")
        for arch in M2_FACTORS:
            for manip in ("under_report_output_90", "total_mismatch", "honest"):
                r = await m2_cell(client, aid, key, arch, manip, args.reps)
                m2_rows.append(r)
                print(f"  [{arch:<18} {manip:<22}] eff={r['leakage_efficiency']:.3f} "
                      f"viol={r['invariant_violations']:>2} detect={r['detection']}")

    payload = {
        "experiment": "architectural_ablation", "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "purpose": ("Determine WHICH enforcement primitive closes each violation, by "
                    "removing one primitive at a time (factorial ablation)."),
        "parameters": {"reps": args.reps, "abort_pcts": args.abort_pcts,
                       "prompt_m1": PROMPT_M1, "prompt_m2": PROMPT_M2, "seed": SEED,
                       "n_out": n_out, "unit_cost": str(unit)},
        "m1_factorial": m1_rows, "m1_solvency_probe": m1_solvency, "m2_factorial": m2_rows,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"ablation_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nablation -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
