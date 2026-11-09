# Independent adversarial review (2026-11-07)

Two independent read-only reviews were performed after the submission package commit.

## Scientific review

- Claim ledger and manuscript remain evidence-bounded; no unsupported novelty or result claim
  was identified.
- The six-point asynchronous TLC result is correctly scoped as bounded/exhaustive model
  checking, not an implementation proof.
- The unexecuted 1,200-trial Docker fault matrix and absent independent second-host
  replication are explicitly disclosed.
- The full upgrade test suite passed: `37 passed`.

## Compliance/reproducibility review

- The rebuilt named PDF has 33 pages and the anonymous PDF has 32 pages; both contain 87
  bibliography entries.
- Neither PDF contains `[?]` or `(?)` citation markers.
- The anonymous source/PDF contain no author names, affiliations, emails, ORCID, GitHub
  identifiers, or Zenodo identifiers.
- Matching `.tex`, `.bib`, `.bbl`, and figure assets are present for both package variants.
- Only the inherited user edits (`paper/main_taisap.tex`, `paper/main_taisap_anon.tex`) and
  the user-provided `AGENTS.md` remain outside the committed upgrade work.

## Remaining blockers

These are administrative and require author action, not further autonomous research work:

1. Natasha Kaila's supplied ORCID is now recorded as `0009-0006-4252-9705`.
2. All authors must confirm author order, manuscript contents, and exclusive submission.
3. Current TAISAP policy must be rechecked immediately before any submission.

The package contains a harmless duplicate `results_figures/` copy in addition to the
correctly referenced `results/figures/` tree; it does not affect reproducibility or the
preflight checks.
