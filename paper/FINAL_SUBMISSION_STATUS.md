# Final submission status — Computers & Security

```
MANUSCRIPT:            READY
FIGURES:               READY
DECLARATIONS:          READY
ARCHIVE PACKAGE:       READY
ZENODO DOI:            NOT MINTED
AUTHOR MATERIALS:      NOT SUPPLIED
JOURNAL SUBMISSION:    NOT SUBMITTED
```

**The paper has not been submitted. No Zenodo DOI exists. No author biography or
photograph has been supplied.** Everything that could be finished without a human or an
external service is finished.

---

## Verification results

```
scripts/check_cose_submission.py     31/31 PASS
abstract words                       248        (limit 250)
total words (body + references)      10,064     (limit 12,000)
keywords                             9          (range 5-10)
references                           26         (all 26 cited)
in-text citations                    49
figures                              6          (all cited)
tables                               6          (all cited)
compiled length                      25 pages, 0 blank
undefined references                 0
undefined citations                  0
duplicate labels                     0
overfull boxes                       2          (2.6 pt, 6.8 pt -- cosmetic)
```

## Scientific regression

```
regression_class6                    19/19 PASS
regression_m                         16/16 PASS
metamorphic                          22/22 PASS
recompute_all                        0 discrepancies
m2_independent_check                 0 mismatches
TLC                                  40/40, 27,526 distinct states, 0 disagreements
```

```
raw data changed:                    NO
processed results changed:           NO
tables or figures data changed:      NO
formal model changed:                NO
measured values changed:             NO
taxonomy changed:                    NO
claims added or strengthened:        NO
references added:                    NO
```

Every headline number in the manuscript reproduced exactly: B0 linear at \$0.099 per
additional concurrent request with $R^2 = 1.0000$; M1 request-level attack success 1.000
vulnerable / 0.000 safe; M2 leakage efficiency 58.3% controlled and 69.0% against the real
serving stack, 0.000 for every server-authoritative architecture.

## What changed in this packaging pass

Three defects, all editorial, none touching a measured value.

**Figure numbering was off by one in the submission artwork.** Figure 1 is the TikZ
request-lifecycle diagram drawn inline, so it had no file, and the raster figures shipped
as `Figure_1..Figure_5` while printing as Figure 2..Figure 6. Every separate artwork file
a reviewer opened would have been mislabelled. Figure 1 is now exported as a vector PDF
plus a 600 dpi PNG, the rasters are renumbered, and the mapping was verified against the
printed numbers in the compiled PDF rather than assumed.

**Five of twelve floats were never cited in the text** — the state-machine figure, the B0
figure, the M1 concurrency figure, the M2 heatmap, and the structural-distinction table.
Elsevier requires every float to be referred to. References were added at the points where
each was already under discussion, and `check_cose_submission.py` now enforces this as a
gate check, because an uncited float renders perfectly and so survives a visual pass.

**The data-availability statement pointed at tag `v1.0.0`** while the submission artifact
is `v1.0.1`. Corrected in both the manuscript and `paper/data_availability.md`, with the
relationship between the two tags stated explicitly and an explicit, clearly-marked
placeholder where the Zenodo DOI will go.

Two smaller corrections: a stale header comment describing the IEEE source as still
carrying an uncorrected B0 claim, fixed at v1.0.1; and "prove orthogonal" changed to "are
orthogonal" in the abstract, since this paper reserves "prove" for model-checked results
and M1 orthogonality is established analytically and by model checking rather than proved
in the sense the paper's own evidence labels use.

Nothing else in the manuscript's scientific content was touched.

## What remains, and who has to do it

These are the only open items. None can be closed from inside the repository, and none was
invented, approximated, or worked around.

| # | item | why it is open | blocking? |
|---|---|---|---|
| 1 | Zenodo DOI | needs the author's Zenodo account; package is built and waiting in `release/zenodo/` | yes |
| 2 | Author biography | needs facts only the author has | yes, if the submission system enforces the field |
| 3 | Author photograph | a portrait of a real person is not something to synthesise | yes, same condition |
| 4 | Author family name | the manuscript carries the single word "Hardik"; Editorial Manager and Zenodo both want given and family names separately, and a surname will not be inferred from an email address | yes |
| 5 | Corresponding-author address | personal vs. institutional; a deliberate choice, not a defect | no |
| 6 | Graphical abstract | optional per Elsevier; would require new artwork | no |
| 7 | `CITATION.cff` is behind | still says v1.0.0, no repository URL; should be fixed once, after item 4 | no |
| 8 | Human read-through | no automated pass substitutes for one | no, but recommended |

Exact remediation steps for each are in `paper/SUBMISSION_BLOCKERS.md`.

## Submission sequence

Once items 1-4 are closed:

1. Resolve the author name; update `paper/main_cose.tex`, `CITATION.cff`, and
   `release/zenodo/metadata.md` together.
2. Write `paper/author_bio.txt`; supply the photograph per
   `paper/AUTHOR_PHOTO_REQUIRED.md`.
3. Create the GitHub release for tag `v1.0.1`; deposit to Zenodo using
   `release/zenodo/metadata.md`; record the minted DOI.
4. Insert the DOI in `paper/main_cose.tex` and `paper/data_availability.md`, replacing
   `[ZENODO DOI TO BE INSERTED]`. Add it to `CITATION.cff`.
5. Recompile: `tectonic -X compile paper/main_cose.tex`.
6. Re-run `python scripts/check_cose_submission.py` — must stay 31/31.
7. Upload the files listed in `paper/FINAL_SUBMISSION_MANIFEST.md` §1 to Editorial
   Manager.

---

```
STATUS: SUBMISSION-READY EXCEPT FOR EXTERNAL AND HUMAN MATERIALS
NOT SUBMITTED. NO DOI. NO AUTHOR BIOGRAPHY. NO AUTHOR PHOTOGRAPH.
```
