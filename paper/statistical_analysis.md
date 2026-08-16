# Statistical Analysis: Methods and Justification

All statistics cited in the paper are produced by the standalone script
`experiments/statistical_analysis.py` (scipy 1.15.3, statsmodels 0.14.5, numpy) and
written to **`results/tables/stats_output.txt`**. The paper cites that file. No
statistic is computed by hand, estimated, or transcribed from memory.

```bash
python -m experiments.statistical_analysis     # regenerates results/tables/stats_output.txt
```

---

## 1. The central methodological problem: much of this study is deterministic

The testbed is deliberately deterministic — identical prompt, identical seed, identical
code path, no sampling in the mock generator. Consequently many measured quantities have
**exactly zero variance**: e.g. M1 leak-per-request is `0.0528` in every cell at every
concurrency, and M2 leakage efficiency is `0.228` in every `client` cell.

For such quantities:

- A significance test is **not meaningful**. There is no sampling distribution; the
  observed value is the value. A p-value computed against zero variance is an artifact
  of the test's assumptions, not evidence.
- Cohen's *d* is **infinite** (pooled SD = 0 with different means). We report this
  honestly as *complete separation* rather than printing `inf` as if it were an effect
  size.
- Confidence intervals collapse to points, so reporting them would imply a precision
  claim that is true but vacuous.

The script therefore **detects zero-variance groups** and prints, verbatim:

```
NOTE: both groups have zero variance (deterministic outcomes). d is infinite by
      construction; the meaningful statement is complete separation:
      every vulnerable cell leaks X, every safe cell leaks Y.
      No hypothesis test is reported because there is no sampling variability.
```

This is a deliberate methodological choice, not an omission, and reviewers should read
it as such. Where a factor is a *perfect predictor* of the outcome (architecture →
leak), we report separation, not a model fit.

## 2. Where randomness genuinely exists

Three families of measurement do vary run-to-run, because they depend on OS scheduling,
network loopback, and CPU contention:

| quantity | source of variability |
|---|---|
| client-observed latency, gateway throughput | scheduling, event loop, Docker loopback |
| tokenizer call timing | CPU contention, cache state |
| real-model end-to-end timing | CPU contention, memory pressure |

These are **skewed and small-n**, so we use nonparametric methods rather than assuming
normality.

## 3. Tests used, and why each was chosen

| test / statistic | where used | why this one |
|---|---|---|
| **OLS linear regression** (`scipy.stats.linregress`) | B0 leak vs concurrency; M1 leak vs tokens delivered | The hypothesized relation is linear by construction (leak = k × units). We report slope, R², and p; R² = 1.0000 confirms the mechanism rather than merely "significance". |
| **Log–log regression** | tokenizer latency vs input length | Tests the *functional form*: slope ≈ 1 ⟺ linear scaling. This is the claim ("cost budgets as tokens × constant"), so we test the exponent, not a mean difference. |
| **Spearman rank correlation** | gateway throughput ratio vs tokenization time | Monotonic-but-not-necessarily-linear relation; robust to the heavy tail in throughput. |
| **Mann–Whitney U** | safe vs vulnerable latency; real-model posture comparisons | Two-sample, nonparametric, no normality assumption, valid for small n. |
| **Kruskal–Wallis** | leak across >2 concurrency levels | Nonparametric one-way comparison; used only when values are not all identical (otherwise reported as "NOT APPLICABLE — all values identical"). |
| **Wilson score interval** | trial-ASR, request-ASR | The correct interval for a binomial proportion at extreme p (our ASRs are 0.0 or 1.0, where the normal approximation is degenerate and would give zero width). |
| **Percentile bootstrap** (10,000 resamples, seed 1337) | recount/e2e fraction; mean leakage efficiency | Distribution-free CI for a median/mean on skewed, small-n timing data. |
| **Cohen's *d*** | architecture effects | Standard parametric effect size; reported alongside a nonparametric partner because *d* assumes comparable spread. |
| **Cliff's delta** | same comparisons | Nonparametric effect size in [−1, 1]; unlike *d* it remains finite and interpretable when variance is zero or highly unequal. |

## 4. What we deliberately do NOT do

- **No p-value is thresholded to support a conclusion.** No claim in the paper rests on
  "p < 0.05". Effect sizes and mechanism (R², slope, separation) carry the argument.
- **No ANOVA over the full factorial.** The design is deliberately not analyzed as a
  single omnibus model because several factors are perfect predictors (architecture →
  leak) which causes separation and makes coefficient estimates meaningless. We instead
  analyze factor-by-factor with the appropriate test and report where a factor explains
  *all* variance.
- **No hypothesis test on zero-variance data** (see §1).
- **No claim of normality** anywhere.

## 5. Interpreting the real-model throughput ratios

The real-model experiment produces ratios such as `1.054` (recount *faster* than no
recount), which is physically impossible for strictly-added work. Two consequences are
stated in the output and the paper:

1. The measurement noise band on these CPU-bound timings is roughly **±10 %**.
2. Because the recount fraction is **0.012–0.016 %** of end-to-end, the true effect is
   ~700× smaller than the noise band and is therefore **not resolvable** by this
   experiment — which is itself the finding: the recount is negligible relative to real
   generation. Large |*d*| values with sign flips across workloads are reported as
   evidence of drift, not of an effect.

## 6. Sample sizes

Chosen from *measured* dispersion, not convention (`experiments/power_analysis.py`):

- Deterministic quantities: variance is structurally 0, so the mean is pinned by a
  single observation; repetitions guard only against scheduling artifacts.
- The binding constraint is **proportion precision**: at n = 20 the Wilson interval at
  p = 0.5 is ±0.219, but our observed ASRs sit at 0 or 1 where the interval is tight
  ([0, 0.16] / [0.84, 1]). B0 uses 30 reps/cell for the same reason.
- The tokenizer benchmark uses an **adaptive** budget: `reps = clamp(1.5 s / probe, 30,
  300)`, with the actual count recorded per cell.
- The gateway benchmark uses **median of 3 independent repeats** per cell after single
  runs produced impossible (>1.0) ratios; repeat spread is reported per cell.

## 7. Reproducibility of the statistics

`stats_output.txt` records the library versions in its header, names the exact source
file for every section, and is regenerated from raw JSON on every reproduction run. If a
raw dataset changes, the statistics change with it — there is no manual step.
