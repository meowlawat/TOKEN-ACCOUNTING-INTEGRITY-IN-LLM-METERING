"""Raw-data runner for flaw class 6 (credit-decrement race).

Protocol (one *trial* = one repetition):
  1. ``POST /admin/trials``          -> pin posture/concurrency/prices/seed, set the
                                        affordable balance, snapshot ``initial_balance``.
  2. fire ``concurrency`` identical  -> each request carries ``trial_id`` + ``request_id``.
     ``/complete`` calls at once
  3. ``POST /admin/trials/{id}/finalize`` -> snapshot ``final_balance`` and return the
                                        server-side mechanical audit (per-request ledger
                                        + reconciliation).

The runner joins client-side timing to the server ledger by ``request_id`` and
writes a single machine-readable JSON with **every request and every balance
snapshot**. It computes no headline statistics itself -- that is
``experiments/summarize_class6.py``'s job, working from this raw file only.

Run against the LOCAL testbed only::

    docker compose up --build -d
    python -m experiments.run_class6

Requires ``httpx`` on the host.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from attacks.class6_credit_race import BurstResult, run_burst

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
SCHEMA_VERSION = 2


def _money(value) -> str:
    """Normalize any JSON-decoded money value to an exact decimal string."""
    if value is None:
        return None  # type: ignore[return-value]
    return str(Decimal(str(value)))


async def _reset_db(client: httpx.AsyncClient) -> None:
    (await client.post("/admin/reset-db")).raise_for_status()


async def _db_info(client: httpx.AsyncClient) -> dict:
    resp = await client.get("/admin/db-info")
    resp.raise_for_status()
    return resp.json()


async def _quote(client: httpx.AsyncClient, prompt: str, seed: int) -> dict:
    resp = await client.get("/admin/quote", params={"prompt": prompt, "seed": seed})
    resp.raise_for_status()
    return resp.json()


async def _create_account(client: httpx.AsyncClient) -> tuple[int, str]:
    resp = await client.post(
        "/admin/accounts", json={"name": "attacker-class6", "plan": "free", "balance": 0.0}
    )
    resp.raise_for_status()
    body = resp.json()
    return body["id"], body["api_key"]


async def _set_mode(client: httpx.AsyncClient, mode: str) -> None:
    (await client.post("/admin/config", json={"class6_credit_race": mode})).raise_for_status()


async def _create_trial(
    client: httpx.AsyncClient, account_id: int, concurrency: int, affordable: int, prompt: str, seed: int
) -> dict:
    resp = await client.post(
        "/admin/trials",
        json={
            "account_id": account_id,
            "concurrency": concurrency,
            "affordable": affordable,
            "prompt": prompt,
            "seed": seed,
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _finalize_trial(client: httpx.AsyncClient, trial_id: str) -> dict:
    resp = await client.post(f"/admin/trials/{trial_id}/finalize")
    resp.raise_for_status()
    return resp.json()


def _merge_requests(burst: BurstResult, audit: dict) -> list[dict]:
    """Join client-side timing (all issued requests) with server ledger rows (served)."""
    server_by_id = {row["request_id"]: row for row in audit.get("rows", [])}
    merged: list[dict] = []
    for r in burst.results:
        row = server_by_id.get(r.request_id)
        merged.append(
            {
                "request_id": r.request_id,
                "http_status": r.status,
                "served": r.status == 200,
                "latency_s": r.latency_s,
                # server-side ledger truth (None for rejected/errored requests):
                "prompt_tokens": (row or {}).get("prompt_tokens"),
                "completion_tokens": (row or {}).get("completion_tokens"),
                "cost": _money((row or {}).get("cost")) if row else None,
                "balance_before": _money((row or {}).get("balance_before")) if row else None,
                "balance_after": _money((row or {}).get("balance_after")) if row else None,
                "applied_debit": _money((row or {}).get("applied_debit")) if row else None,
                "committed": (row or {}).get("committed"),
                "refunded": (row or {}).get("refunded"),
            }
        )
    return merged


def _trial_record(
    rep: int, trial_meta: dict, burst: BurstResult, audit: dict
) -> dict:
    return {
        "trial_id": trial_meta["trial_id"],
        "rep": rep,
        "posture": audit["posture"],
        "concurrency": audit["concurrency"],
        "affordable_k": audit["affordable"],
        "unit_cost": _money(audit["unit_cost"]),
        "initial_balance": _money(audit["initial_balance"]),
        "final_balance": _money(audit["final_balance"]),
        # client-side burst tallies:
        "client_served": burst.served,
        "client_rejected": burst.rejected,
        "client_errors": burst.errors,
        # server-side mechanical audit (authoritative):
        "server_served_count": audit["served_count"],
        "actual_debit": _money(audit["actual_debit"]),
        "applied_debit_total": _money(audit["applied_debit_total"]),
        "reconciled": audit["reconciled"],
        "inference_value": _money(audit["inference_value"]),
        "dollar_leak": _money(audit["dollar_leak"]),
        "paid_requests": _money(audit["paid_requests"]),
        "unpaid_served": _money(audit["unpaid_served"]),
        "over_served": audit["over_served"],
        "invariant_violations": audit["invariant_violations"],
        "unauthorized_completion_tokens": audit["unauthorized_completion_tokens"],
        "detection_status": audit["detection_status"],
        "requests": _merge_requests(burst, audit),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Raw-data runner for flaw class 6.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--prompt", default="benchmark the credit decrement race please")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--affordable", type=int, default=10, help="k: requests the fixed balance covers")
    parser.add_argument(
        "--concurrency", type=int, nargs="+", default=[1, 2, 5, 10, 20, 30, 50]
    )
    parser.add_argument("--reps", type=int, default=30, help="repetitions per (posture, concurrency)")
    parser.add_argument("--modes", nargs="+", default=["vulnerable", "hardened"],
                        choices=["vulnerable", "hardened"])
    parser.add_argument("--out", default=None, help="explicit output path (else results/class6_<ts>.json)")
    parser.add_argument("--no-reset-db", action="store_true", help="do not drop/recreate tables first")
    args = parser.parse_args()

    max_conc = max(args.concurrency)
    limits = httpx.Limits(max_connections=max_conc + 20, max_keepalive_connections=max_conc + 20)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0, limits=limits) as client:
        (await client.get("/health")).raise_for_status()
        if not args.no_reset_db:
            await _reset_db(client)
        db_info = await _db_info(client)
        quote = await _quote(client, args.prompt, args.seed)
        account_id, api_key = await _create_account(client)

        trials: list[dict] = []
        for mode in args.modes:
            await _set_mode(client, mode)
            for concurrency in args.concurrency:
                for rep in range(args.reps):
                    meta = await _create_trial(
                        client, account_id, concurrency, args.affordable, args.prompt, args.seed
                    )
                    burst = await run_burst(
                        client, api_key, args.prompt, args.seed, meta["trial_id"], concurrency
                    )
                    audit = await _finalize_trial(client, meta["trial_id"])
                    trials.append(_trial_record(rep, meta, burst, audit))
                cell = [t for t in trials if t["posture"] == mode and t["concurrency"] == concurrency]
                leaks = sum(1 for t in cell if t["dollar_leak"] and Decimal(t["dollar_leak"]) > 0)
                mean_served = sum(t["server_served_count"] for t in cell) / len(cell)
                print(
                    f"[{mode:<10} c={concurrency:>3}] reps={len(cell)} "
                    f"mean_served={mean_served:5.1f} leaking_trials={leaks}/{len(cell)}"
                )

    payload = {
        "experiment": "class6_credit_decrement_race",
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "db_info": db_info,
        "parameters": {
            "prompt": args.prompt,
            "model_seed": args.seed,
            "affordable_k": args.affordable,
            "unit_cost": _money(quote["cost"]),
            "price_prompt_per_1k": _money(quote["price_prompt_per_1k"]),
            "price_completion_per_1k": _money(quote["price_completion_per_1k"]),
            "prompt_tokens": quote["prompt_tokens"],
            "completion_tokens": quote["completion_tokens"],
            "concurrency_levels": args.concurrency,
            "reps_per_cell": args.reps,
            "postures": args.modes,
        },
        "trials": trials,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = payload["generated_at"]
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"class6_{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nraw results written to {out_path}  ({len(trials)} trials)")


if __name__ == "__main__":
    asyncio.run(main())
