# Confirmation-bias review

*Written during the corrective-audit phase, after the independent integrity audit
(`AUDIT_REPORT.md`) and before the final reproduction. Its purpose is to record where the
research process was structurally biased toward confirming its own hypotheses, not merely
where a number turned out wrong.*

The honest summary: **the accounting measurements survived independent recomputation, but
the interpretive layer around them did not.** Every defect the audit found was in a place
where the artifact *described* an outcome rather than *measured* one. That is a
recognizable pattern, and it is worth naming precisely.

---

## 1. Where the design let a hypothesis validate itself

### 1.1 Detectability (the worst case) — F1

The detectability taxonomy (D0 invisible / D1 reconcilable / D2 logged / D3 prevented)
was written down as part of the *taxonomy*, then implemented as a field the gateway
*emits*:

```python
detection_level = "D3" if arch.safe else "D0"   # M1
detection = arch.detection                       # M2 — static metadata
```

The experiment then read that field back and reported it as a result. No observation ever
entered the loop. The regression suite made this airtight in the wrong direction: it
asserted `detection_level == "D0"`, i.e. it verified that the code returned the constant
the experimenter had typed.

The re-derivation from evidence alone (`experiments/detectability.py`, blind to
architecture name, `safe` flag, and stored label) contradicts the claim outright:

* `client` and `client_logged` retain **identical** evidence fields, and receive
  **identical** evidence-derived levels — the entire published D0-vs-D1 distinction
  between them was an artifact of the label.
* **2,200 records** stored as D0 are D1 or D3 on the evidence.
* **No record in the study qualifies as D0 at all.** The category that carried the
  paper's most quotable detectability sentence is empty.

**Bias mechanism:** a taxonomy category was operationalized as an output rather than as a
measurement, and then the measurement pipeline was pointed at the output.

### 1.2 Backend generality — F3

"17/17 byte-identical across accounting backends" was true and also misleading. Of the 17
cells, 8 genuinely exercised both backends; 5 agree for an analytic reason (the M2 billed
amount is computed before any balance is read, so it *cannot* vary by backend); and 4 are
vacuous — they are the B0 cells, and the frozen B0 debit module contains zero references
to the backend abstraction, so those rows ran identical code twice and could not have
disagreed. B0 was never actually exercised against Backend B at all.

A second-order version of the same bias showed up while *fixing* this: my first
mechanical classifier scored agreements as vacuous whenever the leak was zero, which
produced 4 genuine / 5 analytic / 8 vacuous and contradicted the audit. That rule was
wrong — a defended M1 architecture with zero leak still drives reservations and
settlements through the backend interface and genuinely could have disagreed. The
correct discriminator is the *code path*, not the outcome value, and it reproduces the
audit's 8 / 5 / 4. Convenient-looking agreement between two of my own analyses was not
evidence that either was right.

**Bias mechanism:** the count was reported at the granularity that maximized it. Nobody
asked "how many of these could possibly have come out differently?" — the question a
skeptic asks first and an author asks last.

### 1.3 Concurrency invariance — F2

B0's concurrency slope is a real empirical finding. M1's invariance is a real empirical
finding. M2's invariance is a *derivation*: the billed amount is a pure function of one
request's declared usage, computed before any shared state is touched. The sweep could
not have produced any other answer. Presenting all three in one sentence as parallel
empirical results borrowed B0's evidential weight for a claim that never needed an
experiment.

**Bias mechanism:** rhetorical symmetry. Three dimensions, three findings, one sentence —
the shape of the argument drove the strength of the claim.

### 1.4 Attacker knowledge — F5

The M2 harness builds each manipulation by transforming the *true* server-side usage
vector, i.e. from oracle knowledge a real client does not have. This was never disclosed.

Grading the manipulations by required knowledge (K0 client-observable / K1
provider-reported / K2 oracle) turns out to *support* the paper — the headline attack
(90% output under-reporting, 58.3% leakage efficiency) is K0-feasible, because a client
can count the tokens it received. But that is luck, not method: the disclosure was
omitted, and had it gone the other way the paper would have shipped an attack that
requires knowing what the attack is trying to learn. Two manipulations (`inflate_cached`,
K1; `drop_reasoning`, K2) genuinely do need privileged knowledge and are now labelled.

**Bias mechanism:** convenience in the harness silently became an assumption in the
threat model.

### 1.5 Real-model timing — F6

The 0.014–0.019% figure was reported from a single measurement pipeline and was never
re-measured. The first audit pass did not re-measure it either, yet the audit's own
summary initially treated it as checked. Independent re-timing (separate code,
`audit/verify_real_model_timing.py`, 32 new tokens) gives 0.017–0.028% — same order of
magnitude, ratio rising as generation shortens, exactly as the cost model predicts. The
claim holds; the *verification* of it did not exist until now.

**Bias mechanism:** "verified" quietly expanded to mean "reported by a script I wrote".

---

## 2. Where the process was actually sound

This is not a symmetric list, and it should not be padded to look balanced.

* **The accounting core is genuinely independent.** `audit/recompute_all.py` shares no
  code with the measurement pipeline and reproduces 4,800 M2 records, 2,400 M1 records
  and 420 B0 trials with **0 discrepancies**; the B0 slope (0.099, R²=1.0) reproduces
  exactly. `audit/m2_independent_model.py` goes further, re-deriving ground truth from
  the *specification* — never reading the gateway's own `extra["true"]` field — with **0
  mismatches**.
* **Integrity gates fail closed, and this was tested adversarially** rather than assumed:
  corrupting a leak, a debit, a served flag, a balance, an invariant flag, or deleting a
  ledger row are each detected (12/12).
* **The project killed its own claims before the audit did.** M3 was eliminated at the
  decision gate; two of the original five attack classes were killed in the Phase 1
  novelty audit; a metamorphic property (P3, price-tier invariance) was retracted when
  the suite caught the author's own wrong assumption rather than the code's.
* **The ablation found a real bug in our defense** (`pre_debit` served requests when the
  reservation failed) — a case where the experiment was actually capable of embarrassing
  the design, which is the property all the failures above lacked.
* **Discrepancies were investigated rather than absorbed.** The 3 M2 cross-validation
  "mismatches" and 6 M1 "BUGs" were both traced to definitional differences and are now
  reported in both forms, not silently reconciled to the convenient one.

---

## 3. The generalizable lesson

Every finding in §1 shares one structure: **a claim was encoded in the artifact's
vocabulary before it was measured, and the measurement then read the vocabulary back.**
Detectability levels were emitted by the code that was supposedly being evaluated. The
backend count was taken at the granularity the code happened to produce. Concurrency
invariance inherited the framing of a neighbouring result. Attacker knowledge was
whatever the harness found convenient to pass in.

Where a number had to survive an *independently written* recomputation — the accounting
core — it survived, unanimously and exactly. Where it only had to survive being printed,
it did not.

The operational rule this suggests, and which the corrective phase applies: **a
measurement is only a measurement if the pipeline could have produced a different answer.**
For each reported quantity, the author must be able to state what result would have
falsified it. Applying that test mechanically to the claim matrix is what produced the
`ANALYTICALLY DERIVED` and `WITHDRAWN` classifications — categories the original matrix
had no way to express, which is itself part of the finding.

---

## 4. Disposition

| # | Finding | Disposition |
|---|---------|-------------|
| F1 | Detectability restates experimenter labels | **Claim withdrawn**; table removed; classifier replaced with an evidence-only one; regression assertion removed |
| F2 | Concurrency claim conflates empirical and analytic | Split three ways in the abstract and results; M2 reclassified `ANALYTICALLY DERIVED` |
| F3 | 17/17 backend parity overstated | Restated as **8 genuine** cases; B0 storage-independence declared untested in Threats to Validity |
| F4 | M2 checker read the gateway's own ground truth | Replaced by a specification-derived independent model (0 mismatches) |
| F5 | Undisclosed oracle-level attacker knowledge | K0/K1/K2 model added to the threat model; headline attack shown K0-feasible |
| F6 | Real-model timing never independently re-measured | Re-measured with separate code; wording widened to the verified range |

No finding was closed by argument alone; each was closed by a re-derivation, a
restatement of scope, or a withdrawal.
