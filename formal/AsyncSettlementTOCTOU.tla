----------------------- MODULE AsyncSettlementTOCTOU -----------------------
(***************************************************************************)
(* Faithful model of the ACTUAL asynchronous-settlement B0 mechanism       *)
(* (`app/async_routes.py::async_b0_complete` +                             *)
(* `app/accounting/async_worker.py::drain`), built from the T1-T7          *)
(* instrumentation added in the experimental-strengthening phase, not      *)
(* chosen for ease of verification. See FORMALIZATION_AUDIT.md for the     *)
(* implementation-to-state-machine mapping this model is derived from.     *)
(*                                                                         *)
(* This is a SEPARATE specification from TokenAccounting.tla, which models *)
(* the historical, SYNCHRONOUS blind-overwrite B0 race (the Class 6        *)
(* baseline). The two races are mechanistically different and are kept     *)
(* apart deliberately -- see FORMALIZATION_AUDIT.md Step 8 for exactly     *)
(* what TokenAccounting.tla does and does not cover.                       *)
(*                                                                         *)
(* Key structural fact, verified against the implementation, not assumed:  *)
(* ADMISSION (the authorization read) never writes `balance`. The read is  *)
(* a plain SELECT (`app/accounting/backends.py::read_balance`, a           *)
(* read-only query -- confirmed by reading it directly). Only SETTLEMENT   *)
(* (the worker's `debit_unchecked`) writes `balance`, via a single,        *)
(* atomic, RELATIVE decrement:                                             *)
(*   `UPDATE credits SET balance = balance - :c WHERE account_id = :a`     *)
(* (`app/accounting/backends.py::_mutable_debit`, confirmed by reading it   *)
(* directly). Nothing is ever lost or overwritten -- every admitted        *)
(* request's debit eventually lands, exactly once, additively. The         *)
(* vulnerability is therefore NOT a lost update: it is N concurrent        *)
(* admissions reading the SAME not-yet-decremented balance before ANY of   *)
(* their own settlements land -- a time-of-check-to-time-of-use (TOCTOU)   *)
(* admission race on a shared counter under delayed settlement, not a      *)
(* blind-overwrite lost-update race.                                       *)
(***************************************************************************)
EXTENDS Integers, FiniteSets, TLC

CONSTANTS
    Requests,       \* the set of concurrently-admitted requests, e.g. {r1,...,r6}
    Value,          \* uniform per-request cost v (Assumption A1 -- see
                     \* FORMALIZATION_AUDIT.md Step 3 for why this is required)
    InitialBalance, \* initial funded balance B (Assumption A2: fixed at start,
                     \* no concurrent credits/refunds)
    AtomicCommit    \* FALSE = vulnerable path (C2); TRUE = atomic defense (C3)

States == { "CREATED", "ADMITTED", "REJECTED",
            "RELEASED", "SETTLEMENT_PENDING", "SETTLED" }

VARIABLES pc, balance, debited

vars == << pc, balance, debited >>

TypeOK ==
    /\ pc \in [Requests -> States]
    /\ balance \in Int
    /\ debited \in [Requests -> {0, Value}]

Init ==
    /\ pc = [r \in Requests |-> "CREATED"]
    /\ balance = InitialBalance
    /\ debited = [r \in Requests |-> 0]

(***************************************************************************)
(* VULNERABLE PATH (AtomicCommit = FALSE).                                 *)
(*                                                                         *)
(* `Authorize` collapses T1 (read start) / T2 (read done) / T3 (decision)  *)
(* into one TLA+ step: nothing observable to any OTHER request happens     *)
(* between them (they are three `perf_counter_ns()` samples around a       *)
(* single `SELECT`, not three separate writes), so the state machine does  *)
(* not need three separate actions to be faithful -- what matters is that  *)
(* this step does not touch `balance`, which it does not, matching the     *)
(* implementation exactly.                                                 *)
(***************************************************************************)
Authorize(r) ==
    /\ ~AtomicCommit
    /\ pc[r] = "CREATED"
    /\ IF balance >= Value
       THEN pc' = [pc EXCEPT ![r] = "ADMITTED"]
       ELSE pc' = [pc EXCEPT ![r] = "REJECTED"]
    /\ UNCHANGED << balance, debited >>

(* `Release` collapses T4 (event created) / T4b (emitted to Redis) / T5    *)
(* (HTTP response returned). `aw.new_event()`, `_emit()`, and the MRecord  *)
(* write in `async_b0_complete` all precede any debit and none of them     *)
(* touch `balance` -- confirmed directly by reading the function, which    *)
(* never calls `ledger.debit_unchecked`/`credit` in this code path.        *)
Release(r) ==
    /\ ~AtomicCommit
    /\ pc[r] = "ADMITTED"
    /\ pc' = [pc EXCEPT ![r] = "RELEASED"]
    /\ UNCHANGED << balance, debited >>

(* The event sits in Redis with `deliver_after_ns` in the future. Modelled *)
(* as a distinct state, not a numeric delay in milliseconds -- TLC         *)
(* explores every possible INTERLEAVING of `SettlementPending`/`Settle`    *)
(* against other requests' `Authorize`/`Release`, which is the            *)
(* worst-case-REACHABILITY question this model answers. It does NOT model *)
(* the measured ~2ms real-time threshold from the delay-sweep experiment   *)
(* -- see FORMALIZATION_AUDIT.md Step 9 for why that would need a timed or *)
(* probabilistic model, out of scope here.                                 *)
SettlementPending(r) ==
    /\ ~AtomicCommit
    /\ pc[r] = "RELEASED"
    /\ pc' = [pc EXCEPT ![r] = "SETTLEMENT_PENDING"]
    /\ UNCHANGED << balance, debited >>

(* `Settle` collapses T6 (popped off the queue, due-check passed) / T7     *)
(* (debit durably applied) into one atomic TLA+ step, matching the fact    *)
(* that `debit_unchecked`'s single `UPDATE ... RETURNING balance` plus the *)
(* immediately-following `session.commit()` is one atomic database         *)
(* transaction from every other transaction's point of view (PostgreSQL    *)
(* serializes concurrent writers to the same row). RELATIVE decrement:     *)
(* `balance' = balance - Value`, never an absolute overwrite -- this can   *)
(* drive `balance` negative, which is exactly what "unchecked" means in    *)
(* the implementation's own naming (`debit_unchecked`).                    *)
Settle(r) ==
    /\ ~AtomicCommit
    /\ pc[r] = "SETTLEMENT_PENDING"
    /\ balance' = balance - Value
    /\ debited' = [debited EXCEPT ![r] = Value]
    /\ pc' = [pc EXCEPT ![r] = "SETTLED"]

(***************************************************************************)
(* ATOMIC DEFENSE PATH (AtomicCommit = TRUE) -- mirrors                    *)
(* `async_b0_complete_atomic`'s `ledger.reserve_atomic()`, which for the    *)
(* mutable backend is exactly:                                             *)
(*   `UPDATE credits SET balance = balance - :c WHERE balance >= :c        *)
(*    RETURNING balance`                                                   *)
(* (`app/accounting/backends.py::_mutable_reserve`, confirmed by reading    *)
(* it directly). Check-and-decrement is ONE atomic SQL statement, so it is *)
(* modelled as ONE atomic TLA+ step -- no request can observe, or be       *)
(* observed in, a state where the check has passed but the decrement has   *)
(* not happened yet, because no such state exists in the implementation.   *)
(***************************************************************************)
AtomicAdmit(r) ==
    /\ AtomicCommit
    /\ pc[r] = "CREATED"
    /\ balance >= Value
    /\ balance' = balance - Value
    /\ debited' = [debited EXCEPT ![r] = Value]
    /\ pc' = [pc EXCEPT ![r] = "SETTLED"]

AtomicReject(r) ==
    /\ AtomicCommit
    /\ pc[r] = "CREATED"
    /\ balance < Value
    /\ pc' = [pc EXCEPT ![r] = "REJECTED"]
    /\ UNCHANGED << balance, debited >>

Next ==
    \E r \in Requests :
        \/ Authorize(r) \/ Release(r) \/ SettlementPending(r) \/ Settle(r)
        \/ AtomicAdmit(r) \/ AtomicReject(r)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

Terminal(r) == pc[r] \in { "SETTLED", "REJECTED" }
AllDone == \A r \in Requests : Terminal(r)

ServedCount == Cardinality({ r \in Requests : pc[r] = "SETTLED" })

(***************************************************************************)
(* INVARIANTS -- named identically to TokenAccounting.tla's, so that       *)
(* "which invariant actually fails, here vs. there" is a direct, not       *)
(* relabeled, comparison (see FORMALIZATION_AUDIT.md Step 8).              *)
(***************************************************************************)

(* Solvency is the invariant this mechanism actually violates: N concurrent*)
(* admissions can all pass the `balance >= Value` check before any of     *)
(* their settlements land, driving `balance` negative once they all       *)
(* eventually settle. *)
Solvency == balance >= 0

(* Per-request accounting integrity: every SETTLED request was debited     *)
(* exactly Value for exactly Value of service -- genuinely checked (not a  *)
(* bare TRUE), and it HOLDS even in the vulnerable configuration, because  *)
(* `Settle` always decrements by exactly `Value`, exactly once, for every  *)
(* settled request: nothing is ever double-charged or under-charged at the*)
(* level of a single request. This is the precise sense in which the      *)
(* vulnerability is a GLOBAL (Solvency) failure, not a PER-REQUEST         *)
(* (AccountingIntegrity) one. *)
AccountingIntegrity == \A r \in Requests : (pc[r] = "SETTLED") => (debited[r] = Value)

(* Ledger conservation: total debited equals initial-minus-final, by       *)
(* construction of `Settle`/`AtomicAdmit` as a pure relative decrement      *)
(* applied exactly once per settled request -- this ALSO holds even in the *)
(* vulnerable configuration (nothing is ever lost or double-counted at the *)
(* ledger level; the ledger entries are internally consistent even while   *)
(* the account goes insolvent). This is the precise sense in which this    *)
(* mechanism's bug is NOT the historical TokenAccounting.tla model's        *)
(* blind-overwrite lost-update bug (which violates exactly this invariant, *)
(* while keeping Solvency and AccountingIntegrity intact -- the mirror      *)
(* image of this model's violation profile). *)
LedgerConservation ==
    AllDone => (InitialBalance - balance = ServedCount * Value)

AllSafe == /\ AccountingIntegrity
           /\ Solvency
           /\ LedgerConservation

=============================================================================
