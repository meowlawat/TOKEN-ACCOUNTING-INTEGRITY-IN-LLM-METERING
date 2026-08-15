"""Shared helpers for the M1/M2 experiment runners (raw-data producers)."""

from __future__ import annotations

import platform
from decimal import Decimal

import httpx


def money(v):
    return None if v is None else str(Decimal(str(v)))


async def reset_db(client: httpx.AsyncClient) -> None:
    (await client.post("/admin/reset-db")).raise_for_status()


async def db_info(client: httpx.AsyncClient) -> dict:
    r = await client.get("/admin/db-info")
    r.raise_for_status()
    return r.json()


async def quote(client: httpx.AsyncClient, prompt: str, seed: int) -> dict:
    r = await client.get("/admin/quote", params={"prompt": prompt, "seed": seed})
    r.raise_for_status()
    return r.json()


async def create_account(client: httpx.AsyncClient, name: str = "m-attacker") -> tuple[int, str]:
    r = await client.post("/admin/accounts", json={"name": name, "balance": 0.0})
    r.raise_for_status()
    b = r.json()
    return b["id"], b["api_key"]


async def create_m_trial(client, account_id, mechanism, architecture, price_tier, prompt, seed,
                         initial_credits=100000.0, params=None) -> dict:
    r = await client.post("/admin/m-trials", json={
        "account_id": account_id, "mechanism": mechanism, "architecture": architecture,
        "price_tier": price_tier, "prompt": prompt, "seed": seed,
        "initial_credits": initial_credits, "params": params or {}})
    r.raise_for_status()
    return r.json()


async def finalize_m_trial(client, trial_id) -> dict:
    r = await client.post(f"/admin/m-trials/{trial_id}/finalize")
    r.raise_for_status()
    return r.json()


def env_meta() -> dict:
    return {"python": platform.python_version(), "platform": platform.platform()}


def normalize_row(row: dict) -> dict:
    """Coerce money fields in an MRecord audit row to exact decimal strings."""
    money_fields = ["authoritative_cost", "committed_debit", "refund", "net_debit", "leak",
                    "balance_before", "balance_after"]
    out = dict(row)
    for f in money_fields:
        out[f] = money(row.get(f))
    return out
