# COSE submission readiness report

Conversion of the frozen IEEE manuscript to an Elsevier *Computers & Security*
submission. This is a manuscript-conversion task: no experiment was re-run for
scientific reasons, no raw data changed, and no claim was strengthened or weakened
beyond what internal consistency required.

```
scientific results changed?  NO
raw data changed?            NO
IEEE source changed?         NO  (md5 1c1af42f87de71f2d386c38a1037259b, before and after)
```

---

## What this conversion did

1. New Elsevier manuscript `paper/main_cose.tex`, built on the official `elsarticle`
   LaTeX class (verified genuine — resolved and downloaded by tectonic's own TeXLive
   bundle, not fabricated), with `natbib` author-year citations.
2. Converted every IEEE numeric citation (`[12]`) to author-year form (`\citep`/`\citet`),
   alphabetized the bibliography by first-author surname then chronologically, and kept
   every fact (title, venue, year, arXiv ID, DOI-equivalent) exactly as verified in the
   IEEE source. No reference was added or removed; the count is unchanged at 26.
3. Converted IEEE Roman/`\section` numbering to Elsevier's plain numbered sections
   (1--15), with the required declarations (CRediT, competing interest, funding, GenAI
   disclosure, data availability, acknowledgements) as unnumbered back-matter sections
   in the order the task specified.
4. Rewrote the abstract to fit the 250-word limit (248 words, measured) while preserving
   every required content item: $V(r) \le N(r)$, the B0/M1/M2 decomposition, the
   no-new-primitive statement, TLA+/TLC, the M1 orthogonality result, the M2
   computation-vs-authority result, both leakage figures (58.3%/69.0%) correctly
   attributed to their respective settings, server-authoritative billing closing the
   leak, and the async B0 result.
5. Replaced the IEEE keyword "LLM security" with terms naming the actual subject
   (usage metering, quota enforcement, accounting reconciliation), matching the
   scope-positioning work already done for the IEEE version.
6. Rendered the five raster figures at 600 dpi (`paper/figures_cose/Figure_1.png`
   .. `Figure_5.png`) by re-running the frozen, unmodified plotting code with `matplotlib`
   DPI overridden — no code or data change, and `results/figures/` (the tracked 140 dpi
   research artifact) was verified untouched (0 lines of git diff) after generation.
7. Added all required declarations and side files (Section "Files produced" below).

## A real inconsistency found, and how it was handled

While reading the full frozen IEEE source to build the conversion, I found that
`paper/accounting_state_model_ieee.tex` — an `\input` file inside `main_ieee.tex` that a
previous consistency-audit pass did not grep directly — states, uncorrected:

> "This requires $\ge 2$ concurrent transactions, which is why B0 leaks nothing at
> concurrency 1." ... Table: "Needs concurrency? B0: **yes**" ... "This predicts the
> empirical result: B0 leakage is *created* by concurrency."

This is inconsistent with the abstract, the B0-revisited subsection, the sufficiency
conditions, the discussion, and the conclusion of the *same* IEEE manuscript, all of
which state the general condition established by the asynchronous experiment
(authorization must be atomically coupled to economic commitment on the authorizing
path; concurrency is one trigger among others). It survived because it lives inside an
`\input`-ed file, not the top-level `.tex` a keyword search would normally target.

**Per this task's explicit instruction not to modify the frozen IEEE source, it was left
exactly as-is in `paper/main_ieee.tex` / `paper/main_ieee.pdf`.** It is corrected only in
`paper/main_cose.tex`, whose accounting-state-model section (Sec. 4) now states the
baseline-trigger-versus-general-condition distinction explicitly, with a forward
reference to the async section, and whose structural table (Table 3, "structural
distinction between the three mechanisms") no longer has an unqualified "needs
concurrency: yes" cell.

This is recorded as a submission blocker for the IEEE artifact
(`paper/SUBMISSION_BLOCKERS.md`, item 5) rather than silently fixed there, since fixing
it would have violated the explicit "do not modify main_ieee.tex" instruction for this
task.

## Manuscript metrics

| metric | value | requirement | status |
|---|---|---|---|
| Abstract word count | 248 | <= 250 | PASS |
| Total article word count (body + references) | 10,007 | <= 12,000 | PASS |
| Keyword count | 9 | 5--10 | PASS |
| Reference count | 26 | unchanged from IEEE version | PASS |
| Figure count | 6 (1 TikZ + 5 raster) | -- | -- |
| Table count | 6 | -- | -- |
| Undefined citations | 0 | 0 | PASS |
| Undefined references | 0 | 0 | PASS |
| Duplicate labels | 0 | 0 | PASS |
| Overfull boxes | 2 (2.6pt, 6.8pt -- cosmetically negligible) | none damaging layout | PASS |
| Blank pages | 0 | 0 | PASS |
| Page count | 25 | -- | -- |

## Highlights

`paper/highlights.txt` -- 5 bullets, all measured at or under 85 characters
(64/64/66/66/68 chars). Content is drawn from actual measured results, not aspirational
language.

## Data repository

GitHub: https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING,
tagged release `v1.0.0`.

## DOI

**Not created.** `paper/main_cose.tex`'s Data Availability section states this
explicitly (`[ZENODO DOI TO BE INSERTED]`) rather than fabricating one. See
`paper/SUBMISSION_BLOCKERS.md` item 1 for the exact steps to close this.

## Declarations

| declaration | present | content |
|---|---|---|
| CRediT | YES | Single-author roles actually applicable: Conceptualization, Methodology, Software, Investigation, Formal analysis, Data curation, Validation, Visualization, Writing (both). Funding acquisition and Supervision deliberately omitted as unsupported. |
| Funding | YES | Standard no-funding declaration; no grant invented. |
| Competing interest | YES | Standard no-conflict declaration. |
| Generative AI disclosure | YES | Discloses that Claude (Anthropic) assisted with software development, experiment scripting, manuscript language refinement, and analytical/editorial review; states results and citations were independently verified and that AI tools are not authors. |

## Author biography

`paper/author_bio.txt` is a **TODO placeholder**. No biography, award, membership, or
position was invented. The author must supply verified content and a photograph before
submission. See `SUBMISSION_BLOCKERS.md` item 3.

## Blockers (full list in `paper/SUBMISSION_BLOCKERS.md`)

1. **Zenodo DOI** -- not yet created. Blocking.
2. Corresponding-author email choice (personal vs. institutional) -- non-blocking,
   author's call.
3. **Author biography and photograph** -- placeholder only. Potentially blocking,
   depending on the journal's current submission-system requirements.
4. Graphical abstract -- optional, not created (would require new artwork).
5. The IEEE-manuscript B0 inconsistency described above -- not a COSE blocker, recorded
   for a separate, explicitly-scoped follow-up.
6. Manuscript has not had a human/native-English read-through.

## Verification performed

| check | result |
|---|---|
| `scripts/check_cose_submission.py` | **30/30 checks passed**, exits 0 |
| `paper/main_ieee.tex` git diff | **empty** (byte-identical; md5 confirmed unchanged) |
| `paper/main_ieee.pdf` git diff | **empty** |
| `audit/recompute_all.py` | 0 discrepancies |
| `audit/m2_independent_check.py` | 0 mismatches |
| `formal/check.py` (TLC) | 40/40 matched, 0 disagreements |
| `experiments/regression_class6.py` | 19/19 |
| `experiments/regression_m.py` | 16/16 |
| `experiments/metamorphic_checks.py` | 22/22 |
| `results/figures/` git diff after 600 dpi render | empty (frozen artifact untouched) |
| Visual PDF inspection | title/author/abstract page, a figure page, declarations page, and references page all inspected and render correctly |

## Files produced

```
paper/main_cose.tex
paper/main_cose.pdf
paper/highlights.txt
paper/submission_metadata.md
paper/data_availability.md
paper/author_bio.txt
paper/SUBMISSION_BLOCKERS.md
paper/figures_cose/Figure_1.png .. Figure_5.png   (600 dpi)
scripts/check_cose_submission.py
scripts/count_cose_metrics.py
scripts/render_cose_figures.py
```

`paper/main_ieee.tex` and `paper/main_ieee.pdf` are unmodified.

---

## Final verdict

**BLOCKED** -- not on manuscript quality or scientific content, but on two concrete,
named external items that cannot be completed inside this conversion pass:

- **Zenodo DOI** (item 1) -- requires the author to connect the GitHub repository to
  Zenodo and cut a release; cannot be fabricated.
- **Author biography and photograph** (item 3) -- requires verified biographical
  content and a photograph from the author; cannot be invented.

Once those two items are resolved (and the corresponding-author email choice in item 2
is made deliberately), the manuscript itself -- structure, word counts, references,
declarations, figures, and internal consistency -- is submission-ready.
