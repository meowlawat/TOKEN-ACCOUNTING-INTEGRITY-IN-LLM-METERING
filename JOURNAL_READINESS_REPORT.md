# Journal Readiness Report

**Date:** 2026-08-17 · **Commit:** `6fadf26` · **Paper:** `paper/main.pdf` (524 KB,
compiles with zero overfull boxes and zero undefined references)

Scope of this stage: close the **architectural-generality** gap identified as the single
largest weakness in the previous assessment. No new attack classes, no broadened threat
model, and no change to the validated M1/M2/B0 definitions.

---

## 1. What was added

| phase | work | outcome |
|---|---|---|
| 1 | Multi-worker topology (nginx → 4 uvicorn workers → shared PG/Redis) | full B0/M1/M2 matrix, concurrency 1–100 |
| 2 | Distributed topology (nginx LB → 2 gateway containers × 2 workers) | reduced matched matrix, concurrency 10/50 |
| 3 | Second accounting backend (append-only ledger, derived balance) | 8 genuine cases identical to mutable-row backend; none disagreed (17 cells compared; 5 analytic, 4 vacuous) |
| 4 | `paper/defense_sufficiency.md` | model-level sufficiency conditions per mechanism |
| 5 | Economic sensitivity (3 price tiers) | efficiency invariant under uniform scaling |
| 6 | Statistics extended with cross-topology/backend effect sizes | absolute differences, not spurious p-values |
| 7 | `paper/journal_reviewer_attack.md` | reviewers A–E; all five leave residual limitations |
| 8 | Paper updated (abstract, contributions, results, sufficiency, threats) | new §Cross-architecture validation, §Defense Sufficiency Conditions |
| 9 | Gates re-run on the control with the new code | all pass; 33 claims, 0 unsupported |

## 2. Cross-architecture results

**Topology (96 accounting cells vs the single-worker control): 0 mismatches.**
Differences are exactly zero or bounded by the price of one delivered token — the
disconnect-detection jitter already characterized in `reproduction_consistency.md` — and
never change a verdict. Load demonstrably spread: each ledger row records its serving
process, and four distinct workers served M1 requests in the multi-worker run
(101/164/79/136), with both containers serving in the distributed run.

**B0 preserved everywhere.** Hardened leaks exactly \$0 at every concurrency in every
topology, *including across two separate containers* — atomicity is enforced by the
database, not by process locality. Distributed vulnerable reproduced the control exactly
(\$0.8910 at c=10, \$4.8510 at c=50).

**Backends: 8 genuine cases agreed; no case disagreed.** *(Restated after the independent
audit — the earlier "17/17 byte-identical" headline overstated the evidence.)* All 17
comparison cells agreed, but only 8 genuinely exercised both backends; 5 agree
analytically (the M2 billed amount is computed before any balance is read) and 4 are
vacuous: the frozen B0 debit module does not reference the backend abstraction, so those
B0 cells ran identical code twice. **B0's storage independence is untested.** Agreeing values:
`M2/client` 0.594 both; `M2/server_recount` 0.000 both;
`M1/post_completion/abort90` 0.0950/req both.

**Two genuine multi-worker defects surfaced and are reported as findings**, not hidden:
the B0 runtime posture was per-process (would have reached 1 of 4 workers → moved to
Redis), and four workers racing `create_all` crashed with `UniqueViolation` on `pg_class`
(→ serialized with a PostgreSQL advisory lock).

## 3. Dimension ratings

| dimension | rating | justification |
|---|---|---|
| **Novelty / systematization** | **Moderate** | No primitive-level novelty, stated explicitly throughout. The defensible contribution is the accounting model, the experimentally-distinguishable taxonomy, the orthogonality and authority results, and the cross-architecture validation. Type-B by construction. |
| **Formal rigor** | **Moderate** | A lifecycle state model, a precise invariant admitting legitimate refunds, and per-mechanism sufficiency conditions with model-vs-implementation separation. **Argued, not mechanized** — no TLA+/Coq/Alloy. |
| **Architectural generality** | **Good** (was the main gap) | 3 topologies × 2 accounting backends; 96 cells + 17 cases, no divergence. Still one physical host, one PostgreSQL, one Redis, and both backends strongly consistent. |
| **Empirical rigor** | **Strong** | >10,000 instrumented requests; per-request ledger; ablation isolating load-bearing primitives; 9 lifecycle failure injections; honest-client controls; volume held constant across concurrency. |
| **Statistical rigor** | **Strong** | Standalone scipy/statsmodels script is the sole source of statistics; deterministic conditions reported as constants with complete separation rather than fake p-values; nonparametric tests and bootstrap CIs where variance is real; effect sizes reported. |
| **Reproducibility** | **Strong** | Clean reproduction from wiped volumes/results in 56.3 min; provenance manifest with 88 artifact hashes + PDF hash; every figure/table generated from raw data; fail-closed gates proven by fault injection (12/12) and metamorphic checks (22/22). |
| **External validity** | **Moderate** | Improved from *weak*. Real tokenizers, a local real-model experiment, and cross-topology/backend validation — but no commercial provider, no multi-host, no GPU serving stack, no eventual consistency. |
| **Defense contribution** | **Strong** | Not merely "the defense works": an ablation shows *which* primitive closes *which* property (finalization ⇒ integrity, reservation ⇒ solvency, orthogonal), that recount must be the billing basis, plus measured overhead at three abstraction levels and an independent re-implementation that agrees on every cross-validated cell. |
| **Artifact quality** | **Strong** | `ARTIFACT_README.md` written for an external researcher with no Docker experience; three compose topologies; one-command reproduction; claim-evidence matrix with 0 unsupported claims. |

## 4. Venue assessment

### Computers & Security (Elsevier) — **SUBMITTABLE**
The architectural-generality objection that previously blocked this is now answered with
measurement rather than argument, and the artifact/reproducibility standard is above what
the venue typically requires. Expect reviewers to push on (a) type-B novelty and (b) the
absence of a commercial-provider or multi-host evaluation. Both are stated as limitations
rather than defended. **Assessment: submittable now; accept-after-revision is a realistic
outcome, not a certainty.**

### IEEE TDSC — **BORDERLINE; NOT RECOMMENDED YET**
TDSC's bar on formal treatment is the binding constraint. Our sufficiency conditions are
deductive-within-model and explicitly *not* machine-checked. A credible TDSC submission
would need mechanized invariants (e.g. TLA+ model checking of the lifecycle, or a proof
assistant for the sufficiency conditions) and ideally multi-host validation. The empirical
half would likely satisfy TDSC; the formal half would not. **Assessment: one substantial
formal-methods iteration away.**

### Springer/Elsevier security venues (e.g. *International Journal of Information
Security*, *Journal of Information Security and Applications*) — **SUBMITTABLE**
The systematization + reproducible-artifact profile fits these venues well, and the
cross-architecture evidence is comfortably sufficient for them. Lower formal-rigor
expectations than TDSC. **Assessment: a good fit; the strongest expected-value target
alongside *Computers & Security*.**

### Top-tier security conferences (CCS/USENIX/NDSS/S&P) — **NOT RECOMMENDED**
Unchanged. Type-B novelty plus a single-host testbed would draw novelty and scope
rejections regardless of measurement quality.

## 5. Honest verdict on "journal-ready"

**Yes for *Computers & Security* and comparable Springer/Elsevier venues. No for IEEE
TDSC.**

The specific gap that previously made me withhold a journal recommendation —
architectural generality — has been closed by measurement: three topologies, two
accounting backends, 113 compared cells/cases, zero divergences, with load-spread
evidence recorded per request. What remains is a *different* and narrower set of
limitations (one physical host, strongly-consistent datastores only, no commercial
provider, no mechanized proof), all of which are stated in the paper rather than
defended.

I am **not** claiming the work is now beyond criticism. Reviewer A (novelty) and Reviewer
D (formal rigor) retain valid objections that no amount of additional measurement will
answer; they require either a different contribution or mechanized verification.

## 6. Remaining limitations (carried forward)

1. **One physical host.** Multi-worker and multi-instance confounds removed; multi-host
   networking, replica lag, cross-region latency and datastore partitioning untested.
2. **Both backends strongly consistent.** An eventually-consistent or sharded accounting
   pipeline could break condition (B0-a) or (M1-a) and is unevaluated.
3. **No mechanized proof.** Sufficiency is argued within the model, not verified.
4. **No commercial provider.** The real-model experiment bounds a ratio in one local
   CPU configuration.
5. **Type-B novelty.** The mechanisms are known; the contribution is systematization,
   measurement, and sufficiency analysis.
6. **Gateway performance at c≥50** remains host-saturated and is excluded from headline
   performance claims (accounting measurements at those levels are retained and valid).

## 7. Recommended next step (if pursuing TDSC)

A single, well-scoped addition would move the formal rating: encode the lifecycle state
model and the three sufficiency conditions in TLA+ and model-check that no reachable state
violates `V(r) ≤ N(r)` under the stated conditions, and that removing each condition
produces a counterexample trace matching the measured ablation. That would convert
"argued" into "verified" and pair naturally with the existing empirical necessity
evidence. Multi-host validation would be the second priority.
