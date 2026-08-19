"""Insert the prioritized figures into the IEEE manuscript.

Only figures that carry an argument are included; the rest stay in the artifact. Captions
are written to be self-contained, so a reader who jumps to a figure learns what is plotted,
under which workload and concurrency, whether the values are empirical or analytic, and how
many observations back them.

Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "paper" / "main_ieee.tex"
s = p.read_text(encoding="utf-8")
before = s

FIG_M1 = r"""
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{fig_m1_abort_curve.png}
\caption{M1 leakage against abort position, deterministic generator, concurrency~1, medium
price tier, 20 requests per cell. The $x$-axis is the fraction of the response streamed
before the client disconnects; the $y$-axis is mean leakage per request in scenario dollars,
i.e.\ delivered value minus net committed debit. Vulnerable architectures peak just before
the commit would have fired and collapse to \$0 at completion, when it does fire; safe
architectures stay at \$0 throughout. All values are empirical. Error bars are within-cell
standard deviations and are zero at this concurrency.}
\label{fig:m1}
\end{figure}
"""

FIG_M1C = r"""
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{fig_m1_concurrency.png}
\caption{M1 negative result. Request volume is held constant at 20 requests per cell while
concurrency varies from 1 to 100 ($x$-axis, log scale); the $y$-axis is mean leakage per
request and request-level attack success. Both are invariant across the range, which is the
empirical basis for treating commitment timing as a per-request rather than a
contention-driven defect. Holding volume constant is what prevents traffic level from
masquerading as vulnerability.}
\label{fig:m1conc}
\end{figure}
"""

FIG_M2 = r"""
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{fig_m2_efficiency_heatmap.png}
\caption{M2 leakage efficiency --- the fraction of delivered value evaded --- by architecture
(rows) against declared-usage manipulation (columns), deterministic generator, medium tier,
concurrency~1, 100 requests per cell. Server-authoritative rows are uniformly zero. The
exploitable set differs between category-additive and flat-total pricing, which is the
empirical form of (\ref{eq:m2}): a manipulation pays off only when the pricing basis reads
the field it changes.}
\label{fig:m2}
\end{figure}
"""

FIG_B0 = r"""
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{fig_b0_concurrency.png}
\caption{B0 baseline: mean leakage per trial against concurrency, 30 repetitions per cell,
deterministic generator. Leakage is created by contention here, growing linearly at 0.099 per
additional concurrent request ($R^2 = 1.0000$). Section~\ref{sec:b0revised} shows that
concurrency is not the essential ingredient: delayed settlement produces the same
over-serving with strictly sequential arrivals.}
\label{fig:b0}
\end{figure}
"""

FIG_TOK = r"""
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{tokenizer_latency.png}
\caption{Standalone tokenizer recount latency (p50, log--log axes) by engine, workload and
input length, over 100 cells whose token lengths were verified exactly. Cost is linear in
input length, so recount budgets as tokens times a per-token constant. This is a tokenizer
microbenchmark, not a gateway throughput result: no request path, database or network is
involved.}
\label{fig:toklat}
\end{figure}
"""

# Each figure is placed in the section that argues from it.
anchors = [
    (r"\subsubsection{Two orthogonal properties}", FIG_M1, "fig:m1"),
    (r"\subsubsection{Concurrency is not the mechanism}", FIG_M1C, "fig:m1conc"),
    (r"\input{../results/tables/ieee/table_m2_results.tex}", FIG_M2, "fig:m2"),
    (r"\input{../results/tables/ieee/table_b0_baseline.tex}", FIG_B0, "fig:b0"),
    (r"\section{Cross-Architecture and Asynchronous Validation}", FIG_TOK, "fig:toklat"),
]

for anchor, block, label in anchors:
    if label in s and f"{{{label}}}" in s and "includegraphics" in s.split(label)[0][-400:]:
        continue  # already inserted
    if f"\\label{{{label}}}" in s:
        continue
    s = s.replace(anchor, block + "\n" + anchor, 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
