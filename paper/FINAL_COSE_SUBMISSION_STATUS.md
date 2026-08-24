# Final C&S submission status

Final pre-submission cleanup pass: correct the hidden B0 inconsistency in the IEEE
source, verify the Elsevier manuscript did not regress, and record what remains blocked.

```
IEEE hidden B0 inconsistency fixed:      YES
C&S manuscript unaffected scientifically: YES
raw data changed:                        NO
experimental results changed:            NO
```

---

## What was fixed

`paper/accounting_state_model_ieee.tex` — a file `paper/main_ieee.tex` pulls in via
`\input` — still asserted, uncorrected:

- "This requires $\ge 2$ concurrent transactions, which is why B0 leaks nothing at
  concurrency 1."
- A structural table column headed **"Needs concurrency?"** with **B0: yes ($\ge 2$)**.
- "This predicts the empirical result: B0 leakage is *created* by concurrency."

These contradicted the corrected condition already stated in the same manuscript's
abstract, B0-revisited subsection, sufficiency conditions, discussion, and conclusion.
The earlier consistency audit missed it because it searched only the top-level
`main_ieee.tex` and never followed the `\input`.

**Corrected to distinguish two things that had been conflated:**

- *Baseline manifestation* — the non-atomic check-then-decrement implementation we
  measured exhibits the classic lost-update race when requests overlap, which is why the
  baseline leaks nothing at concurrency 1. That remains true and is still stated.
- *General security condition* — the failure holds whenever authorization observes
  economic state that does not yet include the commitments produced by previously
  authorized service. Overlapping requests create that separation; deferred settlement
  creates it too, under strictly sequential arrivals. The condition is therefore that
  authorization be atomically coupled to economic commitment on the path that authorizes
  service.

The table column is now **"Baseline trigger"**, with B0 reading "overlapping requests
($\ge 2$), or deferred settlement" and the closing column stating the coupling condition
rather than a specific SQL mechanism.

**Two related fixes in the same file**, addressing the same class of imprecision:

- M1's bare "concurrency-invariant" now reads as a measurement of the tested architecture
  under fixed request volume, explicitly not a property of all deployments.
- M2's now states that independence from concurrency is *analytic* under the modeled
  per-request billing function, with the sweep serving as an implementation check rather
  than as its evidence.

B0 is still presented as a known generic baseline. No claim was made that concurrency is
irrelevant to the baseline implementation, and B0 is not described as LLM-specific.

## Builds

```
IEEE PDF rebuilt:  PASS  (13 pages, 0 blank)
C&S PDF rebuilt:   PASS  (25 pages, 0 blank)
```

Visually inspected in the rebuilt IEEE PDF: the corrected structural table (Table II,
page 3), the corrected B0/M1/M2 mechanism-localization paragraphs, and the resolved
cross-references to §X-F (B0 revisited) and §VIII-B (M1 results).

## C&S manuscript metrics

```
C&S abstract words:   248   (limit 250)
C&S article words:  10,010  (limit 12,000)
C&S keywords:            9   (range 5-10)
references:             26
figures:                 6
tables:                  6
```

```
undefined citations:   0
undefined references:  0
duplicate labels:      0
overfull boxes:        2   (2.6 pt and 6.8 pt -- cosmetically negligible)
```

`scripts/check_cose_submission.py`: **30/30 checks passed.**

The only C&S changes in this pass were a proofreading pass: British-to-American spelling
normalization (`modelling`/`behaviour`/`labelled`/`catalogue`/`unmodelled` → American
forms, aligning with the already-dominant `defense`/`center`) and expanding "TLC" to "the
TLC model checker" at first substantive use in the body. No scientific content changed;
the diff is visible and contains no numbers, claims, or citations.

## Scientific regression

```
regression_class6:  PASS  19/19
regression_m:       PASS  16/16
metamorphic:        PASS  22/22
recompute_all:      0 discrepancies
independent M2:     0 mismatches
TLC:                40/40, 27,526 distinct states, 0 expectation disagreements
```

`git diff` over `results/raw`, `results/processed`, `results/tables`, and
`results/figures` is empty. No raw data was touched.

## Remaining blockers (external materials only)

```
Zenodo DOI:          PENDING  -- not minted; manuscript carries an explicit placeholder,
                                not a fabricated identifier
author bio:          PENDING  -- paper/author_bio.txt is a marked TODO; nothing invented
author photo:        PENDING  -- passport-style image not supplied
graphical abstract:  OPTIONAL -- not created; would require new artwork
```

Also outstanding, non-blocking but worth a deliberate decision:

- Corresponding-author email: `hardikahlawat13@gmail.com` (as supplied) versus the
  institutional address on the author's resume. Academic convention favors the
  institutional one.
- No human or native-English final read-through has occurred. The automated proofreading
  pass above is not a substitute.

Full detail in `paper/SUBMISSION_BLOCKERS.md`.

## Submission package

```
paper/main_cose.tex
paper/main_cose.pdf
paper/highlights.txt
paper/submission_metadata.md
paper/data_availability.md
paper/author_bio.txt              (TODO placeholder)
paper/cover_letter.md
paper/SUBMISSION_BLOCKERS.md
paper/figures_cose/Figure_1.png .. Figure_5.png   (600 dpi)
scripts/check_cose_submission.py
```

## Versioning

```
v1.0.0  immutable historical artifact -- preserved, not withdrawn, data unchanged
v1.0.1  supersedes v1.0.0 for submission use (scientific consistency correction)
```

v1.0.0 is deliberately left pointing at the pre-correction IEEE history rather than being
retagged, so the record shows what was actually frozen at that point. `RELEASE_FREEZE.md`,
`RELEASE_NOTES.md`, `FINAL_RESEARCH_REPORT.md`, and `JOURNAL_READINESS_REPORT.md` all
state the supersession and describe the correction as a consistency fix, not a new
finding. `JOURNAL_READINESS_REPORT.md` additionally retracts its own earlier claim that
the IEEE manuscript was fully consistent, and records why that claim was wrong: an audit
that greps one file is not an audit of the document that file assembles.

---

## FINAL STATUS

```
SCIENCE FROZEN
C&S MANUSCRIPT READY
SUBMISSION BLOCKED ONLY BY EXTERNAL MATERIALS
```

Not submitted. Zenodo DOI does not exist. Author biography and photograph not supplied.
