"""Verify every figure and table in the COSE manuscript is cited in the text."""
import re
import pathlib

s = pathlib.Path("paper/main_cose.tex").read_text(encoding="utf-8")

figs = re.findall(r"\\label\{(fig:[^}]+)\}", s)
tabs = re.findall(r"\\label\{(tab:[^}]+)\}", s)
refs = set(re.findall(r"\\ref\{([^}]+)\}", s))

print("FIGURES:")
for f in figs:
    print(f"  {f:24} cited: {f in refs}")
print("TABLES:")
for t in tabs:
    print(f"  {t:24} cited: {t in refs}")

uncited = [x for x in figs + tabs if x not in refs]
print()
print("UNCITED FLOATS:", uncited or "none")
print("figure count:", len(figs), " table count:", len(tabs))
