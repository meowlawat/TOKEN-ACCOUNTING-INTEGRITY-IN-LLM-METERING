-------------------------- MODULE TokenAccounting --------------------------
(***************************************************************************)
(* Token-accounting integrity: a request-lifecycle model of LLM metering.  *)
(*                                                                         *)
(* One specification covers all three studied dimensions.  Each dimension  *)
(* is a BOOLEAN ARCHITECTURE FLAG, so the safe and unsafe architectures    *)
(* are the SAME state machine under different constants -- exactly as the  *)
(* testbed implements them behind one interface.                           *)
(*                                                                         *)
(*   AtomicDebit      B0  synchronization: atomic conditional decrement    *)
(*                        vs. read / check / blind absolute write          *)
(*   Reserves         M1  does the architecture hold funds before serving? *)
(*   AbortSafe        M1  does every terminal path reach finalization?     *)
(*   ServerAuthority  M2  is the billing basis server-computed usage, or   *)
(*                        the client-declared usage?                       *)
(*                                                                         *)
(* `ClientMayAbort` is not an architecture property but a WORKLOAD switch.  *)
(* Disabling it in the B0 configurations keeps the synchronization          *)
(* counterexample free of commitment-timing noise, so each mechanism's      *)
(* trace isolates its own defect -- the same separation the experiments     *)
(* enforce by holding the other two dimensions at their safe setting.       *)
(*                                                                         *)
(* Reservation and abort-safe finalization are deliberately INDEPENDENT    *)
(* flags: the empirical ablation found they are orthogonal controls, and   *)
(* the model must be able to express all four combinations to check that.  *)
(***************************************************************************)
EXTENDS Integers, FiniteSets, TLC

CONSTANTS
    Requests,
    Chunks,
    DeclaredUsage,
    InitialBalance,
    AtomicDebit,
    Reserves,
    AbortSafe,
    ServerAuthority,
    ClientMayAbort

ASSUME DeclaredUsage \in 0..Chunks

Cost(units) == units

States == { "CREATED", "AUTHORIZED", "RESERVED", "EXECUTING", "STREAMING",
            "ABORTED", "COMPLETED", "ACCOUNTED", "RECONCILED", "REFUNDED",
            "REJECTED", "DONE" }

VARIABLES pc, snapshot, delivered, reserved, debit, refund, balance

vars == << pc, snapshot, delivered, reserved, debit, refund, balance >>

Net(r) == debit[r] - refund[r]

Terminal(r) == pc[r] \in { "DONE", "REJECTED" }

AllDone == \A r \in Requests : Terminal(r)

SumNet == LET f[S \in SUBSET Requests] ==
              IF S = {} THEN 0
              ELSE LET x == CHOOSE y \in S : TRUE
                   IN Net(x) + f[S \ {x}]
          IN f[Requests]

TypeOK ==
    /\ pc        \in [Requests -> States]
    /\ delivered \in [Requests -> 0..Chunks]
    /\ reserved  \in [Requests -> 0..Chunks]
    /\ debit     \in [Requests -> 0..Chunks]
    /\ refund    \in [Requests -> 0..Chunks]

Init ==
    /\ pc        = [r \in Requests |-> "CREATED"]
    /\ snapshot  = [r \in Requests |-> 0]
    /\ delivered = [r \in Requests |-> 0]
    /\ reserved  = [r \in Requests |-> 0]
    /\ debit     = [r \in Requests |-> 0]
    /\ refund    = [r \in Requests |-> 0]
    /\ balance   = InitialBalance

(***************************************************************************)
(* B0 -- state synchronization.                                            *)
(*                                                                         *)
(* Non-atomic path: a request READS the balance (AuthorizeRead) and only   *)
(* later WRITES an absolute value derived from that stale read             *)
(* (ReserveWrite).  Two requests interleaving read/read/write/write lose   *)
(* one decrement.  This is a blind absolute write, not a decrement, which  *)
(* is why row locking under READ COMMITTED does not prevent it.            *)
(***************************************************************************)

AuthorizeRead(r) ==
    /\ ~AtomicDebit
    /\ pc[r] = "CREATED"
    /\ pc' = [pc EXCEPT ![r] = "AUTHORIZED"]
    /\ snapshot' = [snapshot EXCEPT ![r] = balance]
    /\ UNCHANGED << delivered, reserved, debit, refund, balance >>

ReserveWrite(r) ==
    /\ ~AtomicDebit
    /\ pc[r] = "AUTHORIZED"
    /\ snapshot[r] >= Cost(Chunks)
    /\ pc' = [pc EXCEPT ![r] = IF Reserves THEN "RESERVED" ELSE "EXECUTING"]
    /\ reserved' = [reserved EXCEPT ![r] = IF Reserves THEN Cost(Chunks) ELSE 0]
    /\ balance' = IF Reserves THEN snapshot[r] - Cost(Chunks) ELSE balance
    /\ UNCHANGED << snapshot, delivered, debit, refund >>

RejectStale(r) ==
    /\ ~AtomicDebit
    /\ pc[r] = "AUTHORIZED"
    /\ snapshot[r] < Cost(Chunks)
    /\ pc' = [pc EXCEPT ![r] = "REJECTED"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

AtomicReserve(r) ==
    /\ AtomicDebit
    /\ pc[r] = "CREATED"
    /\ balance >= Cost(Chunks)
    /\ pc' = [pc EXCEPT ![r] = IF Reserves THEN "RESERVED" ELSE "EXECUTING"]
    /\ reserved' = [reserved EXCEPT ![r] = IF Reserves THEN Cost(Chunks) ELSE 0]
    /\ balance' = IF Reserves THEN balance - Cost(Chunks) ELSE balance
    /\ UNCHANGED << snapshot, delivered, debit, refund >>

AtomicReject(r) ==
    /\ AtomicDebit
    /\ pc[r] = "CREATED"
    /\ balance < Cost(Chunks)
    /\ pc' = [pc EXCEPT ![r] = "REJECTED"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

(***************************************************************************)
(* M1 -- commitment timing.                                                *)
(***************************************************************************)

Begin(r) ==
    /\ pc[r] = "RESERVED"
    /\ pc' = [pc EXCEPT ![r] = "EXECUTING"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

StartStream(r) ==
    /\ pc[r] = "EXECUTING"
    /\ pc' = [pc EXCEPT ![r] = "STREAMING"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

Deliver(r) ==
    /\ pc[r] = "STREAMING"
    /\ delivered[r] < Chunks
    /\ delivered' = [delivered EXCEPT ![r] = delivered[r] + 1]
    /\ UNCHANGED << pc, snapshot, reserved, debit, refund, balance >>

Abort(r) ==
    /\ ClientMayAbort
    /\ pc[r] = "STREAMING"
    /\ pc' = [pc EXCEPT ![r] = "ABORTED"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

Complete(r) ==
    /\ pc[r] = "STREAMING"
    /\ delivered[r] = Chunks
    /\ pc' = [pc EXCEPT ![r] = "COMPLETED"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

(***************************************************************************)
(* M2 -- usage authority.  The billing basis is a pure function of one     *)
(* request's own fields, with no reference to `balance` -- which is why M2 *)
(* leakage cannot depend on concurrency or on the storage backend.         *)
(***************************************************************************)

BilledUsage(actual) ==
    IF ServerAuthority THEN actual
    ELSE IF DeclaredUsage < actual THEN DeclaredUsage ELSE actual

AccountComplete(r) ==
    /\ pc[r] = "COMPLETED"
    /\ LET charge == Cost(BilledUsage(delivered[r]))
           \* The committed debit is the reservation where one exists (the hold is
           \* converted into a charge); the refund returns its unconsumed part.  So
           \* Net(r) = D(r) - F(r) = charge either way, which is what the accounting
           \* model in the paper defines.
           committed == IF reserved[r] > 0 THEN reserved[r] ELSE charge
           back      == IF committed > charge THEN committed - charge ELSE 0
       IN /\ debit'  = [debit  EXCEPT ![r] = committed]
          /\ refund' = [refund EXCEPT ![r] = back]
          /\ balance' = balance + reserved[r] - charge
    /\ pc' = [pc EXCEPT ![r] = "ACCOUNTED"]
    /\ UNCHANGED << snapshot, delivered, reserved >>

AccountAbort(r) ==
    /\ AbortSafe
    /\ pc[r] = "ABORTED"
    /\ LET charge == Cost(BilledUsage(delivered[r]))
           \* The committed debit is the reservation where one exists (the hold is
           \* converted into a charge); the refund returns its unconsumed part.  So
           \* Net(r) = D(r) - F(r) = charge either way, which is what the accounting
           \* model in the paper defines.
           committed == IF reserved[r] > 0 THEN reserved[r] ELSE charge
           back      == IF committed > charge THEN committed - charge ELSE 0
       IN /\ debit'  = [debit  EXCEPT ![r] = committed]
          /\ refund' = [refund EXCEPT ![r] = back]
          /\ balance' = balance + reserved[r] - charge
    /\ pc' = [pc EXCEPT ![r] = "ACCOUNTED"]
    /\ UNCHANGED << snapshot, delivered, reserved >>

AbortBypass(r) ==
    /\ ~AbortSafe
    /\ pc[r] = "ABORTED"
    /\ debit'  = [debit  EXCEPT ![r] = reserved[r]]
    /\ refund' = [refund EXCEPT ![r] = reserved[r]]
    /\ balance' = balance + reserved[r]
    /\ pc' = [pc EXCEPT ![r] = "REFUNDED"]
    /\ UNCHANGED << snapshot, delivered, reserved >>

Reconcile(r) ==
    /\ pc[r] = "ACCOUNTED"
    /\ pc' = [pc EXCEPT ![r] = "RECONCILED"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

Finish(r) ==
    /\ pc[r] \in { "RECONCILED", "REFUNDED" }
    /\ pc' = [pc EXCEPT ![r] = "DONE"]
    /\ UNCHANGED << snapshot, delivered, reserved, debit, refund, balance >>

Next ==
    \E r \in Requests :
        \/ AuthorizeRead(r)   \/ ReserveWrite(r)  \/ RejectStale(r)
        \/ AtomicReserve(r)   \/ AtomicReject(r)
        \/ Begin(r)           \/ StartStream(r)   \/ Deliver(r)
        \/ Abort(r)           \/ Complete(r)
        \/ AccountComplete(r) \/ AccountAbort(r)  \/ AbortBypass(r)
        \/ Reconcile(r)       \/ Finish(r)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

(***************************************************************************)
(* INVARIANTS: the formal counterparts of the three integrity gates the    *)
(* summarizers apply to every experimental record (G1/G2/G3), plus the     *)
(* refund condition from the paper's accounting model.                     *)
(***************************************************************************)

AccountingIntegrity ==
    \A r \in Requests : Terminal(r) => delivered[r] <= Net(r)

Solvency == balance >= 0

LedgerConservation == AllDone => (InitialBalance - balance = SumNet)

RefundBounded ==
    \A r \in Requests :
        refund[r] <= (IF reserved[r] > delivered[r]
                      THEN reserved[r] - delivered[r] ELSE 0)

AllSafe ==
    /\ AccountingIntegrity
    /\ Solvency
    /\ LedgerConservation
    /\ RefundBounded

=============================================================================
