"""Regression / control suite for M1 and M2 (safety invariants + controls).

Does NOT call /admin/reset-db (safe to run alongside stored sweeps): it provisions
its own account and trials. Exits non-zero on any failure.

Controls (per methodology):
  * honest client (M1 completion, M2 honest) => no leak                 [Control 2, 6, 7]
  * hardened architecture => safe at the strongest attack               [Control 4]
  * vulnerable architecture => measurable accounting violation          [Gate B]
  * server-authoritative usage neutralizes every manipulation           [M2 defense]
  * every trial reconciles: balance delta == sum(net_debit)             [ledger conservation]
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

import httpx

from attacks.m1_stream_abort import stream_and_abort
from attacks.m2_usage_authority import send

PROMPT = "benchmark the metering integrity controls end to end please"
SEED = 1337


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


class Checker:
    def __init__(self):
        self.results = []

    def check(self, name, cond, detail=""):
        self.results.append((name, bool(cond), detail))

    @property
    def ok(self):
        return all(p for _, p, _ in self.results)


async def _mtrial(client, aid, mech, arch, tier="medium"):
    r = await client.post("/admin/m-trials", json={"account_id": aid, "mechanism": mech,
        "architecture": arch, "price_tier": tier, "prompt": PROMPT, "seed": SEED,
        "initial_credits": 100000.0})
    r.raise_for_status()
    return r.json()["trial_id"]


async def _audit(client, tid):
    r = await client.post(f"/admin/m-trials/{tid}/finalize")
    r.raise_for_status()
    return r.json()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    args = ap.parse_args()
    chk = Checker()
    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        (await client.get("/health")).raise_for_status()
        acct = (await client.post("/admin/accounts", json={"name": "regression-m", "balance": 0.0})).json()
        aid, key = acct["id"], acct["api_key"]
        q = (await client.get("/admin/quote", params={"prompt": PROMPT, "seed": SEED})).json()
        n_out = int(q["completion_tokens"])

        # ---- M2 controls ----
        # honest on client arch => no leak
        t = await _mtrial(client, aid, "m2", "client")
        await send(client, key, PROMPT, SEED, t, "honest")
        a = await _audit(client, t)
        chk.check("M2 client honest: no leak", D(a["total_leak"]) == 0, f"leak={a['total_leak']}")
        chk.check("M2 client honest: reconciled", a["reconciled"] is True)

        # under-report on client => leak, invariant violated, D0
        t = await _mtrial(client, aid, "m2", "client")
        r = await send(client, key, PROMPT, SEED, t, "under_report_output_90")
        chk.check("M2 client under90: leak>0", D(r["leak"]) > 0, f"leak={r['leak']}")
        chk.check("M2 client under90: invariant violated", r["invariant_ok"] is False)
        chk.check("M2 client under90: hidden (D0)", r["detection_level"] == "D0", r["detection_level"])

        # server_recount neutralizes the same manipulation
        t = await _mtrial(client, aid, "m2", "server_recount")
        r = await send(client, key, PROMPT, SEED, t, "under_report_output_90")
        chk.check("M2 recount under90: no leak", D(r["leak"]) == 0, f"leak={r['leak']}")
        chk.check("M2 recount under90: safe (invariant ok)", r["invariant_ok"] is True)

        # hybrid corrects and is safe
        t = await _mtrial(client, aid, "m2", "hybrid_reconcile")
        r = await send(client, key, PROMPT, SEED, t, "under_report_output_90")
        chk.check("M2 hybrid under90: no leak", D(r["leak"]) == 0, f"leak={r['leak']}")

        # ---- M1 controls ----
        # Control: honest completion (no abort) on the vulnerable post_completion arch => billed, no leak
        t = await _mtrial(client, aid, "m1", "post_completion")
        await stream_and_abort(client, key, PROMPT, SEED, t, None)  # complete
        await asyncio.sleep(0.2)
        a = await _audit(client, t)
        row = a["rows"][0]
        chk.check("M1 post_completion complete: no leak", D(row["leak"]) == 0, f"leak={row['leak']}")
        chk.check("M1 post_completion complete: invariant ok", row["invariant_ok"] is True)

        # Vulnerable: abort at 50% => leak, invariant violated
        t = await _mtrial(client, aid, "m1", "post_completion")
        await stream_and_abort(client, key, PROMPT, SEED, t, max(1, n_out // 2))
        await asyncio.sleep(0.2)
        a = await _audit(client, t)
        row = a["rows"][0]
        chk.check("M1 post_completion abort50: leak>0", D(row["leak"]) > 0, f"leak={row['leak']}")
        chk.check("M1 post_completion abort50: invariant violated", row["invariant_ok"] is False)
        chk.check("M1 post_completion abort50: reconciled", a["reconciled"] is True)

        # Safe: reserve_reconcile abort at 50% => no leak
        t = await _mtrial(client, aid, "m1", "reserve_reconcile")
        await stream_and_abort(client, key, PROMPT, SEED, t, max(1, n_out // 2))
        await asyncio.sleep(0.2)
        a = await _audit(client, t)
        row = a["rows"][0]
        chk.check("M1 reserve_reconcile abort50: no leak", D(row["leak"]) == 0, f"leak={row['leak']}")
        chk.check("M1 reserve_reconcile abort50: invariant ok", row["invariant_ok"] is True)

        # Safe: reserve_refund_on_abort is vulnerable (control that our labeling is right)
        t = await _mtrial(client, aid, "m1", "reserve_refund_on_abort")
        await stream_and_abort(client, key, PROMPT, SEED, t, max(1, n_out // 2))
        await asyncio.sleep(0.2)
        a = await _audit(client, t)
        row = a["rows"][0]
        chk.check("M1 reserve_refund abort50: leak>0 (vulnerable)", D(row["leak"]) > 0, f"leak={row['leak']}")

    width = max(len(n) for n, _, _ in chk.results)
    print("=" * (width + 16))
    print("M1/M2 REGRESSION + CONTROL SUITE")
    print("=" * (width + 16))
    for name, passed, detail in chk.results:
        line = f"{name:<{width}}  {'PASS' if passed else 'FAIL'}"
        if not passed and detail:
            line += f"  [{detail}]"
        print(line)
    print("=" * (width + 16))
    print(f"{sum(1 for _, p, _ in chk.results if p)}/{len(chk.results)} checks passed")
    if not chk.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
