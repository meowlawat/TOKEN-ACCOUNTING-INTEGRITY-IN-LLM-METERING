# Double-anonymous upload package (2026-11-07)

The journal's supplied upload instructions require the anonymous PDF as the first file,
designated **Main Document (PDF)**, followed by the unopened source ZIP designated
**Source Document**. No upload or external submission was performed.

## Upload files

1. `upload_ready/Main_Document_Anonymous.pdf` — 2,370,459 bytes, 32 pages.
2. `upload_ready/Source_Document.zip` — 2,774,851 bytes (2.65 MiB), below the 100 MiB
   supplemental-file threshold.

The ZIP contains only the anonymous `main.tex`, matching `.bib` and `.bbl`, and the figure
assets required to compile it. Build intermediates (`.aux`, `.log`, `.out`, and `.blg`) are
excluded.

## Anonymity verification

- The main PDF has no `/Author` metadata field.
- Extracted PDF text contains no author names, affiliations, email domains, ORCIDs,
  repository owner, or Zenodo identifiers.
- Every ZIP member was scanned, including binary assets, for the same identifiers; no
  match was found.
- PNG metadata contains only tool/version and resolution fields. The one included figure
  PDF contains creator/producer/date metadata but no author identity.
- The source retains ACM anonymous mode and omits author contributions and public artifact
  identifiers for review.

## Clean extraction build

The ZIP was extracted into `upload_ready/verification/` and compiled from its own contents:

```text
C:\Users\hardi\bin\tectonic.exe --keep-logs --keep-intermediates --outdir ..\build main.tex
```

Result: exit 0; 32 pages; no unresolved `[?]` or `(?)` citation markers; no forbidden
identity strings in the rebuilt PDF.

## Submission sequence

1. Upload `Main_Document_Anonymous.pdf` first as **Main Document (PDF)**.
2. Upload `Source_Document.zip` without unpacking as **Source Document**.
3. Open the generated PDF in the portal and inspect it before selecting **Save and
   Continue**.

The final portal action remains an author-controlled step.
