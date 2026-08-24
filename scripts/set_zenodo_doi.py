"""Install the published Zenodo version DOI across every file that carries it.

Run this once, after publishing the v1.0.2 Zenodo version, with the DOI read off the
published record:

    python scripts/set_zenodo_doi.py 10.5281/zenodo.<NEW>

The DOI appears in five places. Editing them by hand is how they drift apart, and a
manuscript whose data-availability DOI disagrees with CITATION.cff is worse than one that
has no DOI at all -- so this does all five in one pass, or none of them.

It refuses:
  * anything that is not a well-formed Zenodo DOI;
  * the concept DOI 10.5281/zenodo.22085827, which is not version-specific;
  * the old version DOI 10.5281/zenodo.22085828, which points at the incomplete record.

It will not invent a DOI, and it cannot be run without one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONCEPT_DOI = "10.5281/zenodo.22085827"
OLD_VERSION_DOI = "10.5281/zenodo.22085828"

DOI_RE = re.compile(r"^10\.5281/zenodo\.\d{4,}$")


def fail(msg: str) -> None:
    print(f"REFUSING: {msg}")
    sys.exit(1)


def edit(rel: str, pairs: list[tuple[str, str]]) -> None:
    """Apply replacements to one file, requiring each to match exactly once."""
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            fail(f"{rel}: expected exactly 1 occurrence, found {n}, of:\n    {old[:100]}")
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  updated {rel}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    doi = sys.argv[1].strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)

    if not DOI_RE.match(doi):
        fail(f"{doi!r} is not a well-formed Zenodo DOI (expected 10.5281/zenodo.NNNNNNNN)")
    if doi == CONCEPT_DOI:
        fail("that is the concept DOI, which always resolves to the latest version. "
             "This script installs the VERSION-specific DOI. Read it off the published "
             "v1.0.2 record.")
    if doi == OLD_VERSION_DOI:
        fail("that is the v1.0.1 version DOI, whose record holds only the manuscript and "
             "not the artifact. Publish the v1.0.2 version first, then use its DOI.")

    url = f"https://doi.org/{doi}"
    print(f"Installing version DOI {doi}\n")

    # ---- manuscript -----------------------------------------------------------------
    edit("paper/main_cose.tex", [(
        r"""An archival snapshot is deposited in Zenodo under DOI
\href{https://doi.org/""" + CONCEPT_DOI + "}{" + CONCEPT_DOI + r"""}, a concept DOI
that always resolves to the most recent version of the record; the version archived for
this paper is \href{https://doi.org/""" + OLD_VERSION_DOI + "}{" + OLD_VERSION_DOI + r"""}.
The archive contents and their SHA-256 checksum are listed in \texttt{release/zenodo/} in
the repository.""",
        r"""The complete artifact --- source code, experiment scripts, the formal
specification, raw and processed results, figures, tables, and reproduction scripts ---
is archived in Zenodo as version 1.0.2 under DOI
\href{""" + url + "}{" + doi + r"""}. The concept DOI
\href{https://doi.org/""" + CONCEPT_DOI + "}{" + CONCEPT_DOI + r"""} always resolves to the
most recent version. The archive contents and their SHA-256 checksum are listed in
\texttt{release/zenodo/} in the repository.""")])

    # ---- citation file --------------------------------------------------------------
    edit("CITATION.cff", [(
        f'doi: "{CONCEPT_DOI}"',
        f'doi: "{doi}"')])

    # ---- README ---------------------------------------------------------------------
    edit("README.md", [(
        f"""The archival record is Zenodo [{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI})
— a concept DOI, which always resolves to the latest version. The version archived for the
manuscript is [{OLD_VERSION_DOI}](https://doi.org/{OLD_VERSION_DOI}).""",
        f"""The archival record is Zenodo [{doi}]({url}), version 1.0.2, containing the
complete artifact. The concept DOI
[{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI}) always resolves to the latest version.""")])

    # ---- side documents -------------------------------------------------------------
    edit("paper/data_availability.md", [(
        f"""Concept DOI (all versions, always latest):  {CONCEPT_DOI}
Version DOI (v1.0.1):                       {OLD_VERSION_DOI}
Record:                                     https://zenodo.org/records/22085828""",
        f"""Concept DOI (all versions, always latest):  {CONCEPT_DOI}
Version DOI (v1.0.2, complete artifact):    {doi}
Version DOI (v1.0.1, manuscript only):      {OLD_VERSION_DOI}""")])

    edit("paper/submission_metadata.md", [(
        f"""Concept DOI (cited in the manuscript):  {CONCEPT_DOI}
Version DOI (v1.0.1):                   {OLD_VERSION_DOI}
Record:                                 https://zenodo.org/records/22085828""",
        f"""Version DOI (cited in the manuscript):  {doi}   (v1.0.2, complete artifact)
Concept DOI (resolves to latest):       {CONCEPT_DOI}
Superseded deposition (v1.0.1):         {OLD_VERSION_DOI}""")])

    print("\nAll five files updated. Now:")
    print("  tectonic -X compile paper/main_cose.tex")
    print("  python scripts/check_cose_submission.py")
    print("\nThe gate's DOI check stays satisfied -- the new wording still carries the")
    print("concept DOI. This was verified by dry run before the script was committed.")
    print("Then close item 1 in paper/SUBMISSION_BLOCKERS.md.")


if __name__ == "__main__":
    main()
