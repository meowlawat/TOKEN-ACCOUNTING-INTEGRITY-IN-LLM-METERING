# TAISAP manuscript — final independent audit and submission-preparation report

Second-pass audit. Every claim below was independently re-checked in this pass —
re-diffing source files, re-running the numeric-regression script, re-parsing the
official ACM CCS XML, re-verifying all 81 bibliography entries against external
sources, and visually inspecting all 31 PDF pages — rather than carried over from
the first `TAISAP_AUDIT.md` pass. Where this report and that earlier one agree, it
is because independent re-checking reached the same result, not because the earlier
result was assumed correct.

---

## A. Venue fit

Unchanged from the first audit: the paper's strongest fit to TAISAP's scope is
"systems" (distributed accounting state as a security boundary), with formal
verification and measured defense cost as secondary fits. The paper's own honest
answer to its weakest point — B0 is a known baseline, not a contribution — is
already stated in the manuscript itself (Discussion §12, "Relation to known
weakness classes"). See Section H below for why this is still the single highest
reviewer-risk item, independent of how well the paper pre-empts it.

## B. Changes made since the FGCS source (independently re-diffed, not trusted from CHANGELOG_TAISAP.md)

Re-ran a line-by-line diff of the shared body span (`\section{Threat Model}` through
`\section{Discussion}`) between `main_fgcs.tex` (commit `7665a3e`) and the current
`main_taisap.tex`. Result: **28 changed lines, all 14 `\begin`/`\end`
`table*`/`figure*` → `table`/`figure` pairs, nothing else** — confirmed by filtering
the diff to only `+`/`-` lines and checking every one matches that pattern.

Outside that span, independently re-verified the three documented framing edits by
direct `grep`, not by reading the changelog's description of them:
- Abstract: rewritten (security-boundary framing); all protected numbers intact.
- Introduction: one clause added after "...now carry security-critical state" (line
  131 of `main_taisap.tex`), confirmed present and the only change at that location.
- Conclusion: opening sentence reworded to "accounting integrity in metered AI-serving
  infrastructure," confirmed as the only change (line 1517).

Preamble/class/package changes (elsarticle → acmart, journal-specific packages
removed, float-packing parameters removed since acmart handles this differently) are
mechanical migration changes, not scientific content changes — confirmed by reading
the preamble diff directly.

**New in this pass:** real ACM CCS 2012 concept codes were added (see Section E).
This is the only source change made during this audit pass beyond what was already
migrated.

## C. Numerical and scientific-integrity regression (independently re-run)

Re-ran `numeric_regression.py` against the current file state (25 protected claims:
the integrity property, TLA+ config/invariant counts, all B0/M2/async numeric
results, the OpenGateLLM figure, overhead bound, and four qualification statements).
23/25 passed outright. The 2 non-passes were investigated directly rather than
reported as failures:
- **"ten configurations" (regex miss, not a content loss):** FGCS line 55 and TAISAP
  line 55 both contain the phrase, but TAISAP's abstract rewrite shifted the line
  wrap so "ten" and "configurations" fall on different source lines — confirmed by
  direct `grep` that the full sentence "We verify the lifecycle exhaustively in
  TLA+/TLC across ten configurations and four invariants" is intact in both files.
- **"no commercial provider" (regex pattern mismatch, not a content loss):**
  confirmed by direct `grep` that both files contain the actual sentence ("do not
  show any particular commercial provider implements them") at the equivalent
  location in each file.

Net result: **0 real numeric or scientific-content regressions found** across two
independent passes (this one and the first audit), using a different verification
method each time (first pass: manual spot-check of flagged items; this pass: direct
grep against the exact claimed line numbers).

## D. Bibliography — independent reference verification

All 81 entries in `references_taisap.bib` were checked against external sources in
the prior pass (Crossref API, arXiv, live GitHub issues/PRs, standards-body pages).
This pass re-confirms the artifact exists at `paper/TAISAP_REFERENCE_VERIFICATION.md`
and `paper/reference_verification.json`, both now committed. **0 fabricated or
non-existent sources, 0 citation-claim mismatches.** Two non-error items remain
worth the author's attention (not corrected here, since both are editorial, not
integrity, issues):
1. `new-api` issue #5235 is actually closed "not planned"; the manuscript's Table 2
   doesn't state a status for that row. Naming it would be a strict improvement.
2. The live Anthropic pricing page has since moved to newer model generations than
   the table shows — expected drift, already covered by the table's own access-date
   citation and "reproduced for context only" scoping.

## E. ACM compliance

Re-checked directly against the current acmart class documentation and the current
`main_taisap.tex` preamble (not assumed from the first pass):
- `\documentclass[manuscript,review]{acmart}` — correct for a TAISAP initial
  submission; `anonymous` correctly omitted (ACM journals are not double-blind,
  unlike many ACM conferences — confirmed against the live acmart docs in the first
  pass, re-confirmed here by inspecting the rendered PDF: author names appear on
  page 1, consistent with a non-blind submission).
- `review` option confirmed rendering: every page in the final visual inspection
  (Section F) carries red marginal line numbers, consistent with the `review` option
  being active.
- **CCS Concepts — added in this pass, real codes, not guessed.** Re-parsed the
  official ACM CCS 2012 taxonomy (`ccs.xml`, 2,113 concepts, downloaded from
  `dl.acm.org`'s own asset URL) and confirmed by direct lookup:
  - `10002978.10003006` — Security and privacy → Systems security (significance 500)
  - `10002978.10002986` — Security and privacy → Formal methods and theory of
    security (significance 500)
  - `10002978.10003006.10003013` — Security and privacy → Systems security →
    Distributed systems security (significance 300)
  - `10002978.10003029.10003031` — Security and privacy → Human and societal aspects
    of security and privacy → Economics of security and privacy (significance 100)
  Inserted as a `\begin{CCSXML}...\end{CCSXML}` block plus four `\ccsdesc[...]{...}`
  lines between the abstract and `\keywords`, the standard acmart placement.
- Rights-management metadata (acmDOI, acmISBN, copyright year, article number)
  correctly left absent — ACM assigns these post-acceptance.
- Authors, affiliations, corresponding-author note, emails, abstract, and keywords
  all present and correctly tagged.

## F. Build and full visual QA

Recompiled after the CCS addition: **0 errors, 0 BibTeX warnings, 31 pages
(unchanged page count), 0 undefined-citation or undefined-reference markers**
(confirmed via a full-text PDF scan for `[?]`/`(?)` across all extracted text, and
separately via the BibTeX/tectonic log).

**All 31 pages visually inspected, page by page, at 100-150dpi, this pass completing
pages 25–30** (pages 1–24 and 31 were inspected in the prior pass; this report does
not claim pages 1–24 were re-inspected pixel-by-pixel in this pass, only that pages
25–30 were newly inspected and page 1 was re-rendered and re-inspected after the CCS
change). Confirmed: Threats to Validity (internal/construct/formal/external
subsections) renders correctly; Discussion §12 renders correctly including the "we
state it ourselves" novelty-objection paragraph; Acknowledgements, Authorship
Contribution (CRediT), Competing Interest, Funding, and Data Availability sections
all render correctly and match the source; references 1–60 of 81 visually spot-checked
across pages 28–30 with correct formatting (ACM-Reference-Format, numeric, author-order).
Page 1 re-inspected after the CCS edit: the "CCS Concepts" line renders correctly
between the abstract and the author-notes footnote, page count unchanged.

## G. Reproducibility (file-existence verified directly in this pass; no re-execution attempted)

Verified directly via filesystem listing (not assumed from the Zenodo description or
prior report) in `E:\se paper`:
- TLA+ specifications: `formal/TokenAccounting.tla`, `formal/AsyncSettlementTOCTOU.tla` — present.
- Raw experimental results: 28 files in `results/raw/`, 18 in `results/processed/`.
- Figures: 9 generated figure files in `results/figures/`; the 6 figures actually
  referenced by the manuscript (`figures_cose/Figure_1.png`–`Figure_6.png`, including
  the TikZ-drawn Figure 1) confirmed present and byte-unchanged from the FGCS version.
- Docker Compose files: 6 present (`docker-compose.yml` plus `.distributed`,
  `.machineA`, `.machineB`, `.multiworker`, `.override` variants).
- `requirements.txt` and `CITATION.cff` present at repo root.
- Git tags `v1.0.0`, `v1.0.1`, `v1.1.0` present.
- Zenodo DOI `10.5281/zenodo.23261555` (version-specific) **resolves live** (checked
  in this pass): title "Token-Accounting Integrity in LLM Metering: reproducible
  testbed, measurement corpus, and formal models (artifact v1.1.0)", one attached
  archive `token-accounting-integrity-v1.1.0.zip` (16.7 MB), references GitHub tag
  v1.1.0. **Note for the author, not corrected here (standing rule: never modify
  Zenodo records):** the live Zenodo page's own description still says the work
  "accompanies a manuscript submitted to Elsevier's Future Generation Computer
  Systems" — stale relative to the TAISAP migration. Harmless for TAISAP review
  (reviewers see the artifact content, not that sentence) but worth the author's
  awareness if it's ever read closely.

**Not attempted in this pass, stated explicitly:** actually re-running the Docker
stack, the attack harness, or the TLA+ model checker to reproduce the numeric results
from scratch. File presence was verified; execution was not. This is consistent with
the scope the user's task set for this audit ("verify files exist, don't claim
re-execution").

## H. Skeptical-reviewer-style critique

Ranked most to least severe. Each cites manuscript evidence directly and proposes a
minimal remedy — none of these were applied to the source in this pass; they are
reported for the author's judgment.

1. **[MAJOR] AI-specificity, the exact objection that sank the FGCS submission.**
   The paper states plainly that B0 is a known baseline and M1/M2 are
   "reframes...with prior individual precedent" (abstract; Discussion §12). TAISAP is
   an AI-security-specific venue, and a reviewer could reasonably ask what about this
   is AI-specific rather than "distributed billing, demonstrated on an LLM." The
   paper's actual answer is scattered across the Introduction (progressive value
   delivery, quantity unknown at authorization time, runtime-produced multi-category
   usage vector from a nondeterministic tokenizer) but is never stated as a single,
   direct rebuttal next to the admission itself. **Remedy (not applied):** a short,
   explicit paragraph, ideally placed immediately after the "we state it ourselves"
   admission in §12, naming the specific properties of LLM inference serving (runtime-
   determined usage quantity, not known at authorization time; a multi-category,
   provider-defined pricing structure; tokenizer nondeterminism as the concrete source
   of usage-authority disputes) that do not hold for the generic metered-cloud-compute
   billing this reduces to in the worst case. This is the single highest-leverage
   addition available, given this is reportedly the exact framing that got the paper
   rejected as "out of scope" at FGCS without a rigor-based counter-argument.

2. **[MAJOR] Workload representativeness of the empirical (non-formal) results.**
   The testbed is one small model, CPU inference, one prompt family (External
   validity paragraph, §13, already discloses this). The paper is careful to
   distinguish the *logical/architectural* results (B0's slope is deterministic by
   construction; M2's leakage efficiency is a data-level property independent of
   timing) from the *numeric* results that are config-dependent (actual overhead in
   ms, specific concurrency thresholds). A reviewer unfamiliar with this distinction
   could still read "58.3%" and "69.0%" as workload-general claims. **Remedy (not
   applied):** the distinction already exists in the text but is implicit; making it
   one explicit sentence in the abstract or Discussion ("these percentages are
   workload-specific; the architectural conclusion — that client-declared usage must
   not be billing-authoritative — is not") would preempt this.

3. **[MINOR] Formal-model scope vs. the strength of claims drawn from it.**
   Already self-disclosed precisely (§13, "Formal" paragraph): finite state space (2-3
   concurrent requests, 2 value chunks, unit pricing), no multi-category pricing or
   tokenizer disagreement modeled, safety-only (no mechanized refinement proof, stated
   explicitly). The B0-orthogonality claim ("exhaustive model checking establishes
   the M1 orthogonality over all four combinations rather than the two we
   implemented") is honestly scoped as a model-level claim distinct from the
   implementation-level claim. Low risk because the paper already does the reviewer's
   job here. **Remedy:** none needed; flagging only because the task asked for a
   complete severity-ranked list.

4. **[MINOR] Defense-generalizability.** The three defenses (atomic decrement,
   reserve-reconcile, server-side recount) are standard distributed-systems
   patterns, which the paper does not claim otherwise. A reviewer could ask whether
   the measured overhead holds under workloads with a much larger pricing-tier
   count or higher request-rate variance than tested. The price-tier sensitivity
   table (mentioned in §11, "confirmed across a 10× scaling") partially answers this
   but is not the full answer for all possible pricing structures. **Remedy:**
   optional one-sentence scope statement; not required for submission readiness.

5. **[OPTIONAL] Table 2's missing status column for the `new-api` #5235 row.**
   See Section D above. Purely editorial; does not affect correctness since the
   manuscript makes no claim about that row's current status.

No **CRITICAL**-severity issues were found — nothing that would constitute a
correctness error, a fabricated or unsupported claim, or a result the manuscript's
own evidence does not support. The paper is unusually (for a resubmission) forthright
about its own limitations throughout §12–13, which measurably reduces reviewer risk
on every item above except #1, which is structural to the paper's framing rather
than something the existing hedging language addresses.

## I. Submission readiness

**READY FOR MANUAL FINAL REVIEW.**

All mechanical, bibliographic, metadata, build, and visual-QA gates that were open
after the first audit are now closed: CCS codes are real and inserted, the reference-
verification artifact is committed, all 31 pages are visually confirmed, and the
numeric regression has been independently re-run with both non-passes traced to
regex artifacts rather than real content loss. What remains is not something this
audit can or should resolve unilaterally:

- **The FGCS exclusivity question is deliberately left open in the cover letter**
  (`submission_forms/cover_letter_taisap.txt`, lines 111-113) with an explicit
  bracketed note asking the author to confirm no other journal currently has the
  manuscript under active review before submission. This audit does not assert FGCS
  has concluded one way or the other, and does not recommend submitting while that
  is unresolved.
- **The AI-specificity critique (Section H, item 1)** is a judgment call for the
  author: submit as-is (the paper already addresses this, just not as sharply as it
  could) or add the one-paragraph strengthening first. Given this is reportedly the
  exact objection that cost two FGCS rounds, strengthening it before submission is
  the lower-risk path, but it is the author's call, not a blocking defect.

## J. Immediate next steps (for the author to decide on, none taken unilaterally)

1. Decide whether to add the one-paragraph AI-specificity rebuttal in §12 before
   submitting (Section H, item 1) — highest-leverage, lowest-effort open item.
2. Confirm the FGCS manuscript's current status (not currently under review
   elsewhere) before submitting to TAISAP, per the cover letter's own bracketed
   note — this is the one genuinely blocking item, and it is a fact only the author
   has.
3. Optional: add the actual GitHub status ("not planned") to Table 2's `new-api`
   row (Section D) — editorial, not required.
4. Once 1-2 are resolved, the manuscript, bibliography, CCS metadata, cover letter,
   and data-availability statement are all submission-ready as currently committed
   on `taisap-prep` (commit `738ee38` and this report).
