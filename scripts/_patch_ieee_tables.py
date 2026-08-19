"""Reduce the IEEE manuscript to a journal-appropriate set of tables.

Fourteen tables in a twelve-page body is a report, not a paper. Worse, full-width floats
can only occupy a page top or a dedicated float page, so a queue of them lands after the
bibliography -- which is what happened: six pages of tables trailing the references.

The set kept here is the one the argument actually needs. Everything dropped is still
generated, still in the artifact, and its numbers already appear in the prose; the text now
says so explicitly instead of pointing at a table that is not there.

Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "paper" / "main_ieee.tex"
s = p.read_text(encoding="utf-8")
before = s

DROP = ["table_formal_mapping", "table_real_stack_m2", "table_async_m1",
        "table_economic_sensitivity"]
for d in DROP:
    s = s.replace("\\input{../results/tables/ieee/%s.tex}\n" % d, "")

# Replace the cross-references to dropped tables with prose that carries the same content.
s = s.replace(
    r"""TLC returns a shortest counterexample for each unsafe configuration, and each reproduces the
mechanism we measured (Table~\ref{tab:formalmap}).""",
    r"""TLC returns a shortest counterexample for each unsafe configuration, and each reproduces
the mechanism we measured. The artifact pairs every counterexample with the measurement of
the implemented architecture it abstracts; the correspondence is exact in all ten
configurations.""", 1)

s = s.replace(
    r"""Under flat-total pricing three cells flip sign, because on this
token mix flat-total overcharges by so much that even a 90\,\% under-declared total still
exceeds the authoritative category cost. The architectural conclusion is
generator-independent; the per-manipulation magnitudes are not.""",
    r"""Under flat-total pricing three cells flip sign, because on this
token mix flat-total overcharges by so much that even a 90\,\% under-declared total still
exceeds the authoritative category cost. Five of the 48 cells changed effectiveness in
total; the per-cell comparison against the deterministic corpus is in the artifact. The
architectural conclusion is generator-independent; the per-manipulation magnitudes are
not.""", 1)

s = s.replace(
    r"""Duplicated events are suppressed
idempotently. A lost event, by contrast, leaks permanently. Whether a straggler looks lost or
merely late is a property of the observation horizon rather than of the architecture, and the
table records the horizon used.""",
    r"""Duplicated events are suppressed
idempotently across all 25 injected duplicates. A lost event, by contrast, leaks
permanently at every delay. Whether a straggler looks lost or merely late is a property of
the observation horizon rather than of the architecture; we used four times the configured
delay, floored at 400\,ms, and the artifact records the per-cell outcome.""", 1)

s = s.replace(
    r"""The
real-stack experiment demonstrates the second case directly: on a token mix with no reasoning
tokens, three flat-total cells reverse sign, because the pricing basis overcharges by more
than the manipulation evades.""",
    r"""The
real-stack experiment demonstrates the second case directly: on a token mix with no reasoning
tokens, three flat-total cells reverse sign, because the pricing basis overcharges by more
than the manipulation evades. The full price-tier sensitivity table is in the artifact; its
summary is that efficiency is identical across a uniform $10\times$ scaling and moves only
when the ratio between categories changes.""", 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
print("dropped:", DROP)
