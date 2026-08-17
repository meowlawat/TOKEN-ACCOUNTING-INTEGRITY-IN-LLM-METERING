# Corrective-Fix Baseline

State frozen before corrective work begins. Raw historical results are **not** altered.

| item | value |
|---|---|
| Fix baseline commit | `0901c02` (audit findings, no fixes applied) |
| Paper commit before fixes | `f533d69` |
| Audit commit | `0901c02` |
| Working tree | clean |
| Date | 2026-08-17 |

## Defects being fixed (from `AUDIT_REPORT.md`)

| id | defect | severity | planned action |
|---|---|---|---|
| **F1** | Detectability assigned from configuration (`"D3" if arch.safe else "D0"`), never measured; `client` (D0) retains the same evidence as `client_logged` (D1), so the claimed distinction is false | **contradicted** | Build an evidence-only detector (`experiments/detectability.py`). Let the data decide. If no defensible distinction exists → **withdraw** detectability as a primary metric. |
| **F2** | M2 concurrency-invariance presented as empirical; it is analytic (`billed_cost` is a pure function of the request) | confirmation bias | Split the three-way claim: B0 empirical, M1 empirical, M2 analytic + empirically confirmed. |
| **F3** | "17/17 identical across backends" overstated; B0 never uses the pluggable backend (0 `ledger_entries` rows from a 5-request B0 trial) | partially vacuous | Verify the genuine/analytic/vacuous split from source and raw data; restate to the evidence-supported scope. |
| **F4** | "Independent" M2 checker consumes `extra["true"]`, the gateway's own ground truth | partially dependent | New `audit/m2_independent_model.py` deriving true usage from `(prompt, seed)` spec; rewire the checker. |
| **F5** | M2 attacker has oracle knowledge (server applies the transformation to true usage) | scope overclaim | Add a knowledge-level model (K0/K1/K2); relabel the existing experiment an economic upper bound. |
| **F6** | Real-model timing (0.014–0.019%) never independently re-measured | unverified | Re-measure independently, or downgrade wording to "previously measured in the artifact". |

## Files expected to change

```
experiments/detectability.py            (new, evidence-based detector)
audit/m2_independent_model.py           (new, independent truth derivation)
audit/m2_independent_check.py           (new, rewritten checker)
audit/recompute_all.py                  (extended: genuine-backend subset, no label trust)
audit/confirmation_bias.md              (new)
experiments/build_claim_matrix.py       (new classification: ANALYTICALLY DERIVED)
experiments/summarize_ablation.py       (detectability table removal/rederivation)
app/m_routes.py                         (only if detectability is re-derived, not relabelled)
paper/main.tex                          (abstract, contributions, results, threat model, discussion)
paper/*.md                              (defense_evaluation, results, threats_to_validity, taxonomy)
AUDIT_REPORT.md, FINAL_RESEARCH_REPORT.md, README.md
```

## Rules for this phase

1. Raw historical result files are never edited.
2. No claim is preserved because it strengthens the paper.
3. A configuration label is never counted as measured evidence.
4. An analytic consequence is never presented as an empirical discovery.
5. If detectability cannot be derived from observable evidence, it is removed rather than
   rescued with new self-validating instrumentation.
