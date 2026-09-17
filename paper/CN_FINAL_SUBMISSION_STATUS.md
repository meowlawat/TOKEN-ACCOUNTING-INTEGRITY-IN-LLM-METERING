# Computer Networks — final submission status

Prepared, **not submitted**. This file records the state of the CN package as of this
pass, verified against the actual repository — nothing below is asserted without a
corresponding check having been run.

```
CN manuscript:                      PASS
CN PDF:                             PASS
Cover letter:                       PASS
Abstract:                           PASS   (248 words; CN limit 250)
Keywords:                           PASS   (6 keywords; CN limit 6)
Figures:                            PASS   (6/6 referenced)
Tables:                             PASS   (6/6 referenced)
References:                         PASS   (26 bibliography entries, all cited; 0 undefined)
Author metadata:                    PASS   (Hardik, mononym, no invented surname)
ORCID:                               N/A   (not printed in manuscript body; entered at
                                            Editorial Manager submission — 0009-0001-1642-6669)
Data availability:                  PASS   (Zenodo concept DOI 10.5281/zenodo.22085827;
                                            superseded version DOI 22085828 absent)
Scientific results unchanged:       PASS   (verified: pagination-normalised PDF diff
                                            against main_jisa.pdf, similarity 0.9155,
                                            every non-equal region is a listed edit or a
                                            reflow of identical text; all 10 headline
                                            values re-confirmed present)
C&S/JISA artifacts untouched:       PASS   (git diff --stat against last commit: empty
                                            for main_cose.tex/.pdf and main_jisa.tex/.pdf)
Git history untouched:              PASS   (no reset, no checkout --, no rewrite; only
                                            new untracked files added, nothing committed
                                            yet by this pass)
Zenodo untouched:                   PASS   (no API call made, no record modified,
                                            no version published)
```

**Full checker output: 36/36 checks passed.** (`python scripts/check_cn_submission.py`)

---

## Remaining blockers

None that block preparing the package further. Two items require the author's decision,
not more automated work:

1. **JISA decision detail is unverified.** The cover letter states only that the
   manuscript "is no longer under consideration" at JISA, without a reason, date, or
   manuscript number, because none exists in this repository. If you supply the same
   detail level given for the C&S decision, I will fold it in with the same accuracy
   standard. See `paper/submission_forms/CN_SCOPE_NOTES.md` §6.
2. **Editorial Manager's own submission questionnaire** will likely ask whether this
   manuscript was previously submitted to another Elsevier journal. Since JISA and C&S
   are both Elsevier journals, the accurate answer is yes to both, independent of what the
   cover-letter prose says. This is a form-filling fact, not a manuscript-content one, and
   is called out here so it isn't missed at submission time.

Everything else — manuscript, PDF, cover letter, scope notes, changelog, and the
submission gate — is complete and passing.
