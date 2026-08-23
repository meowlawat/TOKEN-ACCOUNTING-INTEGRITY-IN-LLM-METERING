"""Compute word/section/figure/table/reference counts for the COSE manuscript."""
import re
import pathlib

s = pathlib.Path("paper/main_cose.tex").read_text(encoding="utf-8")


def word_count(tex: str) -> int:
    tex = re.sub(r"\\(cite[pt]?|ref|label|url|texttt|emph|textbf|textit)\{[^}]*\}", " ", tex)
    tex = re.sub(r"[\\{}$]", " ", tex)
    return len(tex.split())


abstract = s[s.index(r"\begin{abstract}"):s.index(r"\end{abstract}")]
body = s[s.index(r"\section{Introduction}"):s.index(r"\bibliographystyle")]
refs = s[s.index(r"\begin{thebibliography}"):s.index(r"\end{thebibliography}")]

print("abstract words:", word_count(abstract))
print("body words (excl. refs):", word_count(body))
print("references section words:", word_count(refs))
print("total (body+refs):", word_count(body) + word_count(refs))
print("sections:", len(re.findall(r"\\section\{", s)))
print("unnumbered sections:", len(re.findall(r"\\section\*\{", s)))
print("figures:", len(re.findall(r"\\begin\{figure\}", s)))
print("tables:", len(re.findall(r"\\begin\{table\*?\}", s)))
print("bibitems:", len(re.findall(r"\\bibitem", s)))
cites = re.findall(r"\\cite[pt]?\{([^}]*)\}", s)
keys = set()
for c in cites:
    keys.update(k.strip() for k in c.split(","))
print("distinct cited keys:", len(keys))
print("total citation commands:", len(cites))
