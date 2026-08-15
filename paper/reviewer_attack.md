# Self-Critique — Three Adversarial Reviewers

Written *after* the experiments, adopting the posture of reviewers trying to reject the
paper. Each objection is stated at full strength, then the current defense and any fix
applied. Unresolved items are marked ✗.

## Reviewer 1 — Security

- **"The mechanisms aren't novel."** *Conceded.* M1 = new-api #5235 + Cancellation Tax;
  M2 = CWE-807 + aperture #247; B0 = Kettle/Tyk. Fix: the paper claims
  **systematization + measurement + defense**, not new primitives; the abstract and
  intro use bounded language, and `novelty_matrix.md` states the type-B assessment
  openly.
- **"The threat model over-grants the attacker."** The attacker controls only its own
  requests, connection lifetime, and client-declared fields — exactly a real malicious
  client. It cannot forge provider metadata or other tenants' state. Documented in
  `threat_model.md`.
- **"The defenses are obvious."** They are — atomic decrement, reserve-reconcile,
  server recount are textbook. The contribution is showing, with numbers, *which*
  architectures leak, *how much*, and at *what overhead/detection level*, and that all
  three reduce to one invariant. Obvious-in-hindsight defenses that deployed systems
  still get wrong (new-api #5235) are worth measuring.
- **"M2 under-report is trivial (`tokens=1`)."** Addressed by modeling realistic
  multi-category usage (input/output/cached/reasoning, totals, rounding) and showing
  the exploitable set depends on the **billing basis** (category vs total) — a
  non-trivial, measured result.

## Reviewer 2 — Systems

- **"Testbed too narrow / not real inference."** ✗ (partially). The mock is
  deterministic by design; the M2 recount defense is nearly free here but costs a real
  tokenizer pass in production. Fix: stated as a primary threat to validity; overhead
  claims are limited to DB-operation cost; an optional local-model realism experiment
  is left as future work (not claimed).
- **"Timing artifact."** M1 leakage is a deterministic function of delivered tokens
  (std = 0), not a scheduling artifact; the abort-0% → ~1-token lag is reported.
- **"Single node, one row, HTTP/1.1."** Conceded and scoped in threats-to-validity;
  B0's effect is already saturated so HTTP/2 is unnecessary; multi-tenant contention is
  future work.
- **"Overhead measurement inadequate."** Fixed: added `run_overhead.py` with real
  per-request latency (M1 +9.8 ms, M2 +0.1 ms) and the tokenizer caveat.

## Reviewer 3 — Statistics / Methodology

- **"Sample size arbitrary."** Fixed: `power_analysis.py` derives reps from *measured*
  dispersion; leak is deterministic (std = 0) so the mean is pinned; proportion CIs
  (Wilson) are reported where the randomness actually is.
- **"Confidence intervals on deterministic quantities are meaningless."** Agreed and
  handled: we report point values for deterministic leak and say so; CIs are used only
  for proportions (ASR).
- **"Dependent trials / p-hacking / post-hoc hypotheses."** Trials are independent
  (fresh account state per cell; reconciliation asserted per trial). No p-values are
  computed or thresholded; hypotheses (H: commit timing and usage authority create
  measurable boundaries) were fixed before the sweeps and match the results. The
  taxonomy was *reduced* by evidence (M3 killed at its gate, M4/M5 in Phase 1), not
  grown to fit results.
- **"Raw dollar leak grows mechanically with workload."** Addressed: the headline metric
  is **leakage efficiency** (fraction of value evaded), which is price- and
  size-invariant; absolute dollars are secondary.
- **"Integrity of the numbers."** Every figure re-derives leakage from the per-request
  ledger and cross-checks the stored value; a mismatch fails the build (0 problems over
  420 + 840 + 1440 records/trials).

## Remaining weaknesses (honest)

1. ✗ **Production tokenizer cost for the M2 defense is unmeasured** (mock limitation).
2. ✗ **Mechanisms are type-B reframes**, so a venue demanding novel primitives may
   still reject; the paper is positioned as a measurement/systematization contribution.
3. ✗ **M1/M2 not evaluated under concurrency** (orthogonal to B0); a combined-stress
   experiment is future work.
