# Formal model — `TokenAccounting.tla`

A TLA+ specification of the request lifecycle studied in the paper, checked exhaustively
with TLC. It is not decoration for the prose: every safe architecture claim in the paper
that is labelled **MODEL-CHECKED** was checked here, and every unsafe architecture has a
machine-generated counterexample trace that matches the corresponding empirical failure.

## What is modelled

One state machine covers all three dimensions. The safe and unsafe architectures are the
*same* specification under different constants — mirroring the testbed, where they are the
same interface with different implementations behind it.

| constant | dimension | meaning |
|---|---|---|
| `AtomicDebit` | B0 | atomic conditional decrement vs. read / check / blind absolute write |
| `Reserves` | M1 | does the architecture hold funds before serving? |
| `AbortSafe` | M1 | does *every* terminal path reach accounting finalization? |
| `ServerAuthority` | M2 | is the billing basis server-computed usage or client-declared usage? |
| `ClientMayAbort` | *workload* | whether the client disconnects mid-stream (not an architecture property) |

Lifecycle states: `CREATED`, `AUTHORIZED`, `RESERVED`, `EXECUTING`, `STREAMING`,
`ABORTED`, `COMPLETED`, `ACCOUNTED`, `RECONCILED`, `REFUNDED`, `REJECTED`, `DONE`.

## Invariants

Each is the formal counterpart of a check the summarizers already apply to every
experimental record.

| invariant | statement | empirical counterpart |
|---|---|---|
| `AccountingIntegrity` | for every terminal request, `delivered ≤ debit − refund` | gate G1: per-record leak recomputation |
| `Solvency` | `balance ≥ 0` | the balance-goes-negative probe in the M1 ablation |
| `LedgerConservation` | once all requests are terminal, `InitialBalance − balance = Σ Net` | gate G3: ledger conservation |
| `RefundBounded` | `refund ≤ max(0, reserved − delivered)` | the legitimate-refund condition `F(r) ≤ Res(r) − V(r)` |

Solvency is deliberately **separate** from accounting integrity. The ablation exists to
show they are different properties, so collapsing them in the model would destroy the
result it is meant to check.

## Running it

No system Java is required — `jdk4py` ships a JDK as a Python wheel.

```bash
pip install jdk4py
curl -sSL -o formal/tools/tla2tools.jar \
  https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar
python formal/check.py            # all configurations
python formal/check.py m1_        # only M1 configurations
```

`check.py` runs **each invariant in a separate TLC run**, because TLC stops at the first
invariant it finds violated — checking them together would hide that, for example, an M2
architecture breaks both accounting integrity *and* the refund bound. The output is a full
configuration × invariant matrix written to `results/formal/model_check_results.json`.

The `.cfg` files in `cfg/` are the canonical, reviewer-runnable configurations (all
invariants at once, suitable for the TLA+ Toolbox). `check.py` derives its per-invariant
configurations from them at run time.

## Result

40 checks (10 configurations × 4 invariants), **28,363 distinct states**, ~36 s total.
**All 40 matched the expectation declared in `check.py` before the run; 0 disagreements.**

| configuration | Accounting&nbsp;Integrity | Solvency | Ledger&nbsp;Conservation | Refund&nbsp;Bounded |
|---|---|---|---|---|
| `b0_vulnerable` | holds | holds | **VIOLATED** | holds |
| `b0_hardened` | holds | holds | holds | holds |
| `m1_post_completion` | **VIOLATED** | holds | holds | holds |
| `m1_reserve_refund_on_abort` | **VIOLATED** | holds | holds | **VIOLATED** |
| `m1_no_reserve_settle` | holds | **VIOLATED** | holds | holds |
| `m1_reserve_reconcile` | holds | holds | holds | holds |
| `m2_client` | **VIOLATED** | holds | holds | **VIOLATED** |
| `m2_server_recount` | holds | holds | holds | holds |
| `all_defenses` | holds | holds | holds | holds |
| `all_defenses_3req` | holds | holds | holds | holds |

Two rows deserve comment because they are the paper's central architectural claims:

* **`m1_no_reserve_settle`** — abort-safe finalization *without* a reservation keeps
  accounting integrity but breaks solvency. **`m1_reserve_refund_on_abort`** — a
  reservation *without* abort-safe finalization keeps solvency but breaks integrity.
  Neither primitive substitutes for the other, and TLC says so exhaustively rather than
  by example.
* **`m2_client`** violates `AccountingIntegrity` even though the architecture computes a
  correct server-side recount: in this configuration the recount exists but is not the
  billing basis. Computation is not authority.

## The expectation discipline

`check.py` declares the expected outcome of every cell **before** running, and exits
non-zero if TLC disagrees. This is what stops a formal model from being quietly tuned
until it agrees with the paper.

It has already paid for itself. The first version of this specification treated a
reservation as a *hold* and set `debit = charge` at settlement, which made
`Net = debit − refund` come out below the delivered value and caused TLC to reject the
**safe** configurations. The model was wrong, not the paper: in a reserve-and-reconcile
architecture the reservation *is* the committed debit and the refund returns its unused
part. The settlement semantics were corrected (`committed == IF reserved > 0 THEN reserved
ELSE charge`) and the safe configurations then verified. That failure is recorded here
rather than erased.

## What this does and does not establish

**Does:** within this model — bounded request counts, unit pricing, a single shared
balance, and the modelled transformation family — the stated defense conditions are
*sufficient* for the four invariants, and the unsafe architectures are *unsafe on every
run*, not merely on the schedules our harness happened to produce.

**Does not:** prove any production implementation safe. The model abstracts away the
database, the network, partial failure, asynchronous reconciliation, and real pricing
functions. See `paper/scope_of_formal_claims.md` for the explicit exclusion list, and
`paper/formal_empirical_mapping.md` for how each counterexample lines up with a measured
result.
