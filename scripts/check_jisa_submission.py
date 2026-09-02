"""Fail-closed submission gate for the JISA manuscript (paper/main_jisa.tex).

Adapted from scripts/check_cose_submission.py. The differences that matter are the
journal-specific limits taken from JISA's Guide for Authors:

  * abstract   <= 250 words
  * keywords   1 to 7          (C&S allowed more; JISA does not)
  * journal string must name JISA, not Computers & Security

and a hard block on any generative-AI declaration reappearing in the manuscript. That
block exists because such a declaration was introduced into the C&S manuscript against
instruction and had to be removed; the author's decision is that the JISA manuscript
carries none. This gate enforces that decision mechanically rather than trusting a
visual pass -- a declaration section renders perfectly and is easy to miss.

Usage:
    python scripts/check_jisa_submission.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
TEX = PAPER / "main_jisa.tex"
PDF = PAPER / "main_jisa.pdf"
LOG = PAPER / "main_jisa.log"

B = "\\"

# Phrases that would constitute an author-level AI-use declaration. Deliberately does
# NOT include bare "AI", "LLM", "GPT", "model" or "inference": those are the subject
# matter of the paper and must survive untouched.
AI_DECLARATION_MARKERS = [
    "Declaration of generative AI",
    "Declaration of Generative AI",
    "AI-assisted technologies in the writing process",
    "generative AI and AI-assisted",
    "AI-assisted writing",
    "AI-assisted manuscript",
    "Claude (Anthropic)",
    "ChatGPT",
    "the author used Claude",
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

    # ---- JISA journal-specific limits -----------------------------------------------
    abstract = s[s.index(rf"{B}begin{{abstract}}"):s.index(rf"{B}end{{abstract}}")]
    aw = word_count(abstract)
    checks.append(("Abstract <= 250 words (JISA limit)", aw <= 250, f"{aw} words"))

    kw_block = s[s.index(rf"{B}begin{{keyword}}"):s.index(rf"{B}end{{keyword}}")]
    kws = [k.strip() for k in kw_block.replace(rf"{B}begin{{keyword}}", "")
           .split(rf"{B}sep") if k.strip()]
    checks.append(("Keywords between 1 and 7 (JISA limit)",
                   1 <= len(kws) <= 7, f"{len(kws)} keywords"))

    checks.append(("Journal is JISA, not Computers & Security",
                   "Journal of Information Security and Applications" in s
                   and "Computers \\& Security}" not in s, "n/a"))
    checks.append(("Uses elsarticle class", "{elsarticle}" in s, "n/a"))

    # ---- AI declaration must be absent ----------------------------------------------
    found = [m for m in AI_DECLARATION_MARKERS if m in s]
    checks.append(("No generative-AI declaration in source (author decision)",
                   not found, ", ".join(found) if found else "absent"))

    # ---- structural integrity -------------------------------------------------------
    fig_labels = re.findall(rf"{re.escape(B)}label{{(fig:[^}}]+)}}", s)
    tab_labels = re.findall(rf"{re.escape(B)}label{{(tab:[^}}]+)}}", s)
    referenced = set(re.findall(rf"{re.escape(B)}ref{{([^}}]+)}}", s))
    uncited = [x for x in fig_labels + tab_labels if x not in referenced]
    checks.append(("Every figure and table is cited in the text",
                   not uncited, ", ".join(uncited) if uncited else "all cited"))

    labels = re.findall(rf"{re.escape(B)}label{{([^}}]+)}}", s)
    dupes = {x for x in labels if labels.count(x) > 1}
    checks.append(("No duplicate labels", not dupes,
                   ", ".join(sorted(dupes)) if dupes else f"{len(labels)} labels"))

    bib_keys = set(re.findall(rf"{re.escape(B)}bibitem\[[^\]]*\]{{([^}}]+)}}", s))
    cited: set[str] = set()
    for m in re.finditer(rf"{re.escape(B)}cite[pt]?(?:\[[^\]]*\])*{{([^}}]+)}}", s):
        cited.update(k.strip() for k in m.group(1).split(","))
    checks.append(("All bibliography entries cited", not (bib_keys - cited),
                   str(bib_keys - cited) if bib_keys - cited else "all cited"))
    checks.append(("All citations resolve", not (cited - bib_keys),
                   str(cited - bib_keys) if cited - bib_keys else "all resolve"))

    # ---- declarations JISA expects --------------------------------------------------
    for name, needle in [
        ("Data availability statement exists", rf"{B}section*{{Data availability}}"),
        ("Funding statement exists", rf"{B}section*{{Funding}}"),
        ("Competing interest declaration exists",
         rf"{B}section*{{Declaration of competing interest}}"),
        ("CRediT statement exists",
         rf"{B}section*{{CRediT authorship contribution statement}}"),
    ]:
        checks.append((name, needle in s, "n/a"))

    # ---- compiled PDF ---------------------------------------------------------------
    if PDF.exists():
        try:
            import pymupdf
            d = pymupdf.open(PDF)
            pages = d.page_count
            text = "\n".join(p.get_text() for p in d)
            blank = [i + 1 for i in range(pages) if len(d[i].get_text().strip()) < 80]
            d.close()
            checks.append(("PDF compiles and has pages", pages > 0, f"{pages} pages"))
            checks.append(("No blank pages", not blank, str(blank) if blank else "none"))
            pdf_hits = [m for m in AI_DECLARATION_MARKERS if m in text]
            checks.append(("No generative-AI declaration in compiled PDF",
                           not pdf_hits,
                           ", ".join(pdf_hits) if pdf_hits else "absent"))
            checks.append(("JISA named in PDF",
                           "Journal of Information Security" in text, "n/a"))
        except ImportError:
            checks.append(("PDF checks", False, "pymupdf unavailable"))
    else:
        checks.append(("main_jisa.pdf exists", False, "missing"))

    if LOG.exists():
        log = LOG.read_text(encoding="utf-8", errors="ignore")
        ur = len(re.findall(r"Reference `[^']+' .* undefined", log))
        uc = len(re.findall(r"Citation `[^']+' .* undefined", log))
        of = log.count("Overfull")
        checks.append(("Undefined LaTeX references = 0", ur == 0, str(ur)))
        checks.append(("Undefined LaTeX citations = 0", uc == 0, str(uc)))
        checks.append(("Overfull boxes cosmetic only", of <= 3, f"{of} overfull boxes"))
    else:
        checks.append(("Compile log available", False, "main_jisa.log missing"))

    # ---- report ---------------------------------------------------------------------
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
