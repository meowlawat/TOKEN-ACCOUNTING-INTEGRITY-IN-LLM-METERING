"""Rewrite the abstract and contributions for the journal-upgraded paper.

The abstract must now carry: the threat model, the accounting boundary, the three
dimensions, the formal invariant, what was MODEL-CHECKED, the M1 orthogonality result, the
M2 authority result, cross-architecture validation (including the asynchronous family),
the real-serving-stack external validity, and bounded limitations.

It must not: reintroduce detectability, claim a novel attack, say "universal", or describe
anything as proved that was not machine-checked.

Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "paper" / "main.tex"
s = p.read_text(encoding="utf-8")
before = s

NEW_ABSTRACT = r"""\begin{abstract}
Usage-based billing is a security boundary in LLM inference: value is streamed to the
client before accounting is necessarily finalized, and the charge depends on a
multi-category usage record produced at runtime. We study client-side under-payment under
an honest-provider threat model, and model this accounting-security boundary along three
dimensions --- \textbf{state synchronization}, \textbf{commitment timing}, and
\textbf{usage authority} --- unified by a single integrity property, $V(r)\le N(r)$, over a
request-lifecycle model. \emph{We do not claim new attack primitives}: the enabling
mechanisms are individually known, and the contribution is a systematic architectural
analysis, formalization and measurement of them across representative metering designs.

We encode the lifecycle in TLA+ and check it exhaustively with TLC: 10 architecture
configurations $\times$ 4 invariants, $28{,}363$ distinct states, every outcome declared
before the run and all $40$ matching. Model checking establishes what measurement cannot
--- that each unsafe architecture fails on \emph{every} schedule, not merely the ones our
harness produced --- and it separates the failures cleanly. The synchronization race breaks
ledger conservation while every individual record stays self-consistent, which is why a
per-record audit cannot detect it. Reservation and abort-safe finalization are
\textbf{orthogonal}: reservation alone yields solvency and violates integrity, abort-safe
finalization alone yields integrity and drives the balance negative, and only their
conjunction gives both. A correct server-side recount that is not the billing basis
restores nothing.

Empirically, the three dimensions behave differently under load, and we distinguish
empirical from analytic results: the synchronization race grows with concurrency (slope
$0.099$ per additional concurrent request, $R^2=1.0000$); commitment-timing leakage is
\emph{empirically} unchanged across concurrency levels 1--100 under fixed request volume;
and usage-authority leakage is \emph{analytically} independent of concurrency, which our
experiments confirm rather than discover. An architecture that recounts usage correctly,
records the result, and still bills the client-declared number leaks $58.3\%$ of the
delivered value; server-authoritative billing eliminates the observed leakage.

We then attack our own external validity three ways. Across three execution topologies and
two storage backends, $96$ accounting cells match the single-worker control with no
mismatches. Replacing our deterministic generator with a third-party serving stack
(\texttt{llama.cpp} serving SmolLM2-135M-Instruct) leaves the architectural conclusions
unchanged over $60$ cells with zero safety disagreements, while attack \emph{effectiveness}
moves substantially --- and reveals that on a real stack the provider's own honest charge
for a byte-identical request varies by $22$--$32\%$ with prefix-cache state, so a client
cannot verify its own bill even in principle. Finally, decoupling settlement in time shows
that asynchronous accounting is \emph{late rather than lossy} when the event pipeline is
honest, but converts the synchronization race into an architectural window: with
\emph{strictly sequential} arrivals $20$\,ms apart, a $500$\,ms reconciliation delay serves
four requests beyond a two-request budget and drives the balance negative. An atomic
guarded decrement provides nothing if it lands after the next authorization.

All reported results regenerate from raw data through fail-closed integrity gates, and
every headline accounting figure has been independently recomputed by code sharing nothing
with the measurement pipeline. We state explicitly what the formal model does not cover and
which claims are model-checked, analytically derived, or measured.
\end{abstract}"""

start = s.index(r"\begin{abstract}")
end = s.index(r"\end{abstract}") + len(r"\end{abstract}")
if "28{,}363" not in s:
    s = s[:start] + NEW_ABSTRACT + s[end:]

NEW_CONTRIB = r"""\item \textbf{A machine-checked formalization} (\S\ref{sec:formal}): the lifecycle encoded
in TLA+ and checked exhaustively with TLC across 10 architecture configurations and 4
invariants, yielding counterexample traces that match the measured failures and an
exhaustive orthogonality result for the M1 defenses.
\item \textbf{External validity attacked three ways} (\S\ref{sec:generality}): three
execution topologies, three accounting families including an asynchronous
event-and-worker pipeline, and a third-party serving stack in place of our own generator.
\end{enumerate}"""

if "machine-checked formalization" not in s:
    s = s.replace(r"""levels (standalone tokenizer, gateway, and a local real-model experiment).
\end{enumerate}""",
                  r"""levels (standalone tokenizer, gateway, and a local real-model experiment).
""" + NEW_CONTRIB, 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
