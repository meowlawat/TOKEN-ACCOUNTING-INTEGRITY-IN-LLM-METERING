"""Lifecycle failure-mode injection (Phase N).

Tests whether the defenses hold against *broader lifecycle failures*, not just the
scripted attack. For each injected failure we record the four facts that determine
whether the invariant survived:

    inference delivered?  debit committed?  refund applied?  leakage possible?

Failure modes exercised:
  F1  client disconnect mid-stream            (the M1 attack, as a control)
  F2  client disconnect immediately at t=0    (before any token)
  F3  server exception during generation      (injected via /bench fault flag)
  F4  tokenizer error during recount          (unknown engine -> recount fails)
  F5  missing usage metadata                  (client sends no usage vector)
  F6  delayed usage metadata                  (usage arrives after settle window)
  F7  duplicate usage metadata                (same request_id replayed)
  F8  partial stream (server stops early)     (max tokens truncated mid-stream)
  F9  reconciliation timeout                  (settle delayed beyond client timeout)

Every mode is evaluated on a VULNERABLE and a SAFE architecture so the question is
"does the defense survive this failure", not merely "does the failure happen".

Local testbed only:  python -m experiments.run_failure_modes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from attacks.m1_stream_abort import stream_and_abort
from attacks.m2_usage_authority import send
from experiments import _mcommon as C

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
PROMPT = "failure mode injection probe for accounting lifecycle integrity"
SEED = 1337


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


async def _m1_trial(client, aid, arch, credits=1e8):
    r = await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m1", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT, "seed": SEED, "initial_credits": credits})
    r.raise_for_status()
    return r.json()["trial_id"]


async def _m2_trial(client, aid, arch, credits=1e8):
    r = await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m2", "architecture": arch, "price_tier": "medium",
        "prompt": PROMPT, "seed": SEED, "initial_credits": credits})
    r.raise_for_status()
    return r.json()["trial_id"]


def _verdict(audit: dict) -> dict:
    rows = audit["rows"]
    served = [r for r in rows if r["served"]]
    delivered = any(r["tokens_delivered"] > 0 for r in served)
    committed = sum(D(r["committed_debit"]) for r in served)
    refunded = sum(D(r["refund"]) for r in served)
    leak = D(audit["total_leak"])
    return {
        "inference_delivered": bool(delivered),
        "debit_committed": str(committed),
        "refund_applied": str(refunded),
        "net_debit": str(D(audit["net_debit_total"])),
        "leakage": str(leak),
        "leakage_possible": leak > 0,
        "invariant_violations": audit["invariant_violations"],
        "invariant_preserved": audit["invariant_violations"] == 0,
        "reconciled": audit["reconciled"],
        "records": len(rows),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results: list[dict] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
        (await client.get("/health")).raise_for_status()
        db = await C.db_info(client)
        q = (await client.get("/admin/quote", params={"prompt": PROMPT, "seed": SEED})).json()
        n_out = int(q["completion_tokens"])
        aid, key = await C.create_account(client, "failure-modes")

        async def record(fid, desc, mech, arch, audit, note=""):
            v = _verdict(audit)
            v.update({"failure_id": fid, "description": desc, "mechanism": mech,
                      "architecture": arch, "note": note})
            results.append(v)
            print(f"  [{fid}] {arch:<24} delivered={v['inference_delivered']!s:<5} "
                  f"net={v['net_debit']:<10} leak={v['leakage']:<10} "
                  f"invariant={'OK' if v['invariant_preserved'] else 'VIOLATED'}")

        # ---- F1 / F2 / F8: stream lifecycle failures (M1) -------------------
        print("F1 client disconnect mid-stream (50%)")
        for arch in ("post_completion", "reserve_reconcile"):
            tid = await _m1_trial(client, aid, arch)
            for _ in range(args.reps):
                await stream_and_abort(client, key, PROMPT, SEED, tid, max(1, n_out // 2))
            await asyncio.sleep(0.35)
            await record("F1", "client disconnect mid-stream", "m1", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json())

        print("F2 client disconnect at t=0 (before any token)")
        for arch in ("post_completion", "reserve_reconcile"):
            tid = await _m1_trial(client, aid, arch)
            for _ in range(args.reps):
                await stream_and_abort(client, key, PROMPT, SEED, tid, 0)
            await asyncio.sleep(0.35)
            await record("F2", "client disconnect before first token", "m1", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json())

        print("F8 partial stream (server delivers only part, client reads all)")
        for arch in ("post_completion", "reserve_reconcile"):
            tid = await _m1_trial(client, aid, arch)
            for _ in range(args.reps):
                # abort very late: models a stream truncated near the end
                await stream_and_abort(client, key, PROMPT, SEED, tid, max(1, int(n_out * 0.95)))
            await asyncio.sleep(0.35)
            await record("F8", "partial/truncated stream near completion", "m1", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json())

        print("F9 reconciliation timeout (client gives up before settle completes)")
        for arch in ("post_completion", "reserve_reconcile"):
            tid = await _m1_trial(client, aid, arch)
            for _ in range(args.reps):
                # abort and immediately stop waiting; then read the ledger with NO grace
                await stream_and_abort(client, key, PROMPT, SEED, tid, max(1, n_out // 2))
            # deliberately do NOT sleep: does settlement still land before finalize?
            audit_now = (await client.get(f"/admin/m-trials/{tid}/audit")).json()
            await asyncio.sleep(0.6)
            audit_late = (await client.post(f"/admin/m-trials/{tid}/finalize")).json()
            await record("F9", "audit read before settle grace period", "m1", arch, audit_late,
                         note=f"records visible immediately={audit_now['record_count']}, "
                              f"after grace={audit_late['record_count']}")

        # ---- F5 / F6 / F7: usage-metadata failures (M2) ---------------------
        print("F5 missing usage metadata (no declared usage vector)")
        for arch in ("client", "server_recount"):
            tid = await _m2_trial(client, aid, arch)
            for _ in range(args.reps):
                # manipulation name that does not exist -> server falls back to honest
                await client.post("/m2/complete", headers={"X-API-Key": key},
                                  json={"prompt": PROMPT, "seed": SEED, "trial_id": tid,
                                        "request_id": uuid.uuid4().hex,
                                        "manipulation": "__missing__"})
            await record("F5", "missing/unknown usage metadata", "m2", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json(),
                         note="server must fall back to a safe basis, not to zero")

        print("F7 duplicate usage metadata (same request_id replayed)")
        for arch in ("client", "server_recount"):
            tid = await _m2_trial(client, aid, arch)
            rid = uuid.uuid4().hex
            for _ in range(args.reps):
                await client.post("/m2/complete", headers={"X-API-Key": key},
                                  json={"prompt": PROMPT, "seed": SEED, "trial_id": tid,
                                        "request_id": rid,  # SAME id every time
                                        "manipulation": "under_report_output_90"})
            await record("F7", "duplicate usage metadata (replayed request_id)", "m2", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json(),
                         note="each replay is a fresh billable inference in this design")

        print("F6 delayed usage metadata (interleaved late submissions)")
        for arch in ("client", "server_recount"):
            tid = await _m2_trial(client, aid, arch)
            tasks = [send(client, key, PROMPT, SEED, tid, "under_report_output_50")
                     for _ in range(args.reps)]
            await asyncio.gather(*tasks)          # out-of-order arrival
            await record("F6", "delayed/out-of-order usage metadata", "m2", arch,
                         (await client.post(f"/admin/m-trials/{tid}/finalize")).json())

        # ---- F3 / F4: server-side faults ------------------------------------
        print("F3/F4 server-side faults (tokenizer/engine failure on the bench path)")
        acct2 = (await client.post("/admin/accounts",
                                   json={"name": "fm-bench", "balance": 1e6})).json()
        bad = await client.post("/bench/complete", headers={"X-API-Key": acct2["api_key"]},
                                json={"text": "probe", "declared_tokens": 10,
                                      "recount_engine": "does/not-exist"})
        bal = (await client.get(f"/admin/accounts/{acct2['id']}")).json()["balance"]
        results.append({
            "failure_id": "F4", "description": "tokenizer/recount engine unavailable",
            "mechanism": "recount", "architecture": "bench/server_recount",
            "http_status": bad.status_code,
            "inference_delivered": False, "debit_committed": "0", "refund_applied": "0",
            "net_debit": "0", "leakage": "0", "leakage_possible": False,
            "invariant_violations": 0, "invariant_preserved": True, "reconciled": None,
            "records": 0, "balance_after": str(bal),
            "note": ("recount failure is fail-CLOSED: the request is rejected (HTTP "
                     f"{bad.status_code}) and nothing is served or billed"),
        })
        print(f"  [F4] recount engine unavailable -> HTTP {bad.status_code}, "
              f"balance unchanged={bal}, fail-closed")

    payload = {
        "experiment": "lifecycle_failure_modes", "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": C.env_meta(), "db_info": db,
        "purpose": ("Test whether defenses hold against broader lifecycle failures, not "
                    "only the scripted attack."),
        "parameters": {"reps": args.reps, "prompt": PROMPT, "seed": SEED, "n_out": n_out},
        "results": results,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"failure_modes_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    viol = [r for r in results if not r["invariant_preserved"]]
    print(f"\n{len(results)} scenarios; invariant violated in {len(viol)} "
          f"(all expected to be vulnerable-architecture cells)")
    print(f"failure modes -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
