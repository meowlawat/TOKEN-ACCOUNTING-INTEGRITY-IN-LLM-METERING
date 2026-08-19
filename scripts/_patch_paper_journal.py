"""Insert the journal-upgrade sections into paper/main.tex.

Three additions, each placed where the argument needs it:

  * a Formal Verification section, before Defense Sufficiency Conditions, so that the
    sufficiency conditions can cite what was machine-checked rather than asserted;
  * an External Validity subsection inside Cross-architecture validation;
  * an Asynchronous Accounting subsection in the same place, since it is the third
    accounting family.

Kept as a file rather than a heredoc because LaTeX backslashes do not survive shell
quoting. Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "paper" / "main.tex"
s = p.read_text(encoding="utf-8")
before = s

FORMAL = r"""\section{Formal Verification}
\label{sec:formal}
Measurement establishes that a defect occurs on the schedules our harness produced. It
cannot establish that a defended architecture is safe on schedules it did not produce. We
therefore encode the request lifecycle of \S\ref{sec:statemodel} in TLA+ and check it
exhaustively with TLC.

\paragraph{Model.} One specification covers all three dimensions; each dimension is a
Boolean constant, so the safe and unsafe architectures are the \emph{same} state machine
under different constants, exactly as the testbed implements them behind one interface:
\texttt{AtomicDebit} (B0), \texttt{Reserves} and \texttt{AbortSafe} (M1), and
\texttt{ServerAuthority} (M2). A fifth constant, \texttt{ClientMayAbort}, is a
\emph{workload} switch rather than an architecture property; disabling it in the B0
configurations keeps the synchronization counterexample free of commitment-timing noise,
mirroring how the experiments hold the other two dimensions at their safe setting.

Four invariants are checked, each the formal counterpart of a gate the summarizers already
apply to every experimental record: \textsc{AccountingIntegrity}
($\forall r$ terminal: $V(r)\le N(r)$, gate G1), \textsc{Solvency} ($\mathrm{balance}\ge0$),
\textsc{LedgerConservation} (all terminal $\Rightarrow B_{\text{init}}-B_{\text{final}}=\sum_r N(r)$,
gate G3), and \textsc{RefundBounded} ($F(r)\le\max(0,\mathrm{Res}(r)-V(r))$, the paper's
legitimate-refund condition). Solvency is checked \emph{separately} from accounting
integrity; collapsing them would destroy the very distinction the ablation exists to
establish.

\paragraph{Method.} Each invariant is checked in its own TLC run, because TLC halts at the
first violation it finds and checking them jointly would hide that an M2 architecture
breaks two of them. The result is a full configuration $\times$ invariant matrix
(Table~\ref{tab:formalmatrix}): \textbf{10 configurations $\times$ 4 invariants = 40
independent runs, 28{,}363 distinct states}. Every expected outcome is declared in
\texttt{formal/check.py} \emph{before} the run and the script exits non-zero on any
disagreement; \textbf{all 40 matched, with 0 disagreements}.

\input{../results/tables/table_formal_matrix.tex}

\paragraph{What the counterexamples say.} TLC returns a shortest counterexample for each
unsafe configuration, and each one reproduces the mechanism we measured
(Table~\ref{tab:formalmap}, full traces in \texttt{paper/formal\_empirical\_mapping.md}).

For \textbf{B0}, the 21-step trace is the lost update exactly: both requests read
$\mathrm{snapshot}=2$, both blind-write $\mathrm{balance}:=2-2=0$, both then deliver and
are each charged. Note \emph{which} invariant fails --- accounting integrity and the
refund bound both \textbf{hold}, because every individual record is internally consistent;
what breaks is conservation of the shared balance. That is precisely why a per-record
audit cannot detect B0 while a conservation check can.

For \textbf{M1}, the model checks all four combinations of (reserves, abort-safe), not
just the two the implementation ships. Reservation alone yields solvency and violates
integrity; abort-safe finalization alone yields integrity and drives the balance to
$-1$; only the conjunction satisfies both. \textbf{The orthogonality claim is therefore
established by exhaustive exploration, not by the two architectures we happened to
build.}

For \textbf{M2}, the client-authoritative architecture violates accounting integrity, and
\emph{also} the refund bound --- with a reservation in place, under-billing surfaces as an
over-refund. That the same defect appears in two independent invariants is a consequence
of the model rather than something we set out to show; it became visible only because the
invariants are checked separately. Turning on \texttt{ServerAuthority} restores all four
invariants \emph{against the same lying client}: the declared value simply stops being
read.

Finally, the three defenses \emph{compose}: with contention, aborts and a lying client all
enabled, no invariant is violated on any reachable state, at two and at three concurrent
requests.

\paragraph{What this does not establish.} Nothing here proves a production implementation
safe. The model abstracts away the database, the network, partial failure, asynchronous
reconciliation, multi-category pricing and tokenizer disagreement; it is finite (2--3
requests, unit pricing); only safety properties are checked, not liveness; and there is
\textbf{no refinement proof} from the specification to \texttt{app/}. The correspondence
is an argument supported by case-by-case agreement between formal and empirical outcomes,
and we do not call it more than that. The complete exclusion list is
\texttt{paper/scope\_of\_formal\_claims.md}, and every claim in the paper carries one of
\textsc{model-checked}, \textsc{formally argued}, \textsc{analytically derived},
\textsc{directly measured} or \textsc{inferred} accordingly. We never write ``proved'' for
anything weaker than the first.

\paragraph{The model was wrong first.} The expectation discipline earned its keep
immediately. Our first specification treated a reservation as a \emph{hold} and set
$D=\mathrm{charge}$ at settlement, so $N=D-F$ fell below the delivered value and TLC
rejected the \emph{safe} configurations. The model was wrong, not the paper: in a
reserve-and-reconcile architecture the reservation \emph{is} the committed debit and the
refund returns its unused part. We record the failure rather than erase it.

"""

EXTERNAL = r"""\paragraph{A real serving stack.} Every figure above was produced against a generator we
wrote. That is what makes the accounting arithmetic exact, but it leaves an obvious
objection open, so we repeated the experiments with the token source replaced by
\texttt{llama.cpp}'s \texttt{llama-server} running SmolLM2-135M-Instruct on CPU --- a
widely deployed self-hosted serving stack we did not write, with a real BPE tokenizer,
real SSE streaming, and usage records the server produces itself. The gateway,
architectures, accounting backends, settlement logic and integrity gates are unchanged;
only the token source differs, and the mock default remains byte-identical (the regression
suites still pass 16/16 and 19/19).

Across \textbf{12 M1 cells and 48 M2 cells there were zero safety disagreements}
(Tables~\ref{tab:realm1}, \ref{tab:realm2}). Vulnerable commitment-timing architectures
still leak on abort and collapse to zero at completion; \texttt{reserve\_reconcile} still
leaks nothing; every server-authoritative architecture still leaks exactly $0.000$ across
all eight manipulations.

What \emph{did} move is attack effectiveness, and we report it rather than average it
away. Output under-reporting at $90\%$ yields $0.690$ here versus $0.583$ on the mock,
because SmolLM2 emits no reasoning tokens and output therefore dominates the cost. For the
same reason \texttt{drop\_reasoning} --- our only K2 manipulation --- becomes
\textbf{completely inert}: there is nothing to drop. Under flat-total pricing, three cells
flip sign, because on this token mix flat-total over-charges by so much that even a $90\%$
under-declared total still exceeds the authoritative category cost. \textbf{The
architectural conclusion is generator-independent; the per-manipulation magnitudes are
not.}

\paragraph{The provider's own number is not reproducible.} One property of real serving
appeared that the mock cannot exhibit. \texttt{llama-server} reports a prefix-cache split
(\texttt{cached\_tokens}), and because cached input is priced an order of magnitude below
uncached input, the \emph{honest} charge for a byte-identical request depends on server
cache state. Repeating identical requests, the reported split moved (e.g.\ 24 then 52 of
53 prompt tokens) and the authoritative cost moved with it by $22$--$32\%$ on $3/3$ prompts
(Table~\ref{tab:cachedsplit}). Three consequences follow directly, and they sharpen the
threat model rather than decorate it: the provider's authoritative number is not
reproducible across calls; a client cannot verify its own bill even in principle; and a
client that over-declares cached tokens has genuine plausible deniability, because the
true value legitimately varies. This is measured on one stack and we do not generalize it
to commercial providers --- but it is exactly the kind of accounting nondeterminism that
distinguishes LLM metering from metering a fixed-price API call.

\paragraph{Asynchronous accounting.} Both backends so far settle before the response
completes. Real metering pipelines often do not: the gateway emits a usage \emph{event} and
a separate worker applies it later. We therefore added a third accounting family --- an
event queue with a \emph{continuously running} worker and a controlled reconciliation delay
$D$ --- because a claim of architectural generality that quietly assumes strong consistency
is not worth much.

With an honest pipeline, asynchronous accounting is \textbf{late, not lossy}: the mean
exposure window between value delivery and durable debit tracks $D$ closely
($D=0,10,50,100,500$\,ms $\rightarrow$ $14.0,14.9,54.3,103.7,504.1$\,ms) and the leak
reconciles to exactly zero (Table~\ref{tab:asyncm1}). Duplicated events are suppressed
idempotently; a \emph{lost} event leaks permanently. Whether a straggler looks lost or
merely late is a property of the observation horizon, not of the architecture, and the
table says so.

The B0 result is the one that changes an architectural conclusion. We issue requests
\textbf{strictly sequentially}, $20$\,ms apart, so no two are ever in flight together ---
any over-serving therefore \emph{cannot} be a concurrency race. Over-serving nonetheless
appears once $D$ reaches $100$\,ms and reaches \textbf{4 requests over a 2-request budget}
at $D=500$\,ms, with the balance driven negative (Table~\ref{tab:asyncb0}).
\textbf{Decoupling settlement converts a timing race into an architectural window: an
atomic guarded decrement --- the entire B0 defense --- provides nothing if it lands after
the next authorization has already read the balance.} The sufficiency condition of
\S\ref{sec:sufficiency} must therefore be read as requiring atomicity \emph{on the path
that authorizes}, not merely somewhere in the pipeline.

M2, by contrast, is untouched: leakage efficiency is identical ($0.5823$) at every delay,
confirming the analytic independence of usage authority from settlement timing.

"""

if "\\section{Formal Verification}" not in s:
    s = s.replace("\\section{Defense Sufficiency Conditions}", FORMAL + "\\section{Defense Sufficiency Conditions}", 1)

if "A real serving stack" not in s:
    s = s.replace("\\subsection{Lifecycle failure modes}", EXTERNAL + "\\subsection{Lifecycle failure modes}", 1)

# Pull in the generated tables next to the text that discusses them.
if "table_real_stack_m1.tex" not in s:
    s = s.replace("\\subsection{Lifecycle failure modes}",
                  "\\input{../results/tables/table_real_stack_m1.tex}\n"
                  "\\input{../results/tables/table_real_stack_m2.tex}\n"
                  "\\input{../results/tables/table_cached_split.tex}\n"
                  "\\input{../results/tables/table_async_m1.tex}\n"
                  "\\input{../results/tables/table_async_b0.tex}\n\n"
                  "\\subsection{Lifecycle failure modes}", 1)

if "table_formal_mapping.tex" not in s:
    s = s.replace("\\section{Defense Sufficiency Conditions}",
                  "\\input{../results/tables/table_formal_mapping.tex}\n\n"
                  "\\section{Defense Sufficiency Conditions}", 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
