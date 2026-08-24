# Final submission manifest — Computers & Security

Everything that exists, what it is for, and whether it is ready. This is the packing
list; `paper/FINAL_SUBMISSION_STATUS.md` is the verdict.

Verified state at the time of writing: `scripts/check_cose_submission.py` 34/34,
`scripts/count_cose_metrics.py` abstract 248 / total 10,025, PDF 25 pages 0 blank, 0
undefined references, 0 undefined citations, 0 duplicate labels, 2 cosmetic overfull
boxes (2.6 pt and 6.8 pt).

---

## 1. Uploaded to the journal

| file | role | status |
|---|---|---|
| `paper/main_cose.pdf` | manuscript, 25 pages | READY |
| `paper/main_cose.tex` | elsarticle source, self-contained (no `\input`) | READY |
| `paper/highlights_upload.txt` | 5 highlights, 64-68 chars each (limit 85) | READY |
| `paper/figures_cose/Figure_1.pdf` | Figure 1, vector — preferred for line art | READY |
| `paper/figures_cose/Figure_1.png` | Figure 1, 600 dpi raster fallback | READY |
| `paper/figures_cose/Figure_2.png` | Figure 2, B0 baseline, 600 dpi | READY |
| `paper/figures_cose/Figure_3.png` | Figure 3, M1 abort curve, 600 dpi | READY |
| `paper/figures_cose/Figure_4.png` | Figure 4, M1 concurrency, 600 dpi | READY |
| `paper/figures_cose/Figure_5.png` | Figure 5, M2 efficiency heatmap, 600 dpi | READY |
| `paper/figures_cose/Figure_6.png` | Figure 6, tokenizer latency, 600 dpi | READY |
| `paper/submission_forms/cover_letter.txt` | cover letter, paste-ready plain text | READY |
| `paper/submission_forms/declaration_of_interests.docx` | Elsevier's form, completed and named | READY |
| `paper/submission_forms/suggested_reviewers.md` | 5 candidates from the reference list | READY |
| `paper/author_bio.txt` | 85-word biography, drafted from verified sources | **NEEDS AUTHOR REVIEW** |
| `paper/submission_forms/author_photo.jpg` | 1200x1600 @ 300 dpi, passport framing | READY |
| ORCID `0009-0001-1642-6669` | enter in Editorial Manager; record needs populating | READY |

Filenames match printed figure numbers exactly; this was verified against the compiled
PDF, not assumed. Figure 1 is drawn in TikZ inside the manuscript and exported separately
by `scripts/render_tikz_figure1.py`, which is why the raster series starts at Figure 2.

## 2. Declarations, inside the manuscript

| declaration | page | content |
|---|---|---|
| Acknowledgements | 23 | none apply; stated rather than omitted |
| CRediT | 23 | single author, 11 roles enumerated |
| Competing interest | 24 | none declared |
| Funding | 24 | no specific grant |
| Declaration of generative AI and AI-assisted technologies in the writing process | 24 | Elsevier's own heading and template wording; tool named, responsibility accepted |
| Data availability | 24 | GitHub tag `v1.0.1`, explicit Zenodo DOI placeholder |

## 3. Archival deposition — prepared, not published

`release/zenodo/`

| file | what it is |
|---|---|
| `token-accounting-integrity-v1.0.1.zip` | 331 files, ~8 MB, built from the tracked tree at tag `v1.0.1` |
| `SHA256SUMS.txt` | checksum of that archive |
| `ARCHIVE_CONTENTS.md` | full file list, plus what was excluded and why |
| `metadata.md` | every Zenodo form field, filled in |

The archive is built by `scripts/build_zenodo_archive.py` from `git ls-files` at HEAD, so
`.gitignore` remains the single source of truth for exclusions and the archive cannot
drift from the repository's own rules. It refuses to run against a dirty tree, and writes
deterministic entries so rebuilding from the same commit reproduces the checksum exactly.

Contents confirmed to include `results/raw/` (35), `results/processed/` (18),
`results/tables/` (67), `results/figures/` (9), the TLA+ model and TLC driver, the attack
harnesses, the defense implementations, the audit code, both manuscripts, and the
reproduction scripts. Confirmed to contain no key material, credentials, model weights,
tokenizer cache, Docker volumes, LaTeX intermediates, OS metadata, or absolute local
paths.

**DOI minted:** concept `10.5281/zenodo.22085827` (cited in the paper, always resolves to
the latest version), version `10.5281/zenodo.22085828`, record
https://zenodo.org/records/22085828.

**The record does not yet contain this archive** — only the manuscript was deposited.
Uploading the zip as a new Zenodo version is blocker 1 and must happen before submission,
or the data-availability statement is false. `SHA256SUMS.txt` and `ARCHIVE_CONTENTS.md`
are written after the archive, so they are not inside it; that is intended, since they
describe it.

## 4. Author-facing working files, not for upload

`paper/submission_metadata.md`, `paper/SUBMISSION_BLOCKERS.md`,
`paper/data_availability.md`, `paper/AUTHOR_PHOTO_REQUIRED.md`,
`paper/COSE_SUBMISSION_READINESS.md`, `paper/FINAL_COSE_SUBMISSION_STATUS.md`,
`paper/FINAL_SUBMISSION_STATUS.md`, and this file. Also `paper/highlights.txt`, the
annotated version — upload `highlights_upload.txt` instead.

## 5. Verification tooling

| script | what it checks |
|---|---|
| `scripts/check_cose_submission.py` | 34 fail-closed submission checks |
| `scripts/count_cose_metrics.py` | word, section, float, and citation counts |
| `scripts/check_float_citations.py` | every float is referred to in the text |
| `scripts/build_zenodo_archive.py` | deposition archive and checksum |
| `scripts/render_cose_figures.py` | 600 dpi artwork from frozen plot code |
| `scripts/render_tikz_figure1.py` | Figure 1 vector + raster export |
| `scripts/prepare_author_photo.py` | author photograph framing and format |

## 6. Scientific regressions, all re-run for this package

```
regression_class6      19/19 PASS
regression_m           16/16 PASS
metamorphic            22/22 PASS
recompute_all          0 discrepancies over 420 B0 trials + M1/M2 corpus
m2_independent_check   0 mismatches
TLC                    40/40 expectations, 27,526 distinct states, 0 disagreements
```

`git diff` over `results/raw/`, `results/processed/`, `results/tables/`,
`results/figures/`, `formal/`, and `audit/` is empty. The only byte that moved in a
re-run was wall-clock timing inside `results/formal/model_check_results.json`; every
state count and every verdict was identical, and that file was reverted so the frozen
artifact stays byte-identical.

## 7. What is genuinely not done

One blocking item:

1. **The Zenodo record holds the manuscript, not the artifact.** The DOI exists and is
   cited in the paper, but the 8.1 MB archive was never uploaded, so a reviewer following
   the DOI expecting raw data finds a PDF. Needs a *New version* upload plus three
   metadata fixes. Because the paper cites the concept DOI, fixing it requires no
   manuscript edit. Full steps in `paper/SUBMISSION_BLOCKERS.md` item 1.

Two that want the author's attention:

2. **Author biography** — drafted in `paper/author_bio.txt` from the author's resume,
   GitHub profile, and ORCID record, every claim traced to its source. Needs reading and
   correcting, not writing from scratch.
3. **ORCID record** — the ID is verified and recorded everywhere it belongs, but the
   record itself is near-empty. Ten minutes at orcid.org.

Resolved: the author name (mononym "Hardik"), the corresponding-author address (both,
institutional first), the affiliations (IIT Patna and VIPS, dual enrolment),
`CITATION.cff`, the Zenodo DOI, and the author photograph. The graphical abstract remains
deliberately absent — optional per Elsevier, and it would require new artwork.

Detail and exact remediation steps in `paper/SUBMISSION_BLOCKERS.md`.
