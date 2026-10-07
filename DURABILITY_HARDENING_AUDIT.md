# Durability Hardening Audit

Follows `FINAL_HARDENING_AUDIT.md` §5, which found that a hard `SIGKILL` of the Redis
container permanently lost a queued, not-yet-due B0-async settlement event. This document
covers the smallest technically sound fix for that specific gap: a PostgreSQL
transactional outbox for the B0-async settlement path only. It does not touch M1, M2, the
B0 synchronous baseline, the atomic defense (C3), or the authorization/admission step that
is the actual subject of the two-machine experiment and the `AsyncSettlementTOCTOU.tla`
formal model.

---

## Pre-implementation questions (answered before any code was written)

**1. Can the existing PostgreSQL schema support a transactional outbox cleanly?**
Yes. `app/db.py` uses one shared async engine/session factory across the whole
application; a new table fits alongside `credits`/`m_records` with no conflict, and the
existing `Base.metadata.create_all` lifespan hook (`app/main.py`) picks up a new model
automatically — confirmed directly: `\d outbox_events` showed the table created on the
next gateway startup with no migration step added.

**2. Exactly where should the outbox insert occur?**
Inside `async_b0_complete`, in the SAME transaction that already writes the `MRecord`
audit row (`app/async_routes.py`, the `async with SessionLocal() as s:` block) — the one
and only place a B0-async event is created.

**3. What transaction currently establishes the economic commitment?**
**None.** This is the key fact the inspection surfaced, re-confirmed by reading the code
directly (not assumed from memory): `async_b0_complete`'s authorization step
(`ledger.read_balance`) is a plain, read-only `SELECT` that writes nothing. The *only*
durable write in the entire handler was the `MRecord` audit row, which explicitly records
`committed_debit=Decimal("0")` — i.e., it documents that nothing has been committed yet.
The vulnerability under study (the TOCTOU admission race, `FORMALIZATION_AUDIT.md`) exists
*because* no commitment is established at authorization time. The fix below does **not**
change this — it makes the *eventual* debit's existence durable, not the admission atomic.

**4. Can the current Redis worker be changed to consume from the durable outbox?**
Yes, as an additional, independent fallback path alongside the existing Redis-driven
`drain()`, not a replacement — detailed in §4/§5 below.

**5. What happens if the worker crashes:**
   - **a. before consuming?** The outbox row sits `pending`; recovered by either the
     normal Redis path (if Redis still has it) or the reconcile-from-outbox fallback (if
     not) on restart. Tested directly (§8, test B/G).
   - **b. after consuming but before settlement?** Cannot happen in the new design: the
     outbox-status claim and the actual balance decrement are the same database
     transaction (`ledger.claim_and_debit_outbox`), not two separate commits. A crash
     anywhere before that transaction commits leaves the row `pending` and the balance
     unchanged — safe, retried later. This was the specific gap identified in the
     pre-implementation design review and closed by construction, not left to chance.
   - **c. after settlement but before marking processed?** Also cannot happen, same
     reason — "settled" and "marked processed" are not two separate steps.

**6. What happens if Redis dies?**
Previously: permanent, silent loss (the discovered gap). Now: the queued copy in Redis is
still lost, but the durable outbox row survives (it was written to Postgres before Redis
was ever involved), and `reconcile_outbox` recovers and settles it once due, independent of
Redis's state. Tested directly (§8, test D) — the headline result of this audit.

**7. What happens if the same event is delivered twice?**
Harmless. Both the Redis-driven path and the reconcile-from-outbox path go through the
identical atomic conditional update
(`UPDATE outbox_events SET status='applied' WHERE event_id=:id AND status='pending'`);
whichever reaches a given row first wins the claim, the other sees zero rows affected and
skips. Tested directly with the existing `duplicate_event` fault injection (§8, test E).

**8. What happens if the database transaction rolls back?**
Nothing is queued anywhere. The Redis push (`_emit`) was moved to occur *after* the
outbox+`MRecord` transaction commits (previously it happened *before* — see §3 root
cause), so a rollback of that transaction means the client never received a `served: true`
response and Redis was never touched. Verified analytically from the code structure (an
`async with SessionLocal() as s:` block rolls back automatically on an unhandled
exception, and `_emit` is a separate, later statement, never reached if the `async with`
block raises) — **not verified by forcing a live rollback**, which is explicitly listed as
not performed in §9.

**9. Can an event ever exist without its corresponding economic commitment?**
No request-visible "commitment" exists in this architecture at all (see answer 3) — the
relevant question is reworded: can a Redis-queued event exist without a corresponding
durable outbox row? Before this fix: yes, trivially (Redis was pushed to first). After:
no — the outbox commit happens strictly before `_emit`, so every event Redis could ever
receive already has a durable row backing it.

**10. Can an economic commitment ever exist without a durable pending event?**
N/A under question 3's answer — there is no separate "commitment" independent of the
outbox row; the outbox row *is* the durable record of the pending debit.

---

## 1. Old architecture

```
async_b0_complete:
    SELECT balance (read-only, no write)
    if balance < cost: return served=False
    new_event()                         # in-memory UsageEvent, not yet durable
    _emit(event)                        # Redis rpush -- FIRST durable-ish write
    INSERT MRecord (separate session), COMMIT
    return served=True
```

Redis was the *only* record of the pending debit between `_emit` and the `MRecord`
commit, and remained the *sole* record of it thereafter until a worker drained it.

## 2. Discovered durability failure

Direct test (not simulated): queued a real event with `reconcile_delay_ms=30000`,
confirmed `queue_depth=1` and a `pending` state existed nowhere durable in Postgres
(there was no outbox table at the time), then `docker kill -s SIGKILL` on the Redis
container, restarted it, and found `queue_depth=0` and the account balance never debited.
**Permanent, silent loss**, confirmed by direct measurement.

## 3. Root cause

Redis's default persistence here (`appendonly no`, `save 3600 1 300 100 60 10000`,
confirmed via `redis-cli CONFIG GET`) does not snapshot on every write. A hard crash
between snapshot points loses anything written since the last one. Combined with the fact
that Redis was the *only* durable record of a pending debit, any such crash within that
window is unrecoverable by construction, not merely unlikely.

## 4. New architecture

```
async_b0_complete:
    SELECT balance (read-only, no write -- UNCHANGED, the TOCTOU window is untouched)
    if balance < cost: return served=False
    new_event()
    BEGIN TRANSACTION
        INSERT OutboxEvent(status='pending', event_id, account_id, amount, deliver_after_ns)
        INSERT MRecord (audit row, as before)
    COMMIT                                # <-- durable source of truth, established HERE
    _emit(event)                          # Redis rpush -- now a FAST-PATH HINT ONLY
    return served=True

worker main loop, every poll interval:
    drain()                               # existing Redis-driven path, UNCHANGED logic;
                                           # for B0 events, its apply_debit callback now
                                           # claims the outbox row and debits atomically
                                           # (one transaction) instead of a plain debit
    reconcile_outbox()                    # NEW: Redis-independent fallback -- scans
                                           # Postgres directly for due+pending rows Redis
                                           # may have lost, claims+debits atomically
```

**Why this is not a transactional outbox applied to the authorization step:** the
authorization/admission decision (`SELECT balance`, `if balance < cost`) is completely
untouched. This fix only changes *where the pending debit's existence is durably
recorded* and *when Redis is told about it relative to that durability*. It does not make
admission atomic with commitment — doing so would eliminate the TOCTOU race entirely,
which is the opposite of this architecture's purpose as a research artifact. **No
semantics of any published or already-collected manuscript experiment changed as a
result** — confirmed directly: grepped every existing raw-data file for `fault=lost_event`
against the B0 endpoint and found none (`lost_event` was only ever exercised against M1,
a different code path this fix does not touch), and reran the full existing concurrency
and delay-sweep matrix locally after the fix (§8, test A) with results identical to the
pre-fix, already-published pattern.

## 5. Transaction boundary

The single atomic unit introduced by this fix is `ledger.claim_and_debit_outbox`
(`app/accounting/ledger.py`): one `UPDATE ... WHERE status='pending'` (the claim) followed
by one relative balance decrement (`debit_unchecked`), both inside the same
caller-supplied session, committed once by the caller. This is the unit that answers
question 5b/5c above: there is no intermediate, partially-applied state for this
transaction to crash into.

## 6. Failure matrix

| failure | before this fix | after this fix |
|---|---|---|
| Worker process killed, event not yet due | recoverable (Redis queue intact) | recoverable (two independent paths now: Redis queue, or outbox scan) |
| Worker process killed, event due, not yet applied | recoverable (Redis queue intact) | recoverable, same |
| Worker crashes mid-claim/mid-debit | not applicable (no claim step existed) | cannot happen — one atomic transaction |
| Redis hard crash (`SIGKILL`) | **event permanently lost** | **recovered** via `reconcile_outbox` once due |
| Duplicate delivery (Redis at-least-once, or both paths racing the same row) | suppressed via Redis `APPLIED_KEY` | suppressed via the atomic Postgres claim (stronger: survives even if Redis's own idempotency set is also lost) |
| Database transaction rollback (outbox+MRecord insert) | n/a (no outbox existed) | no economic consequence anywhere — verified analytically, not by forcing a live rollback (§9) |
| Machine/VM restart | untested (unchanged from `FINAL_HARDENING_AUDIT.md` §5) | untested, same |

## 7. Idempotency argument

**At-least-once delivery, idempotent settlement — not exactly-once.** The claim stated
precisely: an event may be *attempted* more than once (by Redis's own retry/duplicate
fault injection, by the reconcile fallback racing the Redis path, or by both after a
crash), but it is *applied* at most once, because every attempt — regardless of path —
must pass through the same single-row, single-column conditional `UPDATE` guarded by
`WHERE status = 'pending'`, which PostgreSQL evaluates and applies atomically per row.
This is not claimed to be exactly-once delivery (delivery can and does happen more than
once); it is exactly-once *application*, enforced by the database, not by any
coordination between the two consumer paths.

## 8. Tests performed (raw evidence for each)

| test | description | result | evidence |
|---|---|---|---|
| A | Normal delayed settlement, full concurrency/delay matrix, after the fix | identical to pre-fix pattern (noisy at D=0, consistent 4-over-served at D≥10ms) | `results/two_machine/C1_concurrent_20261007T211320Z.summary.json` |
| B | Worker SIGKILL before event is due | recovered on restart, single correct debit | worker log: `applied=1` after restart, balance `999.8975` matches exactly one debit of `0.1025` |
| C | (same run as B) — claim/debit atomicity | no intermediate state possible by construction; not independently forced | see §4/§5 design argument |
| D | Redis SIGKILL/restart, event queued but not yet due | **event recovered and correctly applied** by `reconcile_outbox`, not lost | balance `1000.000000` → `999.907000` (exact cost), outbox row `status=applied`, `applied_at` populated |
| E | Duplicate event delivery (`--fault duplicate_event`) | correctly suppressed, zero double-charging | `duplicates_suppressed=6` (exactly 2 served × 3 reps), `final_balance=0.000000` every rep |
| F | Database transaction rollback | not forced live; verified analytically from code structure | §4/§9 discussion |
| G | Worker restart/recovery | clean, correct, no duplicate application | same run as B |
| H | Final ledger conservation | held in every test above | `initial - final = applied debits` in every balance check |
| I | Final balance correctness | held in every test above | exact match to expected cost in every case |
| J | No duplicate debit | held in every test above (worker-restart test, duplicate-fault test) | counters and balances both confirm |
| — | Atomic defense (C3) unaffected | unaffected, as designed (does not use the outbox at all) | `results/two_machine/C3_concurrent_20261007T211848Z.summary.json`, identical to pre-fix |

A benign, already-anticipated startup race was observed and is noted, not hidden: the
worker's first few poll passes after a fresh container start can hit
`relation "outbox_events" does not exist` if the worker polls before the gateway's own
`create_all()` has run (the exact same class of race already documented in
`RESEARCH_LOG.md` for the pre-existing `MRecord` table). Confirmed transient, not ongoing:
the error count (`errors=36`) was static across 1800 subsequent poll passes with no new
errors, and cleared entirely on worker restart once the schema existed.

## 9. Tests NOT performed

- Live, forced database-transaction rollback (test F is analytical only).
- Full Azure VM restart (unchanged limitation from `FINAL_HARDENING_AUDIT.md`).
- The real two-machine (Azure) topology specifically — all tests in this audit were run
  locally, which is sufficient to validate the mechanism (the fix is purely a Postgres/
  application-logic change, not topology-dependent), but the real-topology deployment has
  not yet had this fix deployed/re-verified there.
- Load/stress testing of `reconcile_outbox`'s table scan at a scale larger than this
  testbed's modest row counts.

## 10. Remaining limitations

- `reconcile_outbox` scans up to 1000 pending rows per pass with no indexing strategy
  beyond the existing `status`/`account_id` indexes — adequate for this testbed, not
  evaluated for production-scale queue depths.
- No dead-letter handling for an outbox row that somehow never gets claimed (not observed
  in any test; would require a much longer-running test to rule out entirely).
- The fix is local-topology-validated only; real-Azure-topology re-verification is a
  natural next step but was not performed this pass (see §9).

## Architecture classification

The user's question, answered directly: given the pre-fix Redis-SIGKILL result, how
should the architecture be described?

**Before this fix:** **process-crash vulnerable**, specifically to a Redis crash — not
"durable," not even "eventually durable," because the discovered failure mode was
*permanent*, not merely delayed.

**After this fix:** **eventually durable, at-least-once delivery with idempotent
settlement.** Not "durable" in the strict sense of every intermediate step being
individually crash-safe regardless of timing (machine/VM-level restart durability remains
untested, §9), and explicitly not "exactly-once" (§7). "Cancellation-resistant" is a
narrower, different property (already used correctly elsewhere in the manuscript for M1's
`asyncio.shield`-based mechanism, per `FINAL_HARDENING_AUDIT.md` §5) and is not the right
label here, since the property demonstrated is recovery from a *crash of the queue itself*,
not merely a cancelled asyncio task within an otherwise-live process.

## Manuscript impact

No manuscript text was changed. No already-published or already-collected experiment's
semantics were altered (§4, confirmed by grepping all raw data for `lost_event` against
B0 and finding none, and by rerunning the existing matrix post-fix with identical
results). This document and its evidence are available for integration whenever the
two-machine/formalization work itself is integrated — not before, per instruction.
