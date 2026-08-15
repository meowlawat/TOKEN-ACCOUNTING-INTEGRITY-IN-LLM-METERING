"""Pydantic request/response models for the gateway and admin surface."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from .config import Mode


class CompleteRequest(BaseModel):
    """Body for the metered `/complete` endpoint."""

    prompt: str = Field(..., min_length=1)
    seed: int | None = None
    request_id: str | None = None
    trial_id: str | None = None
    concurrency: int | None = None
    stream: bool = False  # accepted for API realism; the server always meters the full completion


class CompleteResponse(BaseModel):
    request_id: str
    completion: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal
    balance_before: Decimal | None = None
    balance_after: Decimal | None = None
    applied_debit: Decimal | None = None
    committed: bool
    refunded: bool
    served: bool
    mode: Mode


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1)
    plan: str = "free"
    balance: float = 0.0


class AccountOut(BaseModel):
    id: int
    name: str
    plan: str
    api_key: str
    balance: Decimal
    usage_count: int
    usage_sum: Decimal


class ResetRequest(BaseModel):
    """Reset an account's balance and clear its ledger."""

    balance: float


class TopupRequest(BaseModel):
    amount: float


class QuoteOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal
    price_prompt_per_1k: Decimal
    price_completion_per_1k: Decimal


class ConfigUpdate(BaseModel):
    class6_credit_race: Mode | None = None


class ConfigOut(BaseModel):
    class6_credit_race: Mode


class TrialCreate(BaseModel):
    account_id: int
    concurrency: int = Field(..., ge=1)
    affordable: int = Field(..., ge=0)
    prompt: str = Field(..., min_length=1)
    seed: int | None = None


class TrialOut(BaseModel):
    trial_id: str
    account_id: int
    posture: Mode
    concurrency: int
    affordable: int
    model_seed: int
    unit_cost: Decimal
    price_prompt_per_1k: Decimal
    price_completion_per_1k: Decimal
    initial_balance: Decimal
    final_balance: Decimal | None = None


class UsageRow(BaseModel):
    request_id: str
    posture: str | None
    concurrency: int | None
    prompt_tokens: int
    completion_tokens: int
    price_prompt_per_1k: Decimal | None
    price_completion_per_1k: Decimal | None
    cost: Decimal
    balance_before: Decimal | None
    balance_after: Decimal | None
    applied_debit: Decimal | None
    served: bool
    committed: bool
    refunded: bool
    created_at: datetime


class TrialAudit(BaseModel):
    """Server-side, mechanically-derived reconciliation for one trial."""

    trial_id: str
    posture: Mode
    concurrency: int
    affordable: int
    unit_cost: Decimal
    initial_balance: Decimal
    final_balance: Decimal | None
    actual_debit: Decimal | None            # initial - final (balance-snapshot method)
    applied_debit_total: Decimal            # SUM(applied_debit) over served rows (ledger method)
    reconciled: bool | None                 # actual_debit == applied_debit_total
    served_count: int
    rejected_or_absent: int                 # requests without a served ledger row (server view)
    intended_debit_total_served: Decimal    # SUM(cost) over served rows == inference value obtained
    inference_value: Decimal                # == intended_debit_total_served
    dollar_leak: Decimal | None             # inference_value - actual_debit
    paid_requests: Decimal | None           # actual_debit / unit_cost
    unpaid_served: Decimal | None           # served_count - paid_requests
    over_served: int                        # max(served_count - affordable, 0)
    invariant_violations: int               # served rows with applied_debit < cost
    unauthorized_completion_tokens: int     # completion tokens obtained without a committed debit
    detection_status: str                   # none | partial | full
    rows: list[UsageRow]


class DbInfo(BaseModel):
    server_version: str
    transaction_isolation: str
    default_transaction_isolation: str
