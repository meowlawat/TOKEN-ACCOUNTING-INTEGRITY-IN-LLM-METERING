# Final Reviewer Response

Three simulated hostile reviews of the hardened manuscript. For each reviewer we state
the **strongest** objection they can raise, judge whether it is **valid**, point to the
**exact manuscript location** that addresses it, name the **remaining limitation**, and
classify the response as **empirical**, **theoretical**, or **scope-limiting**.

Not every objection is defeated. Where an objection survives, it is recorded as such and
also appears in Threats to Validity.

---

## REVIEWER 1 — Novelty

### Strongest objection
> "Strip away the framing and this is CWE-807 (trusting client input), a classic
> check-then-decrement race, and a known streaming-disconnect bug. The individual
> mechanisms are all documented — one of them in a public GitHub issue you cite
> yourself. Where is the new security knowledge?"

**Valid? PARTIALLY — and we concede the premise explicitly.** The objection is correct
about the *primitives* and incorrect about the *contribution*. We state in the abstract,
introduction, discussion and novelty matrix that no primitive-level novelty is claimed,
that B0 is a known baseline, and that M1/M2 are systematization and measurement.

**Where addressed:** §1 (Introduction, "We are deliberately adversarial about our own
contribution", which cites the very artifacts a reviewer would use against us);
§9 Discussion, paragraph *"Is this not just CWE-807 plus a race plus known streaming
bugs?"*; `paper/novelty_matrix.md`; `paper/novelty_reattack.md`.

**What survives the objection (the actual contribution):**
1. a unified accounting model in which three otherwise-unrelated failures are the *same*
   integrity property violated at different points of one request lifecycle;
2. a taxonomy whose separation is **experimentally demonstrated**, not editorial — the
   concurrency contrast (B0 scales, M1/M2 do not) is evidence that the dimensions are
   genuinely distinct;
3. the M1 ablation showing solvency and accounting integrity are **orthogonal** and need
   different primitives — this does not follow from "there is a streaming bug";
4. the M2 ablation isolating **computation from authority**: an architecture that
   recounts correctly still leaks $0.583$;
5. a **common measurement** (leakage, leakage efficiency, ASR, detectability, invariant
   violations, defense overhead) applied uniformly across all three dimensions, which no
   single prior source provides.

**Remaining limitation:** the contribution is type-B (systematization/measurement). A
venue that requires primitive-level novelty can still reject on that basis alone, and we
say so in the publication assessment.

**Response type:** SCOPE-LIMITING (concede novelty level) + EMPIRICAL (the ablations and
the concurrency contrast are new evidence, not new primitives).

**What we deliberately do NOT say:** that practitioners or industry believed a recount
was sufficient. We never established such a belief. We say only that *in the evaluated
architecture, recounting without authority did not prevent the leakage.*

---

## REVIEWER 2 — Scale / external validity

### Strongest objection
> "One host, one Uvicorn worker, loopback networking, a mock generator for most
> experiments, and a 135M-parameter CPU model. The headline defense-cost number
> (0.014–0.019%) is measured on a toy. Nothing here tells me how a real provider behaves,
> so the performance conclusions are unusable."

**Valid? YES for the performance conclusions; NO for the accounting conclusions.** This
is the objection we consider most damaging, and we do not attempt to defeat it — we bound
the claim instead.

**Where addressed:** §8 Defense Evaluation, "What the strongest defense costs", which
reports three levels and states that each answers a *different* question; §10 Threats to
Validity (Internal + External); `paper/tokenizer_benchmark_methodology.md`; the abstract,
which qualifies the figure as *"in the tested local SmolLM2-135M CPU configuration"*.

**The precise claim structure:**
- *Accounting behaviour* (leakage, ASR, invariant violations, ablation outcomes) is
  **structural** — it depends on architecture and ledger semantics, not on hardware or
  model size. A larger model does not change whether an aborted stream is billed.
- *Performance* (recount cost) is **configuration-bounded**. We report standalone
  tokenizer cost (real, engine-dependent, linear in length), gateway cost under a
  zero-cost mock generator (which *exaggerates* relative recount cost because generation
  is free by construction), and one local real-model measurement as an external-validity
  check on the ratio.
- We explicitly do **not** defend 0.014–0.019% as universally representative, and the
  paper says the experiment "does not validate any commercial provider's billing
  behaviour."

**Remaining limitation:** no distributed serving, no multi-region, no batching, no GPU,
no commercial provider, one DB/cache family. Architectural generality is the single
largest gap and is the stated reason the publication assessment says *candidate with
revision* rather than ready for a Q1 journal.

**Response type:** SCOPE-LIMITING (primary) + EMPIRICAL (three-level measurement bounds
the ratio in one configuration rather than asserting it).

---

## REVIEWER 3 — Methodology / statistics

### Strongest objection
> "You claim leakage is 'invariant' to concurrency, then admit you excluded your
> high-concurrency data. That looks like discarding inconvenient measurements and
> keeping the ones that support the story. Also, reporting effects with zero variance and
> no p-values is not a statistical analysis."

**Valid? NO — but only because the manuscript now distinguishes two things the objection
conflates.** The objection would be fair if the same data were both claimed and
discarded. It is not.

**Where addressed:** §10 Threats to Validity, paragraph *"Two different high-concurrency
questions"*; §7 Results, "Concurrency is not the mechanism"; `paper/statistical_analysis.md`.

**The two questions, separated:**
- **(a) Accounting integrity** was measured at $c = 1, 5, 20, 50, 100$ and **none of it
  was excluded**. These are deterministic functions of the ledger, not of throughput, and
  every trial passed ledger conservation at every level.
- **(b) Gateway throughput ratios** at $c\ge50$ are excluded from *headline performance
  claims* because the benchmark host became the limiting factor — repeat spread to 17%,
  a non-monotonic no-recount baseline, and single runs producing ratios $>1$ (physically
  impossible for strictly-added work). The excluded cells remain published in `results/`
  and are summarized in the paper rather than deleted.

**On the statistics:** zero-variance conditions are handled deliberately, not evasively.
The analysis script detects them and reports the constant plus complete separation,
explicitly declining a p-value, because a significance test against structurally-zero
variance is not meaningful. Where randomness genuinely exists (latency, throughput,
real-model timing) we use nonparametric tests (Mann-Whitney, Kruskal-Wallis, Spearman),
percentile bootstrap CIs, and Wilson intervals for proportions at extreme $p$, and we
report Cliff's delta alongside Cohen's $d$ because $d$ is undefined under zero variance.
No p-value is thresholded to support any conclusion; no post-hoc exclusions were made.

**Wording correction adopted:** the manuscript no longer says leakage is "mathematically
invariant". It says *"under fixed request volume in the tested architecture, per-request
leakage remained unchanged across concurrency levels 1–100"*, and separately explains why
the state model predicts this.

**Remaining limitation:** disconnect-timing jitter at $c\ge50$ changes delivered tokens
by whole-token increments between runs. The accounting identity holds exactly in every
case (verified in `paper/reproduction_consistency.md`), but the *raw* leak figure at those
levels is not bit-identical across runs, and the audit classifies it as
expected-nondeterminism rather than pretending it is exact.

**Response type:** THEORETICAL (the deterministic/stochastic distinction) + EMPIRICAL
(the identity check that reclassified the jitter) + SCOPE-LIMITING (performance claims
restricted to $c\in\{1,10\}$).

---

## Summary

| reviewer | objection valid? | response type | survives as a limitation? |
|---|---|---|---|
| R1 Novelty | partially (primitives are known) | scope-limiting + empirical | **yes** — type-B contribution |
| R2 Scale | yes, for performance claims | scope-limiting + empirical | **yes** — architectural generality |
| R3 Methodology | no (conflates two questions) | theoretical + empirical | minor — high-concurrency jitter |

Two of three objections survive as genuine limitations. Neither is concealed: both appear
in Threats to Validity, in `FINAL_RESEARCH_REPORT.md`, and in the publication assessment,
which rates the work workshop-ready and a Q1 *candidate with revision* rather than ready.
