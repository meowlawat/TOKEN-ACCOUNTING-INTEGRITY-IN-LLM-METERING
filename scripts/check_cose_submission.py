"""Automated submission-readiness gate for the Computers & Security manuscript.

Fails closed: every check must explicitly pass. A check that cannot determine an answer
counts as a failure, not a skip.

Usage:
    python scripts/check_cose_submission.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "main_cose.tex"
PDF = ROOT / "paper" / "main_cose.pdf"
LOG = ROOT / "paper" / "main_cose.log"
PAPER = ROOT / "paper"

STALE_CLAIMS = [
    r"\bD0\b", r"\bD1\b", r"\bD2\b", r"\bD3\b",
    r"17/17", r"CVE-2026-31873", r"\bTyk\b",
    r"single-packet attack.*making remote",  # the old, wrong Kettle title
    r"essentially free", r"0\.1\s*ms\b",
    r"B0.*requires? concurrency\b", r"B0.*needs concurrency\?\s*\*?\*?yes",
]

# "commercial provider(s)" is legitimate when the surrounding text explicitly denies
# validating against one (our own wording always negates this). Flag it only if no
# negation cue ("not", "no", "does not", "cannot") appears within 80 chars before it.
NEGATION_CUES = ("not ", "no ", "n't ", "cannot", "none")


def commercial_provider_hits(s: str) -> list[str]:
    hits = []
    for m in re.finditer(r"commercial provider", s, re.I):
        window = s[max(0, m.start() - 80):m.start()].lower()
        if not any(cue in window for cue in NEGATION_CUES):
            hits.append(s[max(0, m.start() - 40):m.start() + 40])
    return hits


def word_count(tex: str) -> int:
    tex = re.sub(r"\\(cite[pt]?|ref|label|url|texttt|emph|textbf|textit)\{[^}]*\}", " ", tex)
    tex = re.sub(r"[\\{}$]", " ", tex)
    return len(tex.split())


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    if not TEX.exists():
        print("FATAL: paper/main_cose.tex does not exist")
        sys.exit(1)
    s = TEX.read_text(encoding="utf-8")

    # ---- word / structure limits ------------------------------------------------
    abstract = s[s.index(r"\begin{abstract}"):s.index(r"\end{abstract}")]
    body = s[s.index(r"\section{Introduction}"):s.index(r"\bibliographystyle")]
    refs = s[s.index(r"\begin{thebibliography}"):s.index(r"\end{thebibliography}")]
    abs_words = word_count(abstract)
    total_words = word_count(body) + word_count(refs)

    checks.append(("Abstract <= 250 words", abs_words <= 250, f"{abs_words} words"))
    checks.append(("Total manuscript <= 12,000 words", total_words <= 12000,
                   f"{total_words} words"))

    kw_match = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", s, re.S)
    n_kw = len(re.split(r"\\sep", kw_match.group(1))) if kw_match else 0
    checks.append(("Keywords count 5-10", 5 <= n_kw <= 10, f"{n_kw} keywords"))

    checks.append(("No IEEEkeywords environment", r"\begin{IEEEkeywords}" not in s, "n/a"))
    checks.append(("No \\IEEE... commands",
                   not re.search(r"\\IEEE\w+", s), "n/a"))
    checks.append(("No enrollment number", "03517713524" not in s, "n/a"))
    checks.append(("Uses elsarticle class",
                   bool(re.search(r"\\documentclass\[[^\]]*\]\{elsarticle\}", s)),
                   "n/a"))
    checks.append(("Author-year citations (natbib \\citep/\\citet used)",
                   bool(re.search(r"\\cite[pt]\{", s)), "n/a"))

    # ---- stale/withdrawn claims --------------------------------------------------
    stale_hits = []
    for pat in STALE_CLAIMS:
        for m in re.finditer(pat, s, re.I):
            stale_hits.append((pat, s[max(0, m.start()-40):m.start()+40]))
    stale_hits += [("commercial provider (unnegated)", ctx)
                  for ctx in commercial_provider_hits(s)]
    checks.append(("No forbidden stale scientific claims", not stale_hits,
                   f"{len(stale_hits)} hits" if stale_hits else "0 hits"))

    # ---- figure/table/reference resolution --------------------------------------
    fig_labels = set(re.findall(r"\\label\{(fig:[^}]+)\}", s))
    fig_refs = set(re.findall(r"\\ref\{(fig:[^}]+)\}", s))
    unresolved_figs = fig_refs - fig_labels
    checks.append(("All figure references resolve", not unresolved_figs,
                   str(unresolved_figs) if unresolved_figs else "all resolve"))

    tab_labels = set(re.findall(r"\\label\{(tab:[^}]+)\}", s))
    tab_refs = set(re.findall(r"\\ref\{(tab:[^}]+)\}", s))
    unresolved_tabs = tab_refs - tab_labels
    checks.append(("All table references resolve", not unresolved_tabs,
                   str(unresolved_tabs) if unresolved_tabs else "all resolve"))

    bib_keys = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]+)\}", s))
    cited_keys = set()
    for m in re.finditer(r"\\cite[pt]?\{([^}]*)\}", s):
        cited_keys.update(k.strip() for k in m.group(1).split(","))
    uncited = bib_keys - cited_keys
    undefined_cites = cited_keys - bib_keys
    checks.append(("All bibliography entries cited", not uncited,
                   str(uncited) if uncited else "all cited"))
    checks.append(("All citations resolve to a bibliography entry", not undefined_cites,
                   str(undefined_cites) if undefined_cites else "all resolve"))

    # ---- required declarations --------------------------------------------------
    checks.append(("Data availability statement exists",
                   r"\section*{Data availability}" in s, "n/a"))
    checks.append(("Generative AI disclosure exists",
                   r"\section*{Generative AI disclosure}" in s, "n/a"))
    checks.append(("Funding statement exists",
                   r"\section*{Funding}" in s, "n/a"))
    checks.append(("Declaration of competing interest exists",
                   r"\section*{Declaration of competing interest}" in s, "n/a"))
    checks.append(("CRediT statement exists",
                   r"\section*{CRediT authorship contribution statement}" in s, "n/a"))
    checks.append(("Highlights file exists", (PAPER / "highlights.txt").exists(), "n/a"))
    checks.append(("Data availability doc exists",
                   (PAPER / "data_availability.md").exists(), "n/a"))
    checks.append(("Submission metadata doc exists",
                   (PAPER / "submission_metadata.md").exists(), "n/a"))
    checks.append(("Author bio file exists",
                   (PAPER / "author_bio.txt").exists(), "n/a"))
    checks.append(("Submission blockers doc exists",
                   (PAPER / "SUBMISSION_BLOCKERS.md").exists(), "n/a"))
    checks.append(("figures_cose/ directory populated",
                   (PAPER / "figures_cose").is_dir()
                   and any((PAPER / "figures_cose").glob("*.png")), "n/a"))

    # ---- IEEE source untouched ---------------------------------------------------
    import subprocess
    diff = subprocess.run(["git", "diff", "--", "paper/main_ieee.tex"],
                          capture_output=True, text=True, cwd=ROOT).stdout
    checks.append(("paper/main_ieee.tex shows no git diff", diff.strip() == "",
                   "diff present!" if diff.strip() else "no diff"))

    # ---- compiled PDF sanity ------------------------------------------------------
    if PDF.exists():
        try:
            import pymupdf
            d = pymupdf.open(PDF)
            pages = d.page_count
            blank = [i + 1 for i in range(pages) if len(d[i].get_text().strip()) < 80]
            checks.append(("PDF compiles and has pages", pages > 0, f"{pages} pages"))
            checks.append(("No blank pages", not blank, str(blank) if blank else "none"))
        except ImportError:
            checks.append(("PDF page/blank check", False, "pymupdf not available"))
    else:
        checks.append(("main_cose.pdf exists", False, "missing"))

    if LOG.exists():
        log = LOG.read_text(encoding="utf-8", errors="ignore")
        undef_ref = len(re.findall(r"Reference `[^']+' .* undefined", log))
        undef_cite = len(re.findall(r"Citation `[^']+' .* undefined", log))
        overfull = len(re.findall(r"Overfull \\hbox", log))
        checks.append(("Undefined LaTeX references = 0", undef_ref == 0, str(undef_ref)))
        checks.append(("Undefined LaTeX citations = 0", undef_cite == 0, str(undef_cite)))
        checks.append(("Overfull boxes small/cosmetic only",
                       overfull <= 3, f"{overfull} overfull boxes"))
    else:
        checks.append(("Compile log available", False, "main_cose.log missing"))

    # ---- every float cited in the text ----------------------------------------------
    # Elsevier requires each figure and table to be referred to in the body. Shipping an
    # uncited float is invisible in the compiled PDF -- it renders fine -- so it needs an
    # explicit check rather than a visual pass.
    all_fig_labels = re.findall(r"\\label\{(fig:[^}]+)\}", s)
    all_tab_labels = re.findall(r"\\label\{(tab:[^}]+)\}", s)
    referenced = set(re.findall(r"\\ref\{([^}]+)\}", s))
    uncited = [x for x in all_fig_labels + all_tab_labels if x not in referenced]
    checks.append(("Every figure and table is cited in the text",
                   not uncited, ", ".join(uncited) if uncited else "all cited"))

    # ---- report -------------------------------------------------------------------
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
