"""Trim the IEEE abstract to journal length and fix the contributions heading.

The converted abstract ran to roughly 450 words across four paragraphs, which is long even
for a journal. IEEE abstracts are conventionally 150-250 words and a single block. The
rewrite below keeps every load-bearing number and drops the elaboration, which belongs in
the body.

`\\paragraph` under a `\\section` renders in IEEEtran as an enumerated "a) ... :" run-in
head. That is fine for the related-work discussion, where the items really are a sequence,
but it looks wrong immediately before a numbered contributions list, so that one becomes a
plain italic lead-in.

Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "paper" / "main_ieee.tex"
s = p.read_text(encoding="utf-8")
before = s

NEW_ABSTRACT = r"""\begin{abstract}
Usage-based pricing makes metering a security boundary for LLM inference: value reaches the
client while accounting is still open, and the charge depends on a multi-category usage
record that exists only after the request runs. We study the under-explored direction of
that boundary, an honest provider and a dishonest client, by modelling a metered request as
a lifecycle with one integrity property, $V(r) \le N(r)$, and decomposing the failure space
into state synchronization (B0), commitment timing (M1), and usage authority (M2). No new
attack primitive is claimed; the mechanisms are individually known, and the contribution is
their unification, formalization, measurement and defense analysis. Using a Dockerized
FastAPI gateway over PostgreSQL and Redis, we check the lifecycle in TLA+ with TLC across
ten architecture configurations and four invariants, with expectations fixed before the
runs. Reservation and abort-safe finalization prove orthogonal: each alone secures one of
solvency and accounting integrity, and only both secure both. Computing usage correctly is
not the same as billing from it --- an architecture that recounts accurately, stores the
result, and still charges the client-declared number leaks 58.3\,\% of delivered value in
the controlled setting and 69.0\,\% against a real serving stack, while server-authoritative
billing removed the observed leakage. Substituting third-party serving code for our own
generator left every architectural conclusion intact across sixty cells. Decoupling
settlement in time produced over-serving under strictly sequential arrivals, showing that
the B0 condition is not about concurrency: authorization must be atomically coupled to
economic commitment on the path that authorizes service. We report defense overhead,
model-level sufficiency conditions, and what the formal model does not cover.
\end{abstract}"""

start = s.index(r"\begin{abstract}")
end = s.index(r"\end{abstract}") + len(r"\end{abstract}")
if "under-explored direction of\nthat boundary" not in s:
    s = s[:start] + NEW_ABSTRACT + s[end:]

s = s.replace(r"\paragraph{Contributions}", r"\noindent\emph{Contributions.}", 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
