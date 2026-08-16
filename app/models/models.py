"""Database models: accounts, credit balances, trials, and the usage ledger.

Billing authority lives in ``credits.balance`` (the live, spendable quantity). The
``usage_records`` table is a per-request **ledger**: for every served completion it
records not only the intended cost but the *observed balance before and after* the
debit and the *applied* debit (``balance_before - balance_after``). That makes the
class-6 experiment mathematically auditable:

* ``amount actually debited`` for a trial can be derived two independent ways ---
  from the trial's ``initial_balance - final_balance`` snapshots, and from
  ``SUM(applied_debit)`` over the ledger --- and the two must reconcile.
* The safety invariant *completed => committed, non-refunded debit* is checkable
  per request: a served row with ``applied_debit < cost`` is a violation (the
  balance did not actually drop by the request's cost -- a lost update).

A ``Trial`` groups the requests of one experiment repetition and pins the exact
starting conditions (posture, concurrency, prices, seed, initial/final balance) so
no figure in the paper is ever entered by hand.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

# Money is stored as NUMERIC(18,6): 6 fractional digits, no float drift.
Money = Numeric(18, 6)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    credit: Mapped["Credit"] = relationship(back_populates="account", uselist=False)


class Credit(Base):
    __tablename__ = "credits"

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    # Anchor for the append-only backend: the balance there is DERIVED as
    # opening_balance + SUM(ledger_entries.delta) and `balance` is left untouched.
    opening_balance: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))

    account: Mapped["Account"] = relationship(back_populates="credit")


class LedgerEntry(Base):
    """Immutable accounting movement (append-only backend).

    Never updated or deleted by the accounting path; the balance is the sum of these
    rows over the account's opening balance.
    """

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    delta: Mapped[Decimal] = mapped_column(Money, nullable=False)  # +credit / -debit
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # reserve|debit|refund
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Trial(Base):
    """One experiment repetition: pins starting conditions and the balance snapshots."""

    __tablename__ = "trials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # uuid4 hex
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    posture: Mapped[str] = mapped_column(String(16), nullable=False)  # vulnerable | hardened
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    affordable: Mapped[int] = mapped_column(Integer, nullable=False)  # k: requests the budget covers
    model_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    unit_cost: Mapped[Decimal] = mapped_column(Money, nullable=False)
    price_prompt_per_1k: Mapped[Decimal] = mapped_column(Money, nullable=False)
    price_completion_per_1k: Mapped[Decimal] = mapped_column(Money, nullable=False)

    initial_balance: Mapped[Decimal] = mapped_column(Money, nullable=False)
    final_balance: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UsageRecord(Base):
    """Per-request ledger row (one per served completion)."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trial_id: Mapped[str | None] = mapped_column(
        ForeignKey("trials.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # Idempotency handle (also the join key to client-side timing).
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    posture: Mapped[str | None] = mapped_column(String(16), nullable=True)
    concurrency: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    price_prompt_per_1k: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    price_completion_per_1k: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    # Intended debit (server-side recount) and the observed effect on the balance.
    cost: Mapped[Decimal] = mapped_column(Money, nullable=False)
    balance_before: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    applied_debit: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    # Safety-invariant bookkeeping.
    served: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    committed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# --------------------------------------------------------------------------- #
# M-mechanism tables (M1 metering-commit timing, M2 usage-record authority).
# Kept separate from the B0 tables above so the validated baseline is untouched.
# --------------------------------------------------------------------------- #
class MTrial(Base):
    """One M1/M2 experiment repetition: pins architecture + starting conditions."""

    __tablename__ = "m_trials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    mechanism: Mapped[str] = mapped_column(String(8), nullable=False)      # m1 | m2
    architecture: Mapped[str] = mapped_column(String(32), nullable=False)
    price_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    model_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prices: Mapped[dict] = mapped_column(JSON, nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    initial_balance: Mapped[Decimal] = mapped_column(Money, nullable=False)
    final_balance: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MRecord(Base):
    """Per-request ledger row for an M1/M2 request (server-authoritative truth)."""

    __tablename__ = "m_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trial_id: Mapped[str | None] = mapped_column(
        ForeignKey("m_trials.id", ondelete="CASCADE"), index=True, nullable=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mechanism: Mapped[str] = mapped_column(String(8), nullable=False)
    architecture: Mapped[str] = mapped_column(String(32), nullable=False)

    # Token truth (server-observed).
    tokens_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_billed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Money (exact Decimal). authoritative_cost = C(r) for the value the client obtained.
    authoritative_cost: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    committed_debit: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    refund: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    net_debit: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    leak: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)

    balance_before: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    served: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invariant_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    detection_level: Mapped[str] = mapped_column(String(4), nullable=False, default="D0")

    # M1-specific.
    abort_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # M2-specific.
    manipulation: Mapped[str | None] = mapped_column(String(32), nullable=True)

    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
