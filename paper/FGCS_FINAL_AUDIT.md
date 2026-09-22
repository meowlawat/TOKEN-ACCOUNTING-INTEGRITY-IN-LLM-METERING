# FGCS Final Audit

Written after the FGCS adaptation. Files produced: `paper/main_fgcs.tex`,
`paper/main_fgcs.pdf`, `paper/submission_forms/cover_letter_fgcs.txt`,
`paper/FGCS_AUDIT.md` (pre-edit audit), this file. Nothing was committed, pushed,
or rewritten in git; `main_cose.tex`, `main_jisa.tex`, `main_cn.tex` and
`main_jss.tex` are untouched.

## Scope verdict

**Legitimate fit, with one honest weakness.**

The fit rests on content that already existed and is now foregrounded rather than
invented: the accounting lifecycle is distributed state shared across an
authorization path, an execution path, and a settlement path; B0 is a lost update
in the sense of the isolation-level literature the paper already cites; the
asynchronous-settlement result is a statement about staleness between
authorization and durable commitment, with no reference to inference at all. LLM
inference is the workload, not the subject. The abstract, introduction,
contribution list, taxonomy discussion and conclusion now say this directly.

The weakness is that "distributed" in this paper means processes and containers on
one host, communicating over loopback, with settlement separated by an injected
delay rather than a network path. That is stated in a limitation paragraph of its
own (Section 13, "Distribution") and repeated in the cover letter, because an FGCS
reviewer will reach for it first and should find it already conceded rather than
buried.

## Scientific-claim audit

- Grep over the FGCS source for "first," "novel," "new attack," "real-world
  vulnerability," "commercial provider," "production," "guarantee(s/d)," "prove(s),"
  "secure," "general," "all," "always," "no prior work," "practical," "realistic,"
  "state-of-the-art," "production-ready," "formally proven," "proven secure."
- Every hit was read in context. All are ordinals ("First, the standalone
  tokenizer"), correctly hedged non-claims ("No new attack primitive is claimed"),
  formally scoped statements ("conditions sufficient... to guarantee Equation (1)",
  a statement about the model, not the world), or explicit negations ("no
  commercial provider was tested"; "Nothing here shows that a production
  implementation is safe"; "no claim is made about physically distributed or
  wide-area behaviour").
- Two claims introduced during this pass were downgraded before compiling:
  "widely deployed gateway" became "independently developed gateway" (deployment
  scale is not something we can establish), and "independently written
  production-intent code" became "independently written gateway code" (we cannot
  establish those projects' deployment intent).
- No pre-existing claim required downgrading. This matches the result of the same
  sweep run for the CN and JSS versions.

## Numerical-consistency audit

Programmatic comparison of `main_fgcs.tex` against `main_cn.tex` (the pre-JSS
scientific baseline) and `main_jss.tex`:

- Numeric tokens present in CN but missing from FGCS: **none**.
- Numeric tokens present in JSS but missing from FGCS: **none**.
- New numeric tokens in FGCS: only the new evidence-table and pricing-table
  content (issue numbers 14457, 1148, 2179, 5235, 247; list prices 2, 1, 4, 0.20,
  0.10, 10, 5, 20, 0.05; the reported 254,347 figure; column widths; the access
  date). No measured value changed.
- All 3 equations, all 6 figures, and all CN-era tables are byte-identical.
- All 26 original CN bibliography entries are preserved verbatim.
- Headline values verified present in the compiled PDF: 58.3, 69.0, 27,526, 0.099,
  2.871, 4.851, 0.741.

## Reproducibility status

**Artifact-consistency: PASS. Full experimental re-execution: NOT PERFORMED in
this pass, and not claimed.**

- `paper/claim_evidence_matrix.csv` holds 44 claims, each mapped to a generating
  script and a result file, each marked VERIFIED. Classifications: 30 DIRECTLY
  MEASURED, 4 MODEL-CHECKED, 4 INFERRED, 2 ANALYTICALLY DERIVED, 2
  LITERATURE-SUPPORTED, 1 HYPOTHESIS (which is itself a negative statement, "results
  do not generalize to commercial providers"), 1 WITHDRAWN (detectability).
- Every referenced source and result path in that ledger resolves to a file that
  exists in the working tree (87 paths checked; the three initially flagged as
  missing were artifacts of my path-splitting and were confirmed present:
  `experiments/summarize_generality.py`, `app/m_routes.py`, `app/main.py`).
- Each headline number was located in the raw/processed result files independently
  of the manuscript: 0.583 (22 files), 0.690 (16), 27,526 (2), 0.099 (15), 2.871
  (11), 4.851 (10), 0.741 (14). 83 result files scanned.
- Not done: re-running the Docker Compose campaign end to end from a clean clone.
  That requires PostgreSQL, Redis, llama.cpp and hours of runtime, and was not
  performed in this session. The existing artifact and ledger are what support the
  reproducibility claim; the manuscript does not claim a fresh re-execution.
- Repository state at time of audit: `HEAD = b60c37e`, tags `v1.0.0` and `v1.0.1`,
  working tree clean except the new untracked FGCS files. The manuscript cites tag
  `v1.0.1` and Zenodo concept DOI `10.5281/zenodo.22085827`, both unchanged.

## Citation audit

- 83 bibliography entries (JSS had 82).
- Added (4): `litellm14457`, `opengate1148`, `cliproxy2179`, `anthropicpricing`.
  The three GitHub issues were verified by fetching and reading the actual issue
  pages on 23 September 2026, not by trusting search-engine summaries; title,
  status (open/fixed/closed), date and the one quoted figure were each confirmed
  against the page. The pricing entry was verified by fetching Anthropic's own
  pricing page directly.
- Removed (3): `amershi`, `fan`, `hou`, the software-engineering-for-AI references
  added for JSS. They were cited only in a subsection that served JSS scope and
  would read as padding at FGCS; the subsection was removed with them.
- Uncited bibliography entries: **0**. Undefined citations: **0**. Duplicate keys:
  **0**. Unresolved references or citations in the compiled PDF: **0**.
- The 56 references added during the JSS pass, each previously verified against
  Crossref or DataCite metadata, are retained; the majority (transactions,
  consistency, isolation levels, formal methods, cloud computing, fault injection)
  are directly on-scope for FGCS.

## Artifact status

Unchanged and untouched by this pass. Public repository plus Zenodo concept DOI
`10.5281/zenodo.22085827`; manuscript reports tag `v1.0.1`. No new experiment, data
file, figure, or table of results was generated, so nothing needs re-archiving.

## Reviewer attack test

**Reviewer A, FGCS editor: "Why here and not a security or software-engineering
journal?"** Because the result that does the work is about where economic
commitment sits relative to authorization in a multi-component service, and it is
demonstrated by an experiment with no concurrency at all. Sections 12.3 and 9 state
the condition without reference to language models. The security framing is the
threat model, not the contribution. This answer is now visible in the abstract,
the introduction's research question, the contribution list, and the conclusion;
previously it was implicit and had to be inferred from Section 12.

**Reviewer B, distributed systems: "Where is the distributed-systems
contribution?"** Three things, stated at their real strength: a lifecycle model
that localizes three failure modes to a shared-state transition, a terminal path,
and a data-authority boundary; an exhaustive TLC result that reservation and
abort-safe finalization are orthogonal, which is a statement about which
invariants a settlement protocol preserves; and the deferred-settlement result
showing that atomicity on the settlement path does not prevent over-serving if it
lands after the next authorization has read the balance. What the paper does *not*
contribute is anything about replication, consensus, partition tolerance, or
scale, and Section 13 now says so in a dedicated paragraph rather than leaving it
to be discovered.

**Reviewer C, security: "Is the threat model credible?"** The adversary is a
legitimate, authenticated client with six enumerated capabilities and six
enumerated non-capabilities, all exercised by the harness. Every manipulation is
graded by the knowledge it requires (K0/K1/K2), and the headline M2 result rests on
a K0 manipulation that needs nothing but the client's own view. The two non-K0
manipulations are labelled and excluded from the main claim. The provider is
honest by assumption, which is what makes the results attributable to accounting
design rather than compromise. No change was required.

**Reviewer D, formal methods: "Does the TLA+ analysis establish what is claimed?"**
The paper uses three labels and does not interchange them: model-checked, formally
argued, empirically verified. It states that the model is finite (two to three
requests, two value chunks, unit pricing), that only safety is checked, that no
liveness or inductive result is claimed, that there is no mechanized refinement
proof, and that the asynchronous family lies outside the model entirely and is
labelled empirical only. It also reports that the first specification was wrong and
was corrected, which is the failure mode a formal-methods reviewer looks for. The
one thing a hostile reviewer can still say is that agreement between model and
implementation is argued case by case rather than proved; the paper already says
exactly that, in those words. No change was required.

**Reviewer E, experimental methodology: "Could these be artifacts of a toy
implementation?"** This is the objection the paper was built to survive: the
generator is replaced by third-party serving code (llama.cpp with a real subword
tokenizer and real SSE streaming) across 12 M1 and 48 M2 cells with no safety
disagreements; the deployment is varied across three topologies (96 cells, no
mismatches); the storage layer is varied across two accounting backends, with an
honest note that only eight of the 17 comparison cells genuinely exercised both;
integrity gates are validated by 12 fault injections; and an independent checker
that imports nothing from the project reproduces every reported quantity. The
residual, which no amount of writing fixes, is that all of this runs on one host.
That now has its own limitation paragraph. The new Section 3.10 evidence table
also answers a weaker form of the objection: the same architectural gap is
documented in five independently written gateways, so the failure modes are not
peculiar to our code.

## Remaining limitations

Unchanged from the CN/JSS versions, plus one sharpened:

1. Finite formal model; safety only; no liveness, no inductive or parameterized
   result, no refinement proof.
2. Asynchronous settlement measured but not formally modelled.
3. Reconciliation delay injected, not observed in production.
4. **Separation between authorization and settlement is temporal, not physical: one
   host, loopback, no two-machine replication.** (Now its own limitation paragraph.)
5. One serving stack, one small CPU model, one prompt family.
6. B0's storage independence untested (frozen debit module predates the pluggable
   backends).
7. Synthetic pricing tiers; the new pricing table is context from one provider's
   published list prices, not a measurement.
8. No commercial provider tested; detectability claim withdrawn and documented.

## Final submission blockers

None that are scientific. Three procedural items for the author, listed in the
chat report accompanying this file, concern the Guide for Authors limits I could
not verify by direct fetch, the co-author's consent and ORCID, and the declaration
of interests form. They are administrative, not blockers to the manuscript's
correctness.
