# Journal-upgrade baseline (frozen checkpoint)

Everything below describes the repository **as it stands before any journal-upgrade work
begins**. It exists so that every later claim can be diffed against a known-good state,
and so that a reviewer can tell which results predate the upgrade and which were produced
by it.

---

## 1. Commit

| field | value |
|---|---|
| Freeze commit | `a66ade9` — *CORRECTIVE AUDIT FIXES: withdraw detectability, split concurrency claim, restate backend parity to 8 genuine cases, spec-derived independent M2 model, K0/K1/K2 attacker-knowledge disclosure, independently re-measured real-model timing* |
| Parent | `0901c02` — *INDEPENDENT AUDIT: recomputation + findings (no fixes applied)* |
| Tree state at freeze | clean (all corrective fixes committed) |
| Branch | `master` |

Preceding milestones (for provenance):

```
0901c02  INDEPENDENT AUDIT: recomputation + findings (no fixes applied)
f533d69  PHASES 9-10: gates re-verified on control with new code
6fadf26  PHASES 5-8: generality in stats/claims/paper; journal reviewer attack
ad87ebe  PHASES 1-4: cross-topology + cross-backend generality
c6ba833  PAPER HARDENING
56e2905  FINAL HARDENING: clean reproduction PASS (56.3 min)
c1e6553  PHASE G: independent M2 checker + cross-validation
27065df  PHASE B/C/D/E/F/H/I/M/N: real-model experiment, ablation, state model
5a0e4f8  (tag: phase-a-checkpoint) PHASE A: baseline verified
```

## 2. Paper

| field | value |
|---|---|
| Source | `paper/main.tex`, 718 lines |
| Output | `paper/main.pdf`, ~529 KiB |
| Compiler | tectonic 0.17.0 (no host LaTeX) |
| Build state | 0 overfull boxes, 0 undefined references, 0 multiply-defined labels |
| Structure | 11 sections; detectability subsection present **only** as an explicit withdrawal |

## 3. Key results at freeze

### B0 — state synchronization (known baseline, not a contribution)

| quantity | value |
|---|---|
| Leakage vs concurrency | slope **0.099 / additional concurrent request**, R² = **1.0000**, p = 1.9e-50 |
| Concurrency = 1 | zero leak (control) |
| Hardened atomic CAS | **$0** leak at every tested concurrency |
| Trials | 420 |

### M1 — commitment timing

| quantity | value |
|---|---|
| Leak vs abort position | rises monotonically, collapses to 0 at completion |
| Per-request leak | 0.0528 at c = 1, 5, 20, 50, 100 (identical to 4 dp) — **empirical** invariance |
| Request-ASR | 1.000 (vulnerable) / 0.000 (safe) at every level |
| Honest-client control | zero leak everywhere |
| Ablation | abort-safe finalization closes accounting integrity; reservation independently provides solvency; **neither substitutes for the other** |
| Records | 2,400 |

### M2 — usage authority

| quantity | value |
|---|---|
| `client_logged` (correct recount, not the billing basis) | leakage efficiency **0.583** (prompt A) / **0.595** (prompt B) |
| `client_total` + total/subtotal mismatch, flat-total pricing | **0.741** |
| Server-authoritative (`server_recount`, `hybrid_reconcile`, `upstream`) | **0.000** across all manipulations |
| Concurrency independence | **analytic** (billed cost computed before any balance read), empirically confirmed |
| Records | 4,800 |

### Generality

| quantity | value |
|---|---|
| Topologies | single / nginx over 4 workers / LB over 2 gateways — **96 cells, 0 mismatches** |
| Backends | 17 cells compared; **8 GENUINE**, 5 ANALYTIC, 4 VACUOUS; all agreed, none disagreed |

### Cost

| quantity | value |
|---|---|
| Standalone tokenizers | 2.9–3.6× spread across engines; grows with input length |
| Gateway + mock generator | ≥0.96× throughput at ≤1,024 tokens; 0.05–0.76× at 16,384 |
| Local real model (SmolLM2-135M, CPU, greedy) | recount **well under 0.1%** of end-to-end (0.014–0.019% at 64 new tokens; 0.017–0.028% on independent re-measurement at 32) |

## 4. Known limitations at freeze

1. **No machine-checked formal verification.** Sufficiency conditions are stated over the
   accounting model and argued by hand in `paper/defense_sufficiency.md`. Nothing is
   model-checked. *(This is the single largest journal-level gap.)*
2. **Both accounting backends are strongly consistent.** No asynchronous or
   eventually-consistent accounting path exists, so the paper cannot say what happens
   when execution and accounting are decoupled in time.
3. **B0 storage independence untested.** The frozen B0 debit module contains no reference
   to the backend abstraction, so the 4 B0 backend cells ran identical code twice.
4. **Economic analysis is sensitivity-only.** Leakage efficiency is price-invariant under
   uniform scaling and changes under structural repricing, but there is no explicit
   exposure model.
5. **M2 pricing-function result is enumerated, not explained.** Which transformation pays
   off under which pricing basis is measured per cell; the underlying characterization is
   not stated as theory.
6. **Mock generator everywhere except one local real-model experiment.** No commercial
   provider, no production serving stack.
7. **Single-host testbed**; loopback adds a ~45 ms floor per request on this
   Windows/Docker Desktop configuration.
8. **Detectability withdrawn** — the artifact retains no defensible claim in that
   dimension, by choice rather than by omission.
9. **Attacker knowledge idealized in the harness** (transformations applied server-side
   from true usage); mitigated by the K0/K1/K2 grading, but the harness itself still
   grants oracle access.

## 5. Claim matrix status

| field | value |
|---|---|
| File | `paper/claim_evidence_matrix.{csv,md}`, generated by `experiments/build_claim_matrix.py` |
| Total claims | **33** |
| DIRECTLY MEASURED | 24 |
| INFERRED | 4 |
| LITERATURE-SUPPORTED | 2 |
| ANALYTICALLY DERIVED | 1 (C10, M2 concurrency independence) |
| HYPOTHESIS | 1 (explicit scope statement) |
| WITHDRAWN | 1 (C24, detectability) |
| **UNSUPPORTED** | **0** |
| MODEL-CHECKED | **0** — the class does not exist yet |

## 6. Audit verdict at freeze

From `AUDIT_REPORT.md`, after the corrective phase:

> **VERIFIED — MATERIAL LIMITATIONS NOW STATED IN THE PAPER**

Six findings (F1–F6) were raised by the adversarial audit and all six are closed: one by
**withdrawal** (detectability), two by **scope restatement** (concurrency split, backend
parity), one by **re-implementation** (spec-derived M2 model), one by **disclosure**
(K0/K1/K2), one by **re-measurement** (real-model timing).

Independent verification standing at freeze — all by code that imports nothing from the
project:

| check | result |
|---|---|
| `audit/recompute_all.py` | **0 discrepancies** (4,800 M2 + 2,400 M1 + 420 B0) |
| `audit/m2_independent_check.py` | **0 mismatches** (truth derived from specification) |
| `experiments/detectability.py` | 2,200 stored labels contradicted; D0 category empty |
| `experiments/run_cross_validation.py` | M2 42 / M1 16 / B0 2 cells — all implementations agree |
| `experiments/regression_m.py` | 16/16 |
| `experiments/metamorphic_checks.py` | 22/22 |
| Summarizer integrity gates | PASS, 0 problems |

## 7. What this checkpoint forbids

The journal upgrade may **not**:

* add attack classes,
* reintroduce detectability in any form,
* restore any withdrawn claim,
* claim new primitives,
* modify raw historical results in `results/raw/`.

Anything the upgrade adds must be additive and independently verifiable against this
baseline. If a later result contradicts a number recorded here, the contradiction is the
finding and must be reported as such.
