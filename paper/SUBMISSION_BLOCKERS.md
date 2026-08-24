# Submission blockers

Concrete, unresolved items that must be closed before `paper/main_cose.tex` is actually
submitted to Computers & Security. Nothing below was fabricated to make this list look
shorter than it is.

## 1. Zenodo DOI still required before submission

`paper/main_cose.tex`'s Data Availability section currently references the GitHub
release directly and states that an archival Zenodo snapshot is intended. Elsevier and
most funders now expect a persistent dataset DOI, not just a GitHub URL. Action:

1. Connect the GitHub repository to Zenodo (https://zenodo.org/account/settings/github/).
2. Create a new GitHub release matching (or superseding) `v1.0.0` — Zenodo archives on
   release creation, not on existing tags, so a fresh release may be needed.
3. Zenodo mints a DOI. Insert it in place of `[ZENODO DOI TO BE INSERTED]` in both
   `paper/main_cose.tex` and `paper/data_availability.md`.

**Status: BLOCKING.** Do not submit with a placeholder DOI string in the manuscript.

## 2. Corresponding-author email choice

`paper/main_cose.tex` currently lists `hardikahlawat13@gmail.com` (personal address, as
supplied directly for this submission). The author's own resume lists an institutional
address, `hardik24a12res263@iitp.ac.in`. Academic corresponding-author addresses are
conventionally institutional. This is a judgment call for the author, not something this
conversion should decide unilaterally — flagged in `submission_metadata.md` as well.

**Status: non-blocking, but should be a deliberate choice before submission**, not an
oversight.

## 3. Author biography and photograph

Computers & Security's author guide requests a short biography and a passport-style
photograph per author. `paper/author_bio.txt` is a TODO placeholder — no biography was
invented. The author must supply real biographical text (education, current
affiliation, research interests) and a photograph before submission.

**Status: BLOCKING** if the journal's current submission system enforces this field;
check the live author guide, since requirements can change.

## 4. Graphical abstract

Optional per Elsevier's own guidance and left unmade here, since assembling one would
require new artwork beyond what exists in the repository (see
`submission_metadata.md`). Not a blocker, but worth deciding deliberately.

## 5. Residual B0 framing inconsistency in the IEEE manuscript — RESOLVED at v1.0.1

**Status: RESOLVED.** `paper/accounting_state_model_ieee.tex` (included by
`main_ieee.tex` via `\input`) previously stated unconditionally that B0 "needs
concurrency: yes" and that B0 leakage is "created by concurrency," contradicting the
corrected condition stated everywhere else in the same manuscript. It was corrected at
v1.0.1, together with two related fixes giving M1's and M2's concurrency independence
their correct epistemic status (measured for M1, analytic for M2).

No raw data, measured value, or experimental result changed. The Elsevier manuscript was
already correct and is byte-identical across the fix. v1.0.1 supersedes v1.0.0 for
submission use; v1.0.0 is preserved immutable for historical reproducibility.

## 6. Manuscript still needs a human read-through

This conversion preserved every scientific claim, statistic, and citation from the
frozen IEEE source, adapted section numbering and citation style for Elsevier, and fixed
the one internal contradiction described in item 5 (COSE version only). It has not been
read by a human co-author or a native-English copyeditor. Recommended before submission,
not because errors are known to exist, but because no automated pass substitutes for a
human final read.
