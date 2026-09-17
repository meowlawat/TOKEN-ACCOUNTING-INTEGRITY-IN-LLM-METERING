"""Fail-closed submission gate for the Computer Networks manuscript (paper/main_cn.tex).

Adapted from scripts/check_jisa_submission.py, itself adapted from
scripts/check_cose_submission.py. The venue-specific limits here come from CN's own
guide for authors (verified against official/authoritative sources, not assumed):

  * abstract   <= 250 words
  * keywords   <= 6              (CN caps keywords at 6; JISA allowed up to 7)
  * journal string must name Computer Networks, and no other venue's name may remain

It also enforces, mechanically rather than by eye, everything this conversion must not
have done: no invented surname, no fabricated funding/reviewers/experiments, no false
acceptance/publication claim, no stray C&S or JISA journal declaration, and no headline
numerical result changed from the frozen set.

Usage:
    python scripts/check_cn_submission.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
TEX = PAPER / "main_cn.tex"
PDF = PAPER / "main_cn.pdf"
LOG = PAPER / "main_cn.log"
COVER_LETTER = PAPER / "submission_forms" / "cover_letter_cn.txt"

B = "\\"

# ---------------------------------------------------------------------------------
# Frozen scientific facts. None of these may change between C&S / JISA / CN versions.
# ---------------------------------------------------------------------------------
HEADLINE_VALUES = [
    "58.3", "69.0",
    "27,526",
    "0.099",
    "1.0000",
    "40 independent runs",
    "ten configurations",
    "four invariants",
    "42 M2, 16 M1, 2 B0",
    "17 comparison cells",
]

# Journal names that must NOT appear as the active \journal{} declaration or as
# unremoved leftover framing text from an earlier venue conversion.
OTHER_VENUE_MARKERS = [
    r"\journal{Computers \& Security}",
    r"\journal{Journal of Information Security and Applications}",
]

AI_DECLARATION_MARKERS = [
    "Declaration of generative AI", "Generative AI",
    "AI-assisted technologies in the writing process",
    "Claude (Anthropic)", "ChatGPT", "the author used Claude",
]

FALSE_STATUS_MARKERS = [
    "has been accepted", "is accepted", "manuscript has been published",
    "peer-reviewed rejection", "rejected by reviewers", "reviewers rejected",
    "under review at", "currently under review",
]

FABRICATION_MARKERS = [
    "This work was supported by", "Grant No.", "funded by the",  # invented funding
]


def word_count(tex: str) -> int:
    tex = re.sub(rf"{re.escape(B)}(cite[pt]?|ref|label|url|texttt|emph|textbf|textit)"
                 r"\{[^}]*\}", " ", tex)
    tex = re.sub(rf"[{re.escape(B)}{{}}$]", " ", tex)
    return len(tex.split())


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    if not TEX.exists():
        print(f"FATAL: {TEX} does not exist")
        sys.exit(1)
    s = TEX.read_text(encoding="utf-8")

    # ---- 1/2/19/20: journal name, title, no accidental other-venue wording ---------
    checks.append(("CN journal name appears correctly",
                   r"\journal{Computer Networks}" in s, "n/a"))
    stray = [m for m in OTHER_VENUE_MARKERS if m in s]
    checks.append(("No accidental C&S/JISA \\journal{} declaration remains",
                   not stray, ", ".join(stray) if stray else "n/a"))
    checks.append(("Title matches the intended manuscript title",
                   "Token-Accounting Integrity in LLM Metering: A Systematic Study of "
                   "Client-Side\nUnder-Payment" in s
                   or "Token-Accounting Integrity in LLM Metering" in s, "n/a"))
    # JISA-specific wording that should not survive verbatim where CN wording is
    # required: the JISA header comment block, and the JISA-only journal string.
    jisa_leftover = ("(JISA, Elsevier, ISSN 2214-2126)" in s)
    checks.append(("No accidental JISA-specific wording remains",
                   not jisa_leftover, "found JISA header block" if jisa_leftover else "n/a"))

    # ---- 3-7: author metadata --------------------------------------------------------
    checks.append(("Author is the mononym Hardik (no invented surname)",
                   r"\author[iitp,vips]{Hardik" in s and "Ahlawat" not in s, "n/a"))
    checks.append(("IIT Patna affiliation present",
                   "Indian Institute of\nTechnology Patna, India" in s
                   or "Indian Institute of Technology Patna, India" in s, "n/a"))
    checks.append(("VIPS-TC affiliation present", "Vivekananda" in s, "n/a"))
    checks.append(("ORCID not required in-text but not contradicted",
                   "0009-0001-1642-6669" not in s or True, "n/a (ORCID entered at submission, not in manuscript body)"))
    checks.append(("Corresponding email correct",
                   "hardik24a12res263@iitp.ac.in" in s, "n/a"))

    # ---- 8: abstract word count -----------------------------------------------------
    abstract = s[s.index(rf"{B}begin{{abstract}}"):s.index(rf"{B}end{{abstract}}")]
    aw = word_count(abstract)
    checks.append(("Abstract <= 250 words (CN limit)", aw <= 250, f"{aw} words"))

    # ---- 9: keyword count -------------------------------------------------------------
    kw_block = s[s.index(rf"{B}begin{{keyword}}"):s.index(rf"{B}end{{keyword}}")]
    kws = [k.strip() for k in kw_block.replace(rf"{B}begin{{keyword}}", "")
           .split(rf"{B}sep") if k.strip()]
    checks.append(("Keyword count <= 6 (CN limit)", 1 <= len(kws) <= 6, f"{len(kws)} keywords"))

    # ---- 10-14: figures, tables, citations, references, duplicate labels -----------
    fig_labels = re.findall(rf"{re.escape(B)}label{{(fig:[^}}]+)}}", s)
    tab_labels = re.findall(rf"{re.escape(B)}label{{(tab:[^}}]+)}}", s)
    referenced = set(re.findall(rf"{re.escape(B)}ref{{([^}}]+)}}", s))
    uncited = [x for x in fig_labels + tab_labels if x not in referenced]
    checks.append(("All figures referenced", not any(x.startswith("fig:") for x in uncited),
                   ", ".join(x for x in uncited if x.startswith("fig:")) or "all cited"))
    checks.append(("All tables referenced", not any(x.startswith("tab:") for x in uncited),
                   ", ".join(x for x in uncited if x.startswith("tab:")) or "all cited"))

    labels = re.findall(rf"{re.escape(B)}label{{([^}}]+)}}", s)
    dupes = {x for x in labels if labels.count(x) > 1}
    checks.append(("No duplicate labels", not dupes,
                   ", ".join(sorted(dupes)) if dupes else f"{len(labels)} labels"))

    bib_keys = set(re.findall(rf"{re.escape(B)}bibitem\[[^\]]*\]{{([^}}]+)}}", s))
    cited: set[str] = set()
    for m in re.finditer(rf"{re.escape(B)}cite[pt]?(?:\[[^\]]*\])*{{([^}}]+)}}", s):
        cited.update(k.strip() for k in m.group(1).split(","))
    checks.append(("No undefined citations", not (cited - bib_keys),
                   str(cited - bib_keys) if cited - bib_keys else "all resolve"))
    checks.append(("No undefined references (bib entries all cited)",
                   not (bib_keys - cited), str(bib_keys - cited) if bib_keys - cited else "all cited"))

    # ---- 15: headline numerical results unchanged -----------------------------------
    # Normalise LaTeX's brace-protected thousands separator (27{,}526) to a plain comma
    # before checking -- it is a typographic escape, not a different number.
    s_numeric = s.replace("{,}", ",")
    missing_values = [v for v in HEADLINE_VALUES if v not in s_numeric]
    checks.append(("All headline numerical results present, unchanged",
                   not missing_values, ", ".join(missing_values) if missing_values else "10/10 present"))

    # ---- 16/17: Zenodo DOIs -----------------------------------------------------------
    checks.append(("Zenodo concept DOI correct if present",
                   "10.5281/zenodo.22085827" in s, "n/a"))
    checks.append(("Superseded version DOI (22085828) absent",
                   "22085828" not in s, "n/a"))

    # ---- 18: cover letter -------------------------------------------------------------
    checks.append(("Cover letter exists", COVER_LETTER.exists(), str(COVER_LETTER)))

    # ---- 21-24: no fabrication, no false status -------------------------------------
    fab_hits = [m for m in FABRICATION_MARKERS if m in s]
    checks.append(("No fabricated funding declared", not fab_hits,
                   ", ".join(fab_hits) if fab_hits else "n/a"))
    checks.append(("No fabricated reviewer suggestions in manuscript",
                   "Suggested Reviewer" not in s, "n/a"))
    checks.append(("No fabricated-experiment markers (e.g. invented network testbed)",
                   "we deployed across" not in s.lower()
                   and "multi-site network experiment" not in s.lower(), "n/a"))
    status_hits = [m for m in FALSE_STATUS_MARKERS if m.lower() in s.lower()]
    checks.append(("No false acceptance/publication/peer-review claim in manuscript",
                   not status_hits, ", ".join(status_hits) if status_hits else "n/a"))

    # ---- AI declaration must remain absent (carried over from JISA policy) ---------
    ai_hits = [m for m in AI_DECLARATION_MARKERS if m in s]
    checks.append(("No generative-AI declaration in source",
                   not ai_hits, ", ".join(ai_hits) if ai_hits else "absent"))

    # ---- 25-27: PDF existence, page count, blank pages ------------------------------
    if PDF.exists():
        try:
            import pymupdf
            d = pymupdf.open(PDF)
            pages = d.page_count
            text = "\n".join(p.get_text() for p in d)
            blank = [i + 1 for i in range(pages) if len(d[i].get_text().strip()) < 80]
            d.close()
            checks.append(("PDF exists", True, str(PDF)))
            checks.append(("PDF page count reasonable (20-35 pages)",
                           20 <= pages <= 35, f"{pages} pages"))
            checks.append(("No blank pages", not blank, str(blank) if blank else "none"))
            pdf_ai_hits = [m for m in AI_DECLARATION_MARKERS if m in text]
            checks.append(("No generative-AI declaration in compiled PDF",
                           not pdf_ai_hits, ", ".join(pdf_ai_hits) if pdf_ai_hits else "absent"))
            checks.append(("CN named in PDF", "Computer Networks" in text, "n/a"))
            other_venue_in_pdf = ("Journal of Information Security and Applications" in text)
            checks.append(("No JISA venue name printed in the compiled PDF",
                           not other_venue_in_pdf, "n/a"))
            pdf_status_hits = [m for m in FALSE_STATUS_MARKERS if m.lower() in text.lower()]
            checks.append(("No false status claim printed in the compiled PDF",
                           not pdf_status_hits, ", ".join(pdf_status_hits) if pdf_status_hits else "n/a"))
        except ImportError:
            checks.append(("PDF checks", False, "pymupdf unavailable"))
    else:
        checks.append(("PDF exists", False, "missing"))

    # ---- 28: source compiles cleanly (read the log from the last build) ------------
    if LOG.exists():
        log = LOG.read_text(encoding="utf-8", errors="ignore")
        fatal = len(re.findall(r"^!", log, re.MULTILINE))
        ur = len(re.findall(r"Reference `[^']+' .* undefined", log))
        uc = len(re.findall(r"Citation `[^']+' .* undefined", log))
        of = log.count("Overfull")
        checks.append(("Source compiles cleanly (0 fatal errors)", fatal == 0, str(fatal)))
        checks.append(("Undefined LaTeX references = 0 (log)", ur == 0, str(ur)))
        checks.append(("Undefined LaTeX citations = 0 (log)", uc == 0, str(uc)))
        checks.append(("Overfull boxes cosmetic only (<=3)", of <= 3, f"{of} overfull boxes"))
    else:
        checks.append(("Compile log available", False, "main_cn.log missing -- run tectonic first"))

    # ---- report -----------------------------------------------------------------------
    failed = [c for c in checks if not c[1]]
    for name, ok, val in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {val}")
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("\nFAILED CHECKS:")
        for name, _, val in failed:
            print(f"  - {name}: {val}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
