# TAISAP submission preflight (2026-11-07)

Status: **CONDITIONAL READY — REQUIRES AUTHOR ACTION**. This is a local, non-submitted
package. No venue submission, upload, or external contact was performed.

## Package contents

- `submission_package/named/`: named upgrade source, bibliography, BBL, PDF, and figure assets.
- `submission_package/anonymous/`: double-anonymous source, bibliography, BBL, PDF, and figure assets.
- Both PDFs were rebuilt with Tectonic from the selected upgrade source and have 33 pages.
- The named source contains the verified Hardik ORCID `0009-0001-1642-6669`, Natasha Kaila's
  supplied ORCID `0009-0006-4252-9705`, and six ACM figure-description blocks.
- The bibliography resolves to 87 entries with no `[?]` or `(?)` markers in either PDF.

## Anonymity checks

The anonymous source uses `acmart` anonymous mode, replaces author metadata with
`Anonymous Authors`, removes emails and ORCID metadata, and removes repository/Zenodo
identifiers from the data-availability section. The anonymous source and rendered PDF were
scanned for author names, affiliations, email domains, and artifact identifiers.

## Evidence and reproducibility

The package is derived from the verified Task 8 manuscript rebuild. It carries the exact
selected `.tex`, matching `.bib`/`.bbl`, and the figure directories needed to reproduce the
figures. Historical `paper/taisap_submission/` artifacts were not overwritten.

## Remaining blockers

1. **REQUIRES AUTHOR ACTION — exclusivity/coauthor confirmation:** confirm all authors approve
   the author order, manuscript contents, and exclusive submission to the selected venue.
2. **REQUIRES AUTHOR ACTION — final venue policy check:** recheck current TAISAP metadata,
   anonymity, artifact, and ORCID requirements immediately before any submission. This report
   does not authorize submission.

## Local verification commands

```text
python -m pytest -q audit/taisap_upgrade/tests/test_submission_preflight.py
python -c "from pypdf import PdfReader; print(len(PdfReader('audit/taisap_upgrade/submission_package/named/main_taisap_upgrade.pdf').pages)); print(len(PdfReader('audit/taisap_upgrade/submission_package/anonymous/main_taisap_upgrade_anon.pdf').pages))"
```

Expected result: all preflight tests pass; both PDFs report 33 pages.
