"""Remove the incorrect CVE citation and the wrong Kettle title, repository-wide.

Reference verification during the IEEE pass established two facts:

  * `CVE-2026-31873` is NOT the Tyk API Gateway quota race. Both the MITRE CVE Services
    record and NVD show it belongs to an unrelated Unhead URI-scheme sanitization bypass.
    The citation was wrong wherever it appeared.
  * Kettle's 2023 PortSwigger research is titled "Smashing the state machine: the true
    potential of web race conditions", not "The single-packet attack: ...". The
    single-packet attack is a *technique described in* that article, so prose referring to
    the technique is fine; prose presenting it as the article's title is not.

The IEEE manuscript was already corrected. This script propagates the correction to the
rest of the repository so a reader cannot find the wrong citation still standing somewhere.

Files that *document* the correction -- the audit reports and the reference audit -- are
deliberately untouched: they are the record of the mistake, not a repetition of it.

Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files whose job is to record the correction; leaving them alone is the point.
KEEP_AS_HISTORY = {
    "paper/IEEE_FINALIZATION_REPORT.md",
    "paper/ieee_reference_audit.md",
    "AUDIT_REPORT.md",
    "audit/confirmation_bias.md",
    "audit/fix_baseline.md",
    "RELEASE_FREEZE.md",
    "RELEASE_NOTES.md",
    "GITHUB_RELEASE_REPORT.md",
    "scripts/_fix_stale_citation.py",
    "scripts/audit_references.py",
}

KETTLE_OLD = "Kettle's single-packet attack"
KETTLE_NEW = "Kettle's work on web race conditions (which introduces the single-packet attack)"

EDITS: list[tuple[str, str, str]] = [
    # ---- the paper's original (pre-IEEE) manuscript ----------------------------
    ("paper/main.tex",
     r"are a classic web-race primitive with a recent CVE~\cite{kettle,cve2026}; and practitioner",
     r"are a classic web-race primitive~\cite{kettle}; and practitioner"),
    ("paper/main.tex",
     r"understood~\cite{kettle,cve2026}. What we found no prior study of, \emph{in our targeted",
     r"understood~\cite{kettle}. What we found no prior study of, \emph{in our targeted"),
    ("paper/main.tex",
     r"PR~\cite{aperture247}, and a CVE~\cite{cve2026}) were public before this work and are not",
     r"PR~\cite{aperture247}) were public before this work and are not"),
    ("paper/main.tex",
     "\\bibitem{cve2026} CVE-2026-31873: Tyk API Gateway non-atomic quota check/decrement race, 2026.\n",
     ""),
    ("paper/main.tex",
     r"\bibitem{kettle} J. Kettle. The single-packet attack: making remote race-conditions `local'. PortSwigger Research, 2023.",
     r"\bibitem{kettle} J. Kettle. Smashing the state machine: the true potential of web race conditions. PortSwigger Research, 2023."),

    # ---- attack implementation docstring ---------------------------------------
    ("attacks/class6_credit_race.py",
     "art (both verified in ``paper/phase1_sources.json``): Kettle's single-packet attack\n"
     "(PortSwigger Research, 2023) and CVE-2026-31873 (Tyk API Gateway, 2026, CVSS 7.5 —",
     "art: Kettle's \"Smashing the state machine: the true potential of web race\n"
     "conditions\" (PortSwigger Research, 2023), which introduces the single-packet attack ("),
]


def apply_simple(path: Path, pairs: list[tuple[str, str]]) -> int:
    if not path.exists():
        return 0
    s = path.read_text(encoding="utf-8")
    o = s
    for old, new in pairs:
        s = s.replace(old, new)
    if s != o:
        path.write_text(s, encoding="utf-8")
        return 1
    return 0


def main() -> None:
    changed = []

    for rel, old, new in EDITS:
        p = ROOT / rel
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        if old in s:
            p.write_text(s.replace(old, new, 1), encoding="utf-8")
            changed.append(rel)

    # Broad sweep across prose files that merely mention the wrong identifier or title.
    NOTE = ("CVE-2026-31873 was cited here for the quota race; verification against MITRE "
            "CVE Services and NVD showed that identifier belongs to an unrelated advisory, "
            "so the citation was removed")
    for rel in ["CLAUDE.md", "FINAL_RESEARCH_REPORT.md", "paper/class6_methodology.md",
                "paper/false_positive_check.md", "paper/novelty_matrix.md",
                "paper/novelty_matrix.csv", "paper/journal_reviewer_attack_v2.md"]:
        if rel in KEEP_AS_HISTORY:
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        o = s
        s = s.replace("CVE-2026-31873 (Tyk Gateway, 2026, CVSS 7.5)",
                      f"[withdrawn citation: {NOTE}]")
        s = s.replace("CVE-2026-31873 (Tyk API Gateway, 2026, CVSS 7.5)",
                      f"[withdrawn citation: {NOTE}]")
        s = s.replace("(CVE-2026-31873, Kettle)", "(Kettle)")
        s = s.replace("CVE-2026-31873", "[withdrawn CVE citation]")
        s = s.replace(KETTLE_OLD, KETTLE_NEW)
        s = s.replace("The single-packet attack: making remote race-conditions `local'",
                      "Smashing the state machine: the true potential of web race conditions")
        s = s.replace('"The single-packet attack: making remote race-conditions \'local\'"',
                      '"Smashing the state machine: the true potential of web race conditions"')
        if s != o:
            p.write_text(s, encoding="utf-8")
            changed.append(rel)

    print("updated:" if changed else "no changes (already applied)")
    for c in sorted(set(changed)):
        print("  ", c)
    print("\nleft untouched as historical record:")
    for c in sorted(KEEP_AS_HISTORY):
        print("  ", c)


if __name__ == "__main__":
    main()
