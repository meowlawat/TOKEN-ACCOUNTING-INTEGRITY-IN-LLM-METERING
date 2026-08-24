# Final submission status — Computers & Security

```
MANUSCRIPT:            READY
FIGURES:               READY
DECLARATIONS:          READY
ARCHIVE PACKAGE:       READY
SUBMISSION FORMS:      READY
AUTHOR IDENTITY:       RESOLVED
AUTHOR BIOGRAPHY:      DRAFTED, needs author review
ZENODO DOI:            MINTED, record needs completing
AUTHOR PHOTOGRAPH:     READY
JOURNAL SUBMISSION:    NOT SUBMITTED
```

**The paper has not been submitted.** One blocking item remains, and it is on Zenodo
rather than in this repository: the deposited record holds the manuscript, not the
artifact archive. Everything else is done.

---

## Verification results

```
scripts/check_cose_submission.py     34/34 PASS
abstract words                       248        (limit 250)
total words (body + references)      10,052     (limit 12,000)
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

The generative-AI declaration was rewritten to Elsevier's own heading and template
wording — "During the preparation of this work the author used [tool] in order to
[reason]. After using this tool, the author reviewed and edited the content as needed and
takes full responsibility for the content of the publication." The previous version was a
six-line custom paragraph. The declaration itself is required by Elsevier policy and was
not removed; the replacement is shorter, standard, and is what the journal asks to see.
The gate now checks both the exact heading and that the tool is named and responsibility
accepted (32 checks, was 31).

The title page now carries both affiliations and both corresponding-author addresses,
institutional first, following the author's decisions once their resume and profiles were
available. The author name stays the mononym "Hardik", also by the author's decision, and
is now expressed consistently in the manuscript, `CITATION.cff`, and the Zenodo metadata.

Nothing else in the manuscript's scientific content was touched.

## What remains, and who has to do it

These are the only open items. None can be closed from inside the repository, and none was
invented, approximated, or worked around.

| # | item | why it is open | blocking? |
|---|---|---|---|
| 1 | Zenodo record holds the manuscript, not the artifact | the 8.1 MB archive was never uploaded; a reviewer following the DOI expecting data finds a PDF. Fix is one *New version* publish — every field prepared in `release/zenodo/metadata_v1.0.2.md`, and `scripts/set_zenodo_doi.py` installs the resulting DOI in one pass | yes |
| 2 | Author biography | drafted in `paper/author_bio.txt` from verified sources; needs the author's review, not writing | yes, until reviewed |
| 3 | ~~Author photograph~~ | supplied — `paper/submission_forms/author_photo.jpg`, 1200x1600 @ 300 dpi | no |
| 4 | ORCID record is near-empty | the ID `0009-0001-1642-6669` is verified and recorded; the record has no affiliations or works | no, strongly recommended |
| 5 | Graphical abstract | optional per Elsevier; would require new artwork | no |
| 6 | Human read-through | no automated pass substitutes for one | no, but recommended |

**Resolved in this pass**, from the author's resume, GitHub profile, and ORCID record:
the author name (mononym "Hardik", by the author's decision), the affiliations (IIT Patna
and VIPS — dual enrolment, both now on the title page), the corresponding-author address
(both, institutional first), and `CITATION.cff` (v1.0.1, repository URL, ORCID,
affiliation, valid YAML).

Exact remediation steps for each are in `paper/SUBMISSION_BLOCKERS.md`.

## Submission sequence

Once items 1-4 are closed:

1. Fix the Zenodo record — upload `release/zenodo/token-accounting-integrity-v1.0.1.zip`
   as a **New version**, set resource type to Dataset, set the licence to MIT, and repair
   the creator name and ORCID. Details in `paper/SUBMISSION_BLOCKERS.md` item 1. **No
   manuscript edit is needed afterwards**: the paper cites the concept DOI, which follows
   the record forward.
2. Read and correct `paper/author_bio.txt`.
3. Supply the author photograph per `paper/AUTHOR_PHOTO_REQUIRED.md`.
4. Populate the ORCID record (affiliations, the two accepted papers).
5. Upload the files listed in `paper/FINAL_SUBMISSION_MANIFEST.md` §1 to Editorial
   Manager, entering the mononym in the last-name field.

The manuscript itself needs no further edits. It compiles at 34/34 with the DOI in place;
recompile only if you change something.

---

```
STATUS: SUBMISSION-READY EXCEPT FOR EXTERNAL AND HUMAN MATERIALS
NOT SUBMITTED. NO DOI. NO AUTHOR BIOGRAPHY. NO AUTHOR PHOTOGRAPH.
```
