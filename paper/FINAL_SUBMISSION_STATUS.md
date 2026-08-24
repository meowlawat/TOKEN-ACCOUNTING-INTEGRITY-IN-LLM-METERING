# Final submission status — Computers & Security

```
Zenodo DOI:                 10.5281/zenodo.22086254   (v1.0.2, complete artifact)
PDF:                        PASS
Abstract:                   248 words         (limit 250)
Article:                    10,061 words      (limit 12,000)
Figures:                    6/6 cited
Tables:                     6/6 cited
Undefined citations:        0
Undefined references:       0
Duplicate labels:           0
DOI check:                  PASS
Submission checker:         PASS  (36/36)
Git:                        CLEAN
Scientific files changed:   NO
Final manuscript:           READY
```

**FINAL VERDICT: READY FOR EDITORIAL MANAGER.**

**The paper has not been submitted.** Nothing in this repository submits it. The portal
work is yours; `paper/EDITORIAL_MANAGER_FINAL_CHECKLIST.md` is the field-by-field guide.

---

## Zenodo — verified against the live record

The v1.0.2 deposition is public, typed **Dataset**, and holds the complete artifact.

```
Version DOI    10.5281/zenodo.22086254     cited in the manuscript
Concept DOI    10.5281/zenodo.22085827     resolves to the latest version
Superseded     10.5281/zenodo.22085828     v1.0.1, manuscript only — not cited anywhere
```

The deposited archive was checked byte-for-byte against the local build rather than
assumed:

```
size    8,092,411 bytes   local == Zenodo
MD5     c872a3904d5414c69ce8ff0d27b0aee2   local == Zenodo
SHA-256 d8147287e9a26bcf2e4e50d198c634e3a095ca3fd6a6bbdcd5db51fdd24971bc
        matches release/zenodo/SHA256SUMS.txt
```

A reviewer who downloads the deposit gets exactly what this repository produced, and the
published checksum verifies it.

The DOI propagated to all five files that carry it — `paper/main_cose.tex`,
`CITATION.cff`, `README.md`, `paper/data_availability.md`,
`paper/submission_metadata.md`. The superseded v1.0.1 DOI appears nowhere in the
manuscript, and two new gate checks now enforce that: the active DOI must be
`22086254`, and `22085828` must be absent.

## Manuscript

```
pages                 25, 0 blank
embedded images       5
fatal LaTeX errors    0
undefined references  0
undefined citations   0
multiply-defined      0
overfull hboxes       2   (2.61 pt and 6.84 pt — cosmetically negligible)
overfull vboxes       0
```

Visually inspected in the rebuilt PDF: title page with the mononym and both affiliations;
abstract; the nine keywords; the B0 baseline result; M1 orthogonality; M2 usage authority;
the formal-verification matrix; the asynchronous B0 result; the defense-overhead table;
the conclusion; the references; and all six declarations.

Key reported values confirmed present and unchanged: 58.3% and 69.0% M2 leakage, B0 slope
0.099 with $R^2 = 1.0000$, and "ten configurations and four invariants give 40 independent
runs over 27,526 distinct states."

## Science untouched

```
raw data changed:            NO
processed results changed:   NO
tables / figures changed:    NO
formal model changed:        NO
measured values changed:     NO
claims added or altered:     NO
experiments run:             NONE
```

`git diff` against tag `v1.0.1` over `results/`, `formal/`, `audit/`, `experiments/`,
`attacks/`, `defenses/`, `app/`, and `benchmarks/` is empty.

## What changed in this pass

Three things, none of them scientific.

**The DOI was verified rather than trusted.** All five files carry `22086254`; the live
Zenodo record was fetched and confirmed public, typed Dataset, and holding the archive; and
the deposited bytes were hashed and compared against the local build.

**A stale comment in `CITATION.cff`** still described the v1.0.1 DOI as the version-specific
one. Corrected to name v1.0.2 as active and v1.0.1 as superseded.

**The declaration of interests carried a date typo.** It had been filled in as
`25/08/2006` — twenty years early, predating every reference in the paper. Corrected to
`25/08/2026`. The document was revalidated afterwards: zip integrity OK, all 14 XML parts
well-formed. Nothing else in it was touched; the checkbox, name, and affiliations are as
they were.

## Author materials

```
name                  Hardik   (mononym — no surname anywhere in the repository)
ORCID                 0009-0001-1642-6669
photograph            paper/submission_forms/author_photo.jpg
                      1200x1600, 300 dpi, JPEG, 541,309 bytes — unmodified this pass
biography             paper/author_bio.txt — 85 words, needs your read-through
declaration           paper/submission_forms/declaration_of_interests.docx — dated 25/08/2026
```

## Remaining items — none block submission

1. **Read `paper/author_bio.txt`.** It was drafted from your resume, GitHub profile, and
   ORCID record, with every claim traced to its source. It is a biography of a real person
   and should not go out unread.
2. **Populate the ORCID record.** `0009-0001-1642-6669` resolves to a page with a given
   name and nothing else. An ORCID that resolves to a blank page is a weaker signal than
   none. Add the affiliations and the two accepted papers.
3. **Two Zenodo metadata fixes**, both editable without a new version:
   - the licence reads `cc-by-4.0` while the archive ships an MIT `LICENSE` file — the
     record contradicts its own contents;
   - the creator name is stored as `., hardik`, so the record cites as `. , . hardik .`.
4. **Verify reviewer contact details** before entering them. They were deliberately left
   blank.
5. **A human read-through.** No automated pass substitutes for one.

Items 1–4 are each a few minutes. None of them changes the manuscript.

---

```
MANUSCRIPT READY — NOT SUBMITTED
```
