"""Second accounting backend (Phase 3): does the result depend on how money is stored?

Runs the STRONGEST B0/M1/M2 cases against both accounting backends behind the same
semantic interface:

    mutable   a single mutable `credits.balance` row (original)
    ledger    append-only `ledger_entries`; balance is DERIVED as SUM(delta)

The attack logic, architectures, and integrity checks are unchanged --- only the storage
architecture differs. A difference in outcome would mean our conclusions are an artifact
of row-mutation semantics; identical outcomes support the claim that the results follow
from where synchronization, commitment and authority sit.

Local testbed only:
    python -m experiments.run_backend_comparison --base-url http://localhost:8002
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
from experiments import _mcommon as C

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
PROMPT = "backend generality probe for accounting security architecture"
SEED = 1337
BACKENDS = ("mutable", "ledger")


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


async def set_backend(client, name):
    r = await client.post("/admin/accounting-backend", json={"backend": name})
    r.raise_for_status()
    return r.json()["backend"]


async def m2_case(client, aid, key, arch, manip, reps):
    t = (await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m2", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT, "seed": SEED, "initial_credits": 1e6})).json()["trial_id"]
    for _ in range(reps):
        await send(client, key, PROMPT, SEED, t, manip)
    a = (await client.post(f"/admin/m-trials/{t}/finalize")).json()
    served = [r for r in a["rows"] if r["served"]]
    auth = sum(D(r["authoritative_cost"]) for r in served)
    return {"case": f"M2/{arch}/{manip}", "leak": str(D(a["total_leak"])),
            "efficiency": float(D(a["total_leak"]) / auth) if auth > 0 else 0.0,
            "invariant_violations": a["invariant_violations"], "reconciled": a["reconciled"],
            "records": a["record_count"]}


async def m1_case(client, aid, key, arch, abort_pct, n_out, reps):
    t = (await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m1", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT, "seed": SEED, "initial_credits": 1e6})).json()["trial_id"]
    after = None if abort_pct >= 100 else max(1, round(abort_pct / 100 * n_out))
    for _ in range(reps):
        await stream_and_abort(client, key, PROMPT, SEED, t, after)
    await asyncio.sleep(0.4)
    a = (await client.post(f"/admin/m-trials/{t}/finalize")).json()
    served = [r for r in a["rows"] if r["served"]]
    return {"case": f"M1/{arch}/abort{abort_pct:g}",
            "leak_per_request": str((D(a["total_leak"]) / len(served)) if served else Decimal(0)),
            "leak": str(D(a["total_leak"])), "invariant_violations": a["invariant_violations"],
            "reconciled": a["reconciled"], "records": a["record_count"]}


async def b0_case(client, aid, key, posture, concurrency, affordable=5):
    await client.post("/admin/config", json={"class6_credit_race": posture})
    meta = (await client.post("/admin/trials", json={
        "account_id": aid, "concurrency": concurrency, "affordable": affordable,
        "prompt": PROMPT, "seed": SEED})).json()
    await run_burst(client, key, PROMPT, SEED, meta["trial_id"], concurrency)
    a = (await client.post(f"/admin/trials/{meta['trial_id']}/finalize")).json()
    return {"case": f"B0/{posture}/c{concurrency}", "served": a["served_count"],
            "affordable": affordable, "leak": str(D(a["dollar_leak"])),
            "invariant_violations": a["invariant_violations"], "reconciled": a["reconciled"]}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8002")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results: dict[str, list] = {}
    async with httpx.AsyncClient(base_url=args.base_url, timeout=180.0) as client:
        (await client.get("/health")).raise_for_status()
        db = await C.db_info(client)
        q = (await client.get("/admin/quote", params={"prompt": PROMPT, "seed": SEED})).json()
        n_out = int(q["completion_tokens"])

        for backend in BACKENDS:
            active = await set_backend(client, backend)
            assert active == backend, f"backend did not switch: {active}"
            aid, key = await C.create_account(client, f"backend-{backend}")
            rows = []
            print(f"\n=== backend: {backend} ===")

            # M2 strongest cases (vulnerable + hardened)
            for arch, manip in (("client", "under_report_output_90"),
                                ("client_logged", "under_report_output_90"),
                                ("client_total", "total_mismatch"),
                                ("server_recount", "under_report_output_90"),
                                ("hybrid_reconcile", "total_mismatch")):
                r = await m2_case(client, aid, key, arch, manip, args.reps)
                rows.append(r)
                print(f"  {r['case']:<44} eff={r['efficiency']:.3f} viol={r['invariant_violations']:>2} recon={r['reconciled']}")

            # M1 strongest cases (early/late abort, vulnerable + hardened)
            for arch in ("post_completion", "reserve_refund_on_abort",
                         "reserve_reconcile", "no_reserve_settle"):
                for pct in (50, 90):
                    r = await m1_case(client, aid, key, arch, pct, n_out, args.reps)
                    rows.append(r)
                    print(f"  {r['case']:<44} leak/req={float(r['leak_per_request']):.4f} "
                          f"viol={r['invariant_violations']:>2} recon={r['reconciled']}")

            # B0 baseline both postures
            b0_acct = (await client.post("/admin/accounts",
                                         json={"name": f"b0-{backend}", "balance": 0.0})).json()
            for posture in ("vulnerable", "hardened"):
                for conc in (10, 50):
                    r = await b0_case(client, b0_acct["id"], b0_acct["api_key"], posture, conc)
                    rows.append(r)
                    print(f"  {r['case']:<44} served={r['served']}/{r['affordable']} "
                          f"leak={r['leak']} recon={r['reconciled']}")
            results[backend] = rows

        await set_backend(client, "mutable")  # restore default

    # ---- compare the two backends case-by-case ------------------------------
    by_case = {b: {r["case"]: r for r in rows} for b, rows in results.items()}
    cases = sorted(by_case["mutable"])
    diffs = []
    for c in cases:
        a, b = by_case["mutable"][c], by_case["ledger"].get(c)
        if b is None:
            diffs.append({"case": c, "issue": "missing in ledger backend"})
            continue
        keys = [k for k in a if k not in ("case",)]
        mismatch = {k: (a[k], b[k]) for k in keys if a[k] != b[k]}
        if mismatch:
            diffs.append({"case": c, "mismatch": mismatch})

    payload = {
        "experiment": "accounting_backend_comparison", "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "purpose": ("Determine whether accounting-security outcomes depend on the balance "
                    "storage architecture (mutable row vs append-only derived ledger)."),
        "parameters": {"reps": args.reps, "prompt": PROMPT, "seed": SEED, "n_out": n_out,
                       "backends": list(BACKENDS)},
        "results": results,
        "case_count": len(cases),
        "differences": diffs,
        "identical": not diffs,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"backend_comparison_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\ncases compared: {len(cases)} | differing: {len(diffs)} | IDENTICAL: {not diffs}")
    print(f"-> {out}")
    if diffs:
        for d in diffs[:8]:
            print("  DIFF:", d)


if __name__ == "__main__":
    asyncio.run(main())
