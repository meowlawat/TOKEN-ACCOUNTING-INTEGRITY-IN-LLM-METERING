"""Class-6 regression suite: controls + safety-invariant checks.

Runs a fixed battery against the LOCAL gateway and exits non-zero if any check
fails. Covers the negative/control experiments and the safety invariant:

  C1  concurrency=1 (vulnerable)      -> NO leak (the race needs >= 2 concurrent txns)
  C2  insufficient balance, conc=1    -> 402, zero served, no over-serve
  C3  hardened at max concurrency     -> served == k, zero leak, invariant holds
  C4  vulnerable race confirmed       -> leak > 0, over-served > 0, lost updates,
                                         and the ledger still reconciles to the balance
  C5  hardened insufficient balance   -> all 402, zero served
  INV every served row reconciles: SUM(applied_debit) == initial - final (all trials)

Run against the LOCAL testbed only (docker compose up)::

    python -m experiments.regression_class6
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

import httpx

from attacks.class6_credit_race import run_burst

PROMPT = "benchmark the credit decrement race please"
SEED = 1337


def _D(x) -> Decimal | None:
    return None if x is None else Decimal(str(x))


class Checker:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        self.results.append((name, bool(condition), detail))

    @property
    def ok(self) -> bool:
        return all(passed for _, passed, _ in self.results)


async def _set_mode(client: httpx.AsyncClient, mode: str) -> None:
    (await client.post("/admin/config", json={"class6_credit_race": mode})).raise_for_status()


async def _run_trial(
    client: httpx.AsyncClient, account_id: int, api_key: str, concurrency: int, affordable: int
):
    meta = (
        await client.post(
            "/admin/trials",
            json={
                "account_id": account_id,
                "concurrency": concurrency,
                "affordable": affordable,
                "prompt": PROMPT,
                "seed": SEED,
            },
        )
    ).json()
    burst = await run_burst(client, api_key, PROMPT, SEED, meta["trial_id"], concurrency)
    audit = (await client.post(f"/admin/trials/{meta['trial_id']}/finalize")).json()
    return burst, audit


async def main() -> None:
    parser = argparse.ArgumentParser(description="Class-6 regression suite.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--k", type=int, default=10, help="affordable budget for the race checks")
    parser.add_argument("--max-concurrency", type=int, default=50)
    args = parser.parse_args()

    chk = Checker()
    limits = httpx.Limits(max_connections=args.max_concurrency + 20)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0, limits=limits) as client:
        (await client.get("/health")).raise_for_status()
        await client.post("/admin/reset-db")
        acct = (
            await client.post("/admin/accounts", json={"name": "regression", "balance": 0.0})
        ).json()
        account_id, api_key = acct["id"], acct["api_key"]

        # --- C1: concurrency=1 vulnerable => no race -------------------------
        await _set_mode(client, "vulnerable")
        _, a = await _run_trial(client, account_id, api_key, concurrency=1, affordable=args.k)
        chk.check("C1 conc=1 served==1", a["served_count"] == 1, f"served={a['served_count']}")
        chk.check("C1 conc=1 no leak", _D(a["dollar_leak"]) == 0, f"leak={a['dollar_leak']}")
        chk.check("C1 conc=1 no invariant violations", a["invariant_violations"] == 0,
                  f"violations={a['invariant_violations']}")
        chk.check("C1 conc=1 reconciled", a["reconciled"] is True, f"reconciled={a['reconciled']}")

        # --- C2: insufficient balance (k=0), no concurrency ------------------
        _, a = await _run_trial(client, account_id, api_key, concurrency=1, affordable=0)
        chk.check("C2 insufficient served==0", a["served_count"] == 0, f"served={a['served_count']}")
        chk.check("C2 insufficient over_served==0", a["over_served"] == 0, f"over={a['over_served']}")
        chk.check("C2 insufficient no leak", (_D(a["dollar_leak"]) or Decimal(0)) == 0,
                  f"leak={a['dollar_leak']}")

        # --- C4: vulnerable race confirmed at high concurrency ---------------
        burst, a = await _run_trial(client, account_id, api_key, concurrency=30, affordable=args.k)
        served = a["served_count"]
        chk.check("C4 vuln all served", served == 30, f"served={served}")
        chk.check("C4 vuln leak>0", (_D(a["dollar_leak"]) or Decimal(0)) > 0, f"leak={a['dollar_leak']}")
        chk.check("C4 vuln over-served>0", a["over_served"] > 0, f"over={a['over_served']}")
        chk.check("C4 vuln lost updates (violations>=1)", a["invariant_violations"] >= 1,
                  f"violations={a['invariant_violations']}")
        chk.check("C4 vuln underpaid (actual_debit < inference_value)",
                  (_D(a["actual_debit"]) or Decimal(0)) < _D(a["inference_value"]),
                  f"actual_debit={a['actual_debit']} inference_value={a['inference_value']}")
        chk.check("C4 vuln ledger reconciles", a["reconciled"] is True, f"reconciled={a['reconciled']}")

        # --- C3: hardened safe at max concurrency ----------------------------
        await _set_mode(client, "hardened")
        _, a = await _run_trial(client, account_id, api_key, concurrency=args.max_concurrency,
                                affordable=args.k)
        chk.check("C3 hardened served==k", a["served_count"] == args.k,
                  f"served={a['served_count']} k={args.k}")
        chk.check("C3 hardened no leak", (_D(a["dollar_leak"]) or Decimal(0)) == 0,
                  f"leak={a['dollar_leak']}")
        chk.check("C3 hardened no over-serve", a["over_served"] == 0, f"over={a['over_served']}")
        chk.check("C3 hardened no invariant violations", a["invariant_violations"] == 0,
                  f"violations={a['invariant_violations']}")
        chk.check("C3 hardened reconciled", a["reconciled"] is True, f"reconciled={a['reconciled']}")

        # --- C5: hardened insufficient balance -------------------------------
        _, a = await _run_trial(client, account_id, api_key, concurrency=10, affordable=0)
        chk.check("C5 hardened insufficient served==0", a["served_count"] == 0,
                  f"served={a['served_count']}")

    # Report
    width = max(len(name) for name, _, _ in chk.results)
    print("=" * (width + 20))
    print("CLASS 6 REGRESSION SUITE")
    print("=" * (width + 20))
    for name, passed, detail in chk.results:
        status = "PASS" if passed else "FAIL"
        line = f"{name:<{width}}  {status}"
        if not passed and detail:
            line += f"   [{detail}]"
        print(line)
    print("=" * (width + 20))
    passed_n = sum(1 for _, p, _ in chk.results if p)
    print(f"{passed_n}/{len(chk.results)} checks passed")
    if not chk.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
