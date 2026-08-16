"""Cross-validate the defenses against an INDEPENDENT implementation (Phase G).

Three checks:

  1. M2 -- run identical attack workloads and verify the gateway's own verdict against
     `defenses/m2_independent_checker.py`, which re-derives expected cost, leak and the
     integrity decision from primitives without sharing a code path with the gateway.

  2. M1 -- independently verify that finalization CANNOT be bypassed by a client
     disconnect: for every aborted request there must exist exactly one settled ledger
     row, and the balance delta must equal the sum of its net debits. This is checked
     from the persisted ledger, not from the streaming handler's return value.

  3. B0 -- the atomic SQL reference is retained unchanged; we re-assert it here by
     confirming the hardened posture serves exactly the affordable count.

Local testbed only:  python -m experiments.run_cross_validation
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from attacks.class6_credit_race import run_burst
from attacks.m1_stream_abort import stream_and_abort
from attacks.m2_usage_authority import send
from defenses.m2_independent_checker import check_trial
from experiments import _mcommon as C

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
PROMPT = "cross validation of independently implemented accounting defenses"
SEED = 1337

M2_ARCHES = ["client", "client_logged", "client_total", "server_recount",
             "hybrid_reconcile", "upstream"]
MANIPS = ["honest", "under_report_output_50", "under_report_output_90",
          "drop_reasoning", "inflate_cached", "total_mismatch", "rounding_shave"]


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    m2_results, m1_results, b0_results = [], [], []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=180.0) as client:
        (await client.get("/health")).raise_for_status()
        db = await C.db_info(client)
        aid, key = await C.create_account(client, "cross-validation")

        # ---------------- 1. M2 independent verification -------------------- #
        print("M2: gateway verdict vs INDEPENDENT checker")
        for arch in M2_ARCHES:
            for manip in MANIPS:
                meta = await C.create_m_trial(client, aid, "m2", arch, "medium",
                                              PROMPT, SEED, initial_credits=1e8)
                tid = meta["trial_id"]
                for _ in range(args.reps):
                    await send(client, key, PROMPT, SEED, tid, manip)
                audit = await C.finalize_m_trial(client, tid)
                verdict = check_trial(audit, meta["prices"])
                verdict.update({"manipulation": manip})
                m2_results.append(verdict)
                flag = "OK " if verdict["verdict_agrees"] else "MISMATCH"
                print(f"  [{flag}] {arch:<18} {manip:<22} "
                      f"indep_leak={verdict['independent_total_leak']:<10} "
                      f"gw_leak={verdict['gateway_total_leak']:<10} "
                      f"disagree={verdict['disagreements']}")

        # ---------------- 2. M1 finalization cannot be bypassed ------------- #
        print("M1: independent verification that finalization is not bypassable")
        q = (await client.get("/admin/quote", params={"prompt": PROMPT, "seed": SEED})).json()
        n_out = int(q["completion_tokens"])
        for arch in ("post_completion", "reserve_reconcile", "no_reserve_settle", "pre_debit"):
            for pct in (0, 25, 50, 90):
                meta = await C.create_m_trial(client, aid, "m1", arch, "medium",
                                              PROMPT, SEED, initial_credits=1e8)
                tid = meta["trial_id"]
                issued = []
                for _ in range(args.reps):
                    rid, _read = await stream_and_abort(
                        client, key, PROMPT, SEED, tid, max(0, round(pct / 100 * n_out)))
                    issued.append(rid)
                await asyncio.sleep(0.4)
                audit = await C.finalize_m_trial(client, tid)

                ledger_ids = [r["request_id"] for r in audit["rows"]]
                # every issued request must have exactly one settled ledger row
                missing = [r for r in issued if r not in ledger_ids]
                dupes = [r for r in set(ledger_ids) if ledger_ids.count(r) > 1]
                net_sum = sum(D(r["net_debit"]) for r in audit["rows"])
                delta = (D(audit["initial_balance"]) - D(audit["final_balance"]))
                m1_results.append({
                    "architecture": arch, "abort_pct": pct, "issued": len(issued),
                    "ledger_rows": len(ledger_ids),
                    "missing_settlements": len(missing), "duplicate_settlements": len(dupes),
                    "conservation_ok": delta.quantize(Decimal("0.000001")) ==
                                       net_sum.quantize(Decimal("0.000001")),
                    "finalization_bypassed": bool(missing),
                })
                ok = "OK " if not missing and not dupes else "BYPASS"
                print(f"  [{ok}] {arch:<20} abort={pct:>3}% issued={len(issued)} "
                      f"settled={len(ledger_ids)} missing={len(missing)} dup={len(dupes)}")

        # ---------------- 3. B0 atomic SQL reference re-assertion ----------- #
        print("B0: atomic compare-and-decrement reference (unchanged)")
        (await client.post("/admin/config", json={"class6_credit_race": "hardened"})).raise_for_status()
        b0_acct = (await client.post("/admin/accounts",
                                     json={"name": "cv-b0", "balance": 0.0})).json()
        for conc in (10, 50):
            meta = (await client.post("/admin/trials", json={
                "account_id": b0_acct["id"], "concurrency": conc, "affordable": 5,
                "prompt": PROMPT, "seed": SEED})).json()
            burst = await run_burst(client, b0_acct["api_key"], PROMPT, SEED,
                                    meta["trial_id"], conc)
            audit = (await client.post(f"/admin/trials/{meta['trial_id']}/finalize")).json()
            ok = audit["served_count"] == 5 and D(audit["dollar_leak"]) == 0
            b0_results.append({"concurrency": conc, "served": audit["served_count"],
                               "affordable": 5, "leak": str(D(audit["dollar_leak"])),
                               "exactly_affordable": ok})
            print(f"  [{'OK ' if ok else 'FAIL'}] c={conc}: served={audit['served_count']}/5 "
                  f"leak={audit['dollar_leak']}")
        (await client.post("/admin/config", json={"class6_credit_race": "vulnerable"})).raise_for_status()

    m2_mismatch = [r for r in m2_results if not r["verdict_agrees"]]
    m1_bypass = [r for r in m1_results if r["finalization_bypassed"] or not r["conservation_ok"]]
    b0_fail = [r for r in b0_results if not r["exactly_affordable"]]

    payload = {
        "experiment": "cross_validation", "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "purpose": ("Verify defenses against an independently coded checker to reduce "
                    "self-confirmation bias."),
        "m2_independent_verification": m2_results,
        "m1_finalization_verification": m1_results,
        "b0_reference_verification": b0_results,
        "summary": {"m2_cells": len(m2_results), "m2_mismatches": len(m2_mismatch),
                    "m1_cells": len(m1_results), "m1_bypass_or_conservation_failures": len(m1_bypass),
                    "b0_cells": len(b0_results), "b0_failures": len(b0_fail),
                    "all_agree": not (m2_mismatch or m1_bypass or b0_fail)},
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"cross_validation_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    s = payload["summary"]
    print(f"\nM2: {s['m2_cells']} cells, {s['m2_mismatches']} mismatches")
    print(f"M1: {s['m1_cells']} cells, {s['m1_bypass_or_conservation_failures']} bypass/conservation failures")
    print(f"B0: {s['b0_cells']} cells, {s['b0_failures']} failures")
    print(f"ALL IMPLEMENTATIONS AGREE: {s['all_agree']}")
    print(f"-> {out}")
    if not s["all_agree"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
