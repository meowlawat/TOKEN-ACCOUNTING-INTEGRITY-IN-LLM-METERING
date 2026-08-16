# Phase Q — Blind Review Simulation (three adversarial reviewers)

Written after all experiments. Each objection is stated at full strength, then answered
with the evidence that exists (or conceded). Unresolved items are marked **✗ OPEN** and
are repeated verbatim in `threats_to_validity.md` and the final report. Nothing is
hidden.

---

## REVIEWER A — Security

**A1. "This is generic web/API security wearing an LLM costume."**
Partly conceded, and we say so in the paper. B0 *is* generic (a quota race) and is
labelled a known baseline, not a contribution. The LLM-specific content is in M1 and
M2: M1 exists because inference is *streamed and long-running*, so value is delivered
incrementally for hundreds of milliseconds to minutes before any commit point — a
window a request/response CRUD API does not have. M2 exists because the billed unit is
a *multi-category token vector* (input/output/cached/reasoning) produced by a
nondeterministic tokenizer, and our formal result is precisely that which manipulation
succeeds depends on the *pricing basis* over that vector (Table `table_m2_formal`).
Neither reduces to "validate your inputs" without losing the measured structure.
**Gate C test applied explicitly:** would the attack work unchanged against a non-LLM
API? B0 yes → baseline. M1/M2 no → retained.

**A2. "Weak novelty — these are known bugs."**
Conceded and stated in the abstract, introduction, `novelty_matrix.md`, and
`novelty_reattack.md`. M1 has a deployed instance (new-api #5235); M2's principle is
CWE-807 with a deployed mitigation (aperture #247); practitioner guidance already warns
about disconnect-induced token leakage. We claim **systematization + measurement +
ablation**, never discovery, and never "first". The re-attack (Phase P) additionally
surfaced a *fourth* adversary axis (dishonest intermediary: AEX, gateway-path
provenance) which we now present rather than implying the field is empty.

**A3. "The attacker is unrealistic / over-powered."**
The attacker holds exactly six capabilities (C1–C6 in `threat_model.md`), each mapped
to the harness component that exercises it: request payloads and client-declared usage,
permitted headers, concurrency, connection lifecycle, retries, and observation of its
own account. It cannot touch TLS, the database, Redis, the filesystem, the inference
backend, provider metadata, or server code. Every leak we report is therefore
attributable to the provider's own accounting design, not to a compromise.

**A4. "The defenses are trivial — atomic UPDATE, recount, reserve."**
The defenses are ordinary; the *finding* is which one is load-bearing. The ablation
shows (i) abort-inclusive finalization closes M1's integrity violation **with or
without** a reservation, while reservation independently closes *solvency* (removing it
drives the balance to $-0.32$ under a constrained budget); and (ii) **performing** a
recount is insufficient — `client_logged` computes an authoritative recount and still
leaks at efficiency $0.595$ because billing ignores it. "Recount works" would have been
the trivial claim; "recount must be the billing basis, and finalization not reservation
closes integrity" is the non-trivial one.

**A5. "Detectability is a footnote, not a result."**
Addressed: `table_detectability` classifies every mechanism/architecture across five
evidence sources with a D0–D3 level and a latency column, and yields an actionable
finding — merely *logging* a recount moves an M2 leak from D0 (invisible) to D1
(reconcilable) at negligible cost, an intermediate step for operators who cannot
re-architect billing.

---

## REVIEWER B — Systems

**B1. "The generator is a mock; the whole thing is a toy."**
This was the largest gap and is now closed by a *local real-model external-validity
experiment* (SmolLM2-135M, greedy CPU decoding, exact-length prompts at 128/1024/4096
tokens). Result: the authoritative recount is **0.012–0.016 % of end-to-end** at every
context size, with bootstrap CIs. Crucially this *contradicts* the mock-gateway
measurement (where recount cost up to 95 % of throughput) and we explain why: with a
zero-cost generator, tokenization is the entire request. We report all three levels
(standalone, mock-gateway, real-model) rather than the most flattering one.
**✗ OPEN:** the model is small and CPU-only; it bounds a *ratio*, and says nothing about
any commercial provider's serving stack.

**B2. "Single uvicorn worker — you measured your own bottleneck."**
Acknowledged in-paper: tokenization is CPU-bound and blocks the event loop, so the
gateway recount numbers are an explicit **upper bound**; a multi-worker or thread-pool
deployment amortizes it. This is also why the real-model experiment matters — it
removes the single-worker confound from the headline ratio.

**B3. "Loopback on Docker Desktop; the ~48 ms floor swamps your signal."**
Stated as a confound in `tokenizer_benchmark_methodology.md` §8. It makes the gateway
ratios *conservative* for small inputs (understating relative recount cost), and we
therefore report the server-measured tokenization component separately so the tokenizer
conclusion is not contaminated by transport.

**B4. "High-concurrency numbers are noise."**
Agreed, and now measured: repeat spread reaches 17 % of the median at $c\ge50$ and the
no-recount baseline is itself non-monotonic. We switched to median-of-3-repeats, and the
paper treats **only $c=1$ and $c=10$ as defensible**, labelling higher levels capacity
observations. (Single-run data had produced impossible ratios $>1$; that is why the
repeats exist.)

**B5. "Tokenizer benchmark doesn't match what the gateway runs."**
Both now use the same engines and the same artifact revisions
(`hf-internal-testing/llama-tokenizer` @ `d02ad6c…`, SHA-256 recorded; tiktoken vocab
fingerprint recorded), and the container runs them offline from a mounted cache. The
benchmark additionally verifies `len(encode(text)) == target` for **every** cell
(100/100), because the same text does not produce the same count across tokenizers.

**B6. "No scalability story."**
Conceded. Single node, no multi-tenant contention, no load balancer. **✗ OPEN.** We
scope every claim accordingly and never assert internet-scale behaviour.

---

## REVIEWER C — Methodology / Statistics

**C1. "Sample sizes look arbitrary."**
They are derived, not copied: `power_analysis.py` reports the *measured* dispersion and
the reps needed for a target precision; the tokenizer benchmark uses an adaptive budget
(`reps = clamp(1.5 s / probe, 30, 300)`) with the actual count stored per cell. The
leak magnitudes are deterministic (std $=0$), so the binding constraint is proportion
precision, which we report as Wilson intervals.

**C2. "Confidence intervals on deterministic quantities are meaningless."**
Agreed — and this is handled explicitly rather than papered over. `statistical_analysis.py`
detects zero-variance groups and prints "DETERMINISTIC constant … variance structurally
0", declining to compute a p-value, and reserves nonparametric tests (Mann-Whitney,
Kruskal-Wallis, Spearman) and bootstrap CIs for quantities that genuinely vary.

**C3. "p-hacking / cherry-picking / post-hoc hypotheses."**
No p-value is thresholded for a conclusion anywhere. The taxonomy was *reduced* by
evidence (M3 killed at its gate; old classes 4–5 killed in Phase 1), never grown to fit
results. The concurrency hypothesis was fixed before the sweep and returned a **negative**
result, which we report as a headline rather than burying.

**C4. "Dependent trials / shared state."**
Each cell provisions its own trial with a reset balance; ledger conservation is asserted
per trial. Request volume is held **constant** across concurrency levels precisely so
that volume cannot masquerade as vulnerability, and both absolute and normalized
metrics are reported.

**C5. "Your metrics are ambiguous — 'leak' could mean anything."**
Defined formally in `accounting_state_model.md` §5: $\mathrm{Leak}(r)=V(r)-N(r)$ with
$N=D-F$, and integrity as $V\le N$ with an explicit legitimacy condition on refunds.
The cross-validation additionally exposed a real ambiguity — signed vs
under-payment-only aggregation — which we now report as two distinct quantities after an
independent checker flagged three trials where the client was *overcharged*.

**C6. "How do we know your harness isn't just agreeing with itself?"**
Three independent defenses against that: (i) every summarizer re-derives leakage from
primitives and checks ledger conservation without trusting the app's bookkeeping;
(ii) `metamorphic_checks.py` proves the gates *fail closed* by injecting six corruption
types (12/12 detected) and validates 10 metamorphic properties; (iii)
`run_cross_validation.py` re-implements the M2 verdict in a module that shares no code
path with the gateway and compares 42 M2 + 16 M1 + 2 B0 cells (all agree). The
metamorphic suite also *caught one of our own unjustified assumptions* (price-tier
invariance held only under uniform scaling, not structural change), which we corrected
rather than suppressed.

**C7. "Defenses are only tested against your own scripted attack."**
Addressed by lifecycle failure injection: nine failure modes (disconnect at $t=0$ and
mid-stream, truncated stream, settle-window race, missing/delayed/duplicated usage
metadata, recount-engine failure). Every invariant violation lands on a vulnerable
architecture; hardened architectures survive all of them; recount failure is fail-closed.

---

## Unresolved after revision (**✗ OPEN**)

1. Real-model validation uses a **small CPU model**; it bounds a ratio and does not
   speak to commercial serving stacks (B1).
2. **Single-node, single-worker, loopback**; no multi-tenant contention or scale-out
   evidence (B2, B3, B6).
3. M1/M2 are **type-B reframings**, not new primitives; a venue demanding novel attack
   primitives can still reject on that basis alone (A2).
4. High-concurrency gateway measurements remain **noisy**; only low-concurrency columns
   are treated as evidence (B4).
5. Architecture coverage is **representative, not exhaustive** (e.g. deferred batch
   reconciliation, which would land at D1 rather than D3, is not implemented).
