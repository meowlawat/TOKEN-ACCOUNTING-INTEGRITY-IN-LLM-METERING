# Independent Research Integrity Audit

**Auditor role:** adversarial, independent. Objective was to break the project, not to
confirm it. **Baseline:** commit `f533d69`, clean tree.

All recomputation was done with newly written code in `audit/` that imports nothing from
the project and re-derives ground truth from first principles.

---

## Executive verdict

> ## VERIFIED WITH MATERIAL LIMITATIONS

The **core measurement results are real and independently reproducible**. I re-derived
every headline quantity from raw data without trusting any project code and found **zero
discrepancies across 7,200 per-request records and 420 trials**.

However, I found **four material problems**, one of which **contradicts a published
claim** and must be corrected before submission:

1. **Detectability (D0–D3) is declared by configuration, never measured — and the D0
   claim is contradicted by the data.** (Most serious.)
2. **The M2 concurrency-invariance result is analytically necessary**, not an empirical
   discovery — the experiment could not have produced any other answer.
3. **The cross-backend "17/17 identical" claim is partly vacuous** — 4 of 17 cases never
   touched the backend under test.
4. **The "independent" M2 checker is only partially independent** — it inherits the
   gateway's own notion of true usage.

None of these invalidate the central leakage findings. All of them narrow what the paper
may claim.

---

## Evidence quality

| dimension | rating | basis |
|---|---|---|
| Implementation correctness | **Strong** | Independent re-derivation of true usage, pricing, all 7 transformations, and per-architecture billing basis matched the gateway on every one of 4,800 M2 records. |
| Experiment design | **Moderate** | Controls are genuine and volume is properly held constant, but one headline experiment (M2 × concurrency) cannot fail by construction. |
| Raw data | **Strong** | No duplicated, missing, overwritten, or stale rows detected. Conservation recomputed independently holds on every trial. |
| Analysis independence | **Moderate** | Summarizers import only generic stats helpers (good), but the "independent checker" is partially dependent, and detectability is not computed from observation at all. |
| Reproducibility | **Strong** | Numbers regenerate from raw data; my alternative-path recomputation agrees exactly. |
| Statistical validity | **Strong** | Deterministic conditions are correctly reported as constants rather than with fabricated p-values. I independently reproduced B0 slope = 0.099, R² = 1.0. |
| Formal model | **Moderate** | Sufficiency is argued within the model and honestly labelled as not machine-checked; but see the invariant-scope issue below. |

---

## Independent recomputation results

`audit/recompute_all.py` — no project imports; ground truth re-derived as
`input = max(1, word_count)`, `output = 40 + (sha256(f"{seed}:{prompt}")[:16] mod 41)`,
`reasoning = output // 2`; pricing, transformations and billing bases re-implemented.

| dataset | records/trials | true-usage mismatch | auth-cost mismatch | billed mismatch | leak mismatch | invariant mismatch | conservation fail |
|---|---|---|---|---|---|---|---|
| M2 | 4,800 records | **0** | **0** | **0** | **0** | **0** | **0** |
| M1 | 2,400 records | n/a (n_out matched) | **0** | — | **0** | **0** | **0** |
| B0 | 420 trials | — | — | — | **0** | — | **0** |

Independently recomputed B0 regression: **slope = 0.099 per additional concurrent
request, R² = 1.0** — matches the paper exactly.

**Classification: EXACT_MATCH on every compared quantity.** The measurement layer is
trustworthy. This is the strongest positive finding of the audit, and it is what
downgrades the other findings from "invalidating" to "limiting".

---

## Findings

### F1 — Detectability is declared, not measured, and D0 is contradicted (**CONTRADICTED**)

**What the code does.** In `app/m_routes.py`, detectability is assigned from static
architecture metadata, never from observation:

```python
# M2
detection = arch.detection          # a hardcoded field on the architecture object
# M1
detection_level = ("D3" if arch.safe else "D0")   # literally restates the `safe` flag
```

The M1 detection level contains **zero measured information** — it is a rename of the
`safe` boolean that the experimenter set.

**Why it is worse than a labelling weakness.** The paper claims `client` is **D0
("invisible — the ledger faithfully records the client's lie")** and that *"merely logging
a recount moves the same leak to D1"*. I inspected the actual ledger rows:

| architecture | declared level | `extra["true"]` stored? | `extra["declared"]` stored? | discrepancy visible in the row? |
|---|---|---|---|---|
| `client` | **D0** | **yes** | yes | **YES** |
| `client_logged` | D1 | yes | yes | YES |

Both rows are **identical in evidential content** (`true` = 60 output tokens,
`declared` = 6, `authoritative_cost` = 0.139, `net_debit` = 0.058). A reconciliation pass
would detect the `client` leak just as easily as the `client_logged` leak.

**Impact.** Claim C24 ("logging a server recount moves an M2 leak from D0 to D1") is
**contradicted by the implementation**. The detectability table is a design table
presented as a result. The regression assertion `detection_level == "D0"` is circular —
it verifies that the configuration equals itself.

**Does it change the leakage results?** No. Leakage, ASR, and invariant violations are
unaffected. Only the detectability dimension is affected.

### F2 — M2 concurrency-invariance is analytic, not empirical (**CONFIRMATION BIAS**)

In `m2_complete`, `billed_cost` is a pure function of
`(prompt, seed, manipulation, architecture, prices)`. No shared or concurrent state enters
the computation. Therefore leakage efficiency **cannot** vary with concurrency, and the
5-level concurrency sweep **could not have produced any other result**.

Asking the audit brief's question — *"what alternate outcome would this experiment have
detected?"* — the answer for M2 is **none**. This is a tautology check, not evidence.

**M1 is different and the distinction matters.** There, `delivered` is genuinely measured
at runtime (incremented per token, terminated by `request.is_disconnected()`), and it
*did* vary under load (within-cell σ of delivered tokens is exactly 0 at c ≤ 20 and ≈0.011
at c ∈ {50,100}). The accounting nevertheless tracked delivered tokens exactly at every
level. That is a genuine — if modest — empirical result: contention perturbs delivery
timing but does not corrupt settlement.

**Impact.** The paper presents B0-vs-M1/M2 concurrency behaviour as a unified empirical
discovery. For M2 it is a restatement of the implementation; for M1 it is real. The claim
must be split.

### F3 — Cross-backend "17/17 identical" is partly vacuous (**PARTIALLY VERIFIED**)

I traced which code paths the accounting-backend selector actually reaches.

- **B0 (`/complete`) does not use the pluggable backend at all.** `app/main.py` calls
  `app/metering/debit.py`, which contains **zero** references to `backends`/
  `active_backend` and always mutates `credits.balance` directly.
- **Direct database evidence:** with the backend set to `ledger`, I ran a 5-request B0
  trial and a 1-request M2 trial. `ledger_entries` contained exactly **one** row (the M2
  debit). B0's five requests produced **no** ledger rows.

So the 4 B0 rows in the "17/17 identical" table ran **byte-identical code twice**; their
agreement is guaranteed and carries no information.

Breaking the 17 cases down honestly:

| cases | status |
|---|---|
| 4 B0 | **vacuous** — backend setting ignored entirely |
| 5 M2 | **weak** — `billed_cost` (and therefore leak) is computed *before* the backend is called; only balance storage differed |
| 8 M1 | **genuine** — reserve/debit/refund go through the facade, so the backend can affect the outcome |

**Impact.** "17/17 byte-identical across accounting backends" overstates the evidence.
The defensible statement is that **8 cases genuinely exercised the differing storage
architecture and agreed**, plus conservation held under both designs.

### F4 — The "independent" M2 checker is partially dependent (**MITIGATED**)

`defenses/m2_independent_checker.py` imports nothing from the project (verified), but it
takes `record["extra"]["true"]` — *the usage vector the gateway itself wrote* — as ground
truth. It independently re-implements pricing, but inherits the system's own notion of
what the true usage was. Had `_server_truth()` been wrong, the checker would have computed
the "expected" cost from the same wrong vector and agreed perfectly.

**Mitigation:** my own recomputation closed this gap by re-deriving true usage from
`sha256` and confirming it matches on all 4,800 records (0 mismatches). So the underlying
values are correct — but the project's own independence claim was overstated, and it was
**my** check, not the project's, that established it.

---

## Circular validation findings

| check | circular? | notes |
|---|---|---|
| Summarizer imports | **No** | Only `experiments/_stats` (generic statistics). No pricing/debit imports. |
| M2 independent checker | **Partially** | See F4 — inherits gateway's true-usage vector. |
| Detectability assertions | **Yes** | F1 — tests verify configuration equals itself. |
| Regression suites | **No** | Assert properties (`leak == 0`, `leak > 0`, `invariant_ok`), not magic constants. Correct design. |
| Fault injection | **No, but shallow** | Corruptions are detected because stored ≠ recomputed. Genuine, but tests only *result-file* integrity: a gateway bug writing *consistent-but-wrong* values would pass every gate. My first-principles recomputation is what covers that case. |

**Answer to the brief's key question — "could the implementation be wrong and still pass
this test?"** For the integrity gates: **yes**, if it were wrong consistently. That gap is
closed only by the auditor's independent derivation, not by the project's own machinery.

---

## Hard-coded-result findings

Searched `experiments/`, `attacks/`, `defenses/`, `app/`, `benchmarks/` for the headline
constants (0.0528, 0.583, 0.595, 0.741, 0.0960, 0.099, 58.3).

**No hard-coded expected results in any measurement, attack, or defense code.** The only
occurrences are in `experiments/build_claim_matrix.py`, which is a documentation
verification tool that checks a number appears in a generated table. That is acceptable in
purpose but **brittle**: if data changed, the matrix would need manual updating, and its
`file_contains` check would then fail loudly rather than silently — acceptable.

The defense-labelling issue in F1 (`"D3" if arch.safe else "D0"`) is the one place where an
outcome is derived from configuration rather than measurement.

---

## Negative-control audit

**Genuine.** Honest-client arms produce leak = 0 and attacker arms produce leak > 0, and I
verified this from independently recomputed values, not from labels. The distinction
arises from system behaviour (`manipulation == "honest"` ⇒ declared vector equals true
vector ⇒ billed equals authoritative), not from an assigned outcome.

---

## Paper/data discrepancies

| paper number | independently verified? | notes |
|---|---|---|
| B0 slope 0.099, R² 1.0000 | **YES** | Recomputed from raw trials by the auditor. |
| M1 leak/req 0.0528 across c=1..100 | **YES** | Recomputed; invariance holds in the data. |
| M1 abort curve 0.0045→0.0285→0.0540→0.0960→0.0000 | **YES** | Recomputed from delivered tokens. |
| M2 efficiency 0.583 (`client`/`client_logged`) | **YES** | Recomputed independently. |
| M2 0.595 (ablation) | **YES** | Different probe prompt ⇒ different token mix; correctly attributed in the paper after the earlier hardening pass. |
| M2 `total_mismatch` 0.741 under flat-total | **YES** | Recomputed. |
| Tokenizer 2.9–3.6× engine spread | **Not re-measured** | Timing claim; not re-run in this audit. **UNVERIFIED by the auditor** (previously measured, plausible). |
| Real-model 0.014–0.019% | **Not re-measured** | Same. **UNVERIFIED by the auditor.** |
| Topology 96 cells / 0 mismatches | **Structurally verified** | Comparison logic inspected and found sound; the cells themselves derive from the same verified raw schema. |
| Backend 17/17 identical | **CONTRADICTED as stated** | See F3 — 4 cases vacuous, 5 weak. |
| Detectability D0 vs D1 | **CONTRADICTED** | See F1. |

---

## Security-model issues

**Invariant scope.** `V(r) ≤ N(r)` is applied per request, which is correct for the
mechanisms studied, but the audit brief's questions expose untested edges the paper does
not address: cache hits with zero new debit, asynchronous reconciliation that temporarily
violates the invariant without economic leakage, and account-level versus request-level
enforcement. The paper's per-request framing is defensible for M1/M2/B0 but should not be
presented as *the* complete accounting-security property.

**Attacker capability.** The harness is slightly *idealized*, not overpowered: for M2 the
client sends a manipulation *name* and the **server** applies the transformation to the
true usage (`STRATEGIES[req.manipulation](true_usage)`). A real attacker would have to
construct the vector itself, which requires knowing the true output count. The endpoint
does accept a client-supplied `client_usage` vector, so the capability is available — but
the reported experiments mostly used the convenience path, which grants the attacker exact
knowledge of the true usage. This should be stated.

---

## Architecture issues

The three "topologies" are genuinely distinct at the process/container level (verified:
four distinct worker PIDs served requests; both containers served traffic), and the
observed accounting parity is real. But **the security-relevant code is identical across
all three** — the same handlers, the same pricing, the same settlement. What the topology
experiment establishes is that *per-request accounting logic is not corrupted by
concurrency across processes*, which is valuable but weaker than "the results generalize
across architectures".

---

## Statistical issues

**None material.** The handling of deterministic quantities is correct and unusually
honest — the analysis explicitly declines to compute p-values against zero variance. I
independently reproduced the one regression claim (B0 slope/R²) and it matches. No hidden
outlier deletion or post-hoc selection was found.

---

## Novelty issues

Unchanged from the project's own assessment, which I consider accurate: the mechanisms are
known individually and the paper says so. My audit adds one caution — with F1 removed
(detectability was one of the four "dimensions" of contribution) and F2 narrowing the
concurrency claim, the surviving distinct contribution is **narrower** than the paper
currently implies: an accounting model, a measured ablation of enforcement primitives, and
a reproducible benchmark.

---

## Reproduction result

**PASS via an alternative path.** I did not use `scripts/reproduce_all.sh`. I recomputed
all central metrics from raw JSON with independent code and separately queried the live
database for backend-coverage evidence. Every leakage/conservation/invariant quantity
agreed exactly.

---

## Critical fixes required before submission

1. **Remove or re-derive the detectability claim (F1).** Either (a) delete the D0–D3
   dimension and its table, or (b) compute detection *from the ledger contents* (e.g.
   "can a reconciliation pass recover the discrepancy from stored fields?") and re-run.
   As implemented, `client` and `client_logged` are equally detectable and the claimed
   distinction is false. Claim C24 must be withdrawn.
2. **Split the concurrency claim (F2).** State that M2's invariance follows analytically
   from the implementation (billed cost is a pure function of the request), and that only
   M1's invariance is an empirical result about settlement under contention.
3. **Restate the backend result honestly (F3).** Replace "17/17 identical" with the 8
   genuinely-exercised cases, and either wire B0 through the pluggable backend or state
   explicitly that B0 was not covered by the backend experiment.
4. **Downgrade the independence claim for the M2 checker (F4)**, or make the checker
   re-derive true usage from `(prompt, seed)` as the auditor's script does.
5. **Disclose the M2 attacker idealization** (server-applied transformation grants exact
   knowledge of true usage).

---

## Publication impact

| venue | before audit | after audit |
|---|---|---|
| Workshop | READY | **Still ready** after fixes 1–3; the core measurement survives. |
| *Computers & Security* | submittable | **Submittable only after fixes 1–3.** Submitting with a demonstrably false detectability claim would be a serious problem in review. |
| IEEE TDSC | not ready | **Not ready** (unchanged; formal rigor). |
| Top-tier conference | not recommended | **Not recommended** (unchanged). |

The audit does **not** invalidate the project. The leakage measurements — the substance of
the paper — are independently reproducible and exact. What it invalidates is one
subsidiary claim (detectability) and the strength of two others (concurrency generality,
backend generality).

---

## Corrections resulting from independent audit

*Appended after the corrective phase. Every fix below was applied, then re-verified by a
second independent pass; nothing was closed by argument alone.*

| # | Finding | Status | What was actually done | Re-verification |
|---|---------|--------|------------------------|-----------------|
| **F1** | Detectability declared, not measured; D0 contradicted | **CLAIM WITHDRAWN** | The paper now carries `\subsection{Detectability: a claim we withdraw}`; the assertion table generator emits nothing and returns `status: WITHDRAWN`; the hand-written matrix is deleted; the regression assertion that checked for the constant `"D0"` is removed; the two `detection_level` sites in `app/m_routes.py` are annotated as non-measurements retained only for raw-data reproducibility. Claim C24 is reclassified `WITHDRAWN`. | `experiments/detectability.py` (blind to architecture, posture, stored label): `client` and `client_logged` retain **identical** evidence and receive **identical** levels; **2,200** stored-D0 records are D1 or D3 on the evidence; **no record qualifies as D0**. |
| **F2** | M2 concurrency-invariance is analytic | **SPLIT THREE WAYS** | Abstract and results now distinguish B0 (empirical slope), M1 (empirical invariance), M2 (analytic invariance, experiment confirms rather than discovers). Claim C10 reclassified `ANALYTICALLY DERIVED` — a category the original matrix could not express. | The derivation is stated in the paper with its implementation witness: billed cost is computed at `app/m_routes.py:378`, before `ledger.read_balance` at `:380`. |
| **F3** | "17/17 identical" partly vacuous | **RESTATED AS 8** | `summarize_generality.py` now classifies every cell GENUINE / ANALYTIC / VACUOUS **by code path**, and the generated table carries the classification. Paper, `journal_reviewer_attack.md` and `JOURNAL_READINESS_REPORT.md` all state *eight genuine cases agreed, none disagreed*. B0's storage independence is declared **untested** in Threats to Validity. | Regenerated: `GENUINE=8, ANALYTIC=5, VACUOUS=4`, matching the audit's manual count. |
| **F4** | "Independent" M2 checker partially dependent | **REPLACED** | `audit/m2_independent_model.py` re-derives true usage, pricing, all 7 transformations and the per-architecture billing basis **from the specification**, never reading the gateway's `extra["true"]` and importing no project code. | `audit/m2_independent_check.py`: **0 mismatches**. |
| **F5** | Undisclosed oracle-level attacker knowledge | **DISCLOSED** | A K0/K1/K2 knowledge model is added to the threat model. The headline attack (90% output under-reporting, 58.3% efficiency) is **K0-feasible**; `inflate_cached` is K1 and `drop_reasoning` is K2, both labelled and excluded from the main claim. | `knowledge_required()` grades each manipulation from its definition, not its outcome: K0-and-leaking = `under_report_output_50/90`, `under_report_input_50`, `rounding_shave`. |
| **F6** | Real-model timing never re-measured | **RE-MEASURED** | `audit/verify_real_model_timing.py` re-times the recount with separately written code. Paper wording widened to *well under 0.1%* with both ranges and their generation lengths given. | 0.0169–0.0277% at 32 new tokens vs the artifact's 0.014–0.019% at 64 — same order of magnitude, ratio rising as generation shortens, as the cost model predicts. |

### What did *not* change

The accounting core was not touched, and did not need to be. `audit/recompute_all.py`
(zero project imports) still reproduces **4,800 M2 records, 2,400 M1 records and 420 B0
trials with 0 discrepancies**, and the B0 slope at 0.099 with R²=1.0000. The B0/M1/M2
definitions, the frozen debit module, and all raw data are unchanged; no inconvenient
data was deleted, and the withdrawn detectability field remains in the stored records so
historical runs stay byte-reproducible.

### Post-fix re-verification

| check | result |
|---|---|
| `audit/recompute_all.py` (independent) | **0 discrepancies** |
| `audit/m2_independent_check.py` (spec-derived) | **0 mismatches** |
| `experiments/regression_m.py` | **16/16 pass** |
| `experiments/metamorphic_checks.py` | **22/22 pass** |
| `experiments/run_cross_validation.py` | M2 42 cells, M1 16 cells, B0 2 cells — **all implementations agree** |
| Summarizer integrity gates (B0, M1, M2) | **PASS, 0 problems** |
| Topology generality | 96 cells, **0 mismatches** |
| Claim matrix | 33 claims, **0 UNSUPPORTED** (1 WITHDRAWN, 1 ANALYTICALLY DERIVED) |
| `paper/main.pdf` | compiles, **0 overfull boxes** |

### Revised executive verdict

> ## VERIFIED — MATERIAL LIMITATIONS NOW STATED IN THE PAPER

The four material problems are closed by withdrawal (F1), scope restatement (F2, F3),
re-implementation (F4), disclosure (F5) and re-measurement (F6). The paper now claims
less than it did before the audit, and everything it claims has been recomputed by code
that shares nothing with the pipeline that produced it. A process note is recorded
separately in `audit/confirmation_bias.md`, including a second-order bias caught during
the fix itself: the first replacement classifier for F3 used outcome value rather than
code path and reproduced the wrong split until it was checked against the audit.
