# FINAL RESEARCH REPORT
## Token-Accounting Integrity: Client-Side Metering Evasion in LLM-Powered Applications

Date: 2026-08-15. Everything below traces to literature evidence, source code, or raw
experimental data in this repository; hypotheses are labeled as such.

---

## Executive conclusion

We set out to study whether a *dishonest client* can obtain LLM inference value while
under-paying an *honest provider* — the one quadrant of LLM-billing security that prior
work (provider-overcharge auditing; Denial-of-Wallet; LLMjacking) leaves open. The
answer is **yes, systematically, and the failures reduce to a single safety invariant**:
*no served inference without a committed, non-refunded, server-authoritative debit.*

We were adversarial about our own novelty and it cost us classes: of the original five
proposed "novel" classes, **two were killed in the Phase 1 literature audit** (quota
race = baseline; entitlement tampering = OWASP), **one was killed at its Phase 2
decision gate** (inference-cache billing reduces to idempotency + authorization), and
**two survive only as mechanism reframes, not new primitives** (metering-commit timing;
usage-record authority). We built a reproducible testbed, implemented vulnerable and
hardened architectures for both surviving mechanisms plus the baseline, and measured
leakage, attack success, detectability, and defense overhead with per-request-ledger
integrity gates that pass on every trial. The honest contribution is **systematization +
measurement + defense**, not the discovery of new attacks.

---

## Final taxonomy

| id | name | status | evidence |
|---|---|---|---|
| **M1** | Metering-commit timing | SURVIVES (reframe, type B) — implemented + measured | new-api #5235; Cancellation Tax |
| **M2** | Usage-record authority | SURVIVES (reframe, type B, strongest) — implemented + measured | CWE-807; aperture #247; Token Inflation (mirror) |
| **M3** | Inference-cache billing | **KILLED at decision gate** | idempotency (Stripe) + cache authz + billing policy |
| **B0** | Credit/quota-decrement race | BASELINE (known) — validated in Phase 0 | Kettle 2023; CVE-2026-31873 |
| — | Adversarial retry on shared quota (old C4) | KILLED → merged into B0 | CVE-2026-31873 |
| — | Entitlement-metadata tampering (old C5) | KILLED (Phase 1) | OWASP API1/API3:2023 |

Unified by one invariant and one defense pattern: move the authoritative, irrevocable
accounting event **server-side** (atomic decrement / reserve-reconcile / server recount).

---

## Experimental evidence (main numerical findings)

Integrity: independent re-derivation from the per-request ledger passes with **0
problems** over **420 B0 trials + 840 M1 records + 1440 M2 records**; **every trial
reconciles** (Σ net-debit == initial − final); controls pass **19/19 (B0)** and
**16/16 (M1/M2)**.

- **B0 (baseline):** vulnerable leaks for concurrency ≥ 2 (never at 1); trial-ASR 1.0;
  per-trial leak $2.871 at concurrency 30, $4.851 at 50; hardened atomic decrement
  leaks **$0** at all concurrency.
- **M1 (commit timing), medium tier, per request:** vulnerable `post_completion` and
  `reserve_refund_on_abort` — request-ASR **1.00 [0.72,1.00]**, invariant-violation 1.00
  at every abort point before completion; mean leak rises $0.0045 → $0.054 (50%) →
  **$0.096 (90%)**, then **$0 at completion**. Safe `pre_debit`/`reserve_reconcile` —
  request-ASR **0.00**, leak **$0** everywhere.
- **M2 (usage authority), medium tier, leakage efficiency (fraction of value evaded):**
  client-authoritative — 90% output under-report **0.58**, total/subtotal mismatch under
  flat total pricing **0.74**, drop-reasoning 0.32, reclassify-to-cached 0.31; the
  *exploitable manipulation set depends on the billing basis* (category vs total).
  Server-authoritative (`server_recount`, `hybrid_reconcile`, `upstream`) — **0.00**
  across all 8 manipulations; detection D3.
- **Defense overhead (RQ4):** M1 reserve-reconcile **+9.8 ms** mean (~few %); M2
  server-recount **+0.1 ms** (mock; production tokenizer cost NOT captured).

---

## Strongest result

**Usage-record authority (M2) with the billing-basis finding.** On a controlled testbed
with realistic multi-category usage, a client-authoritative meter leaks up to 58–74% of
the true inference value, and — the non-obvious part — *which* manipulation succeeds is
determined by the server's billing basis (category-wise vs flat-total pricing), while a
single server-side recount neutralizes the entire manipulation catalogue at negligible
DB cost. It is measured, mechanically re-derived, and paired with a working defense.

## Strongest limitation

**The M2 defense's real cost is unmeasured.** The deterministic mock makes server-side
recount nearly free (+0.1 ms); in production the recount is a real tokenizer pass whose
cost is model/tokenizer-dependent. Until measured against a real tokenizer, the "recount
is cheap" claim is testbed-only. (Secondary: mechanisms are type-B reframes, not novel
primitives; M1/M2 are not evaluated under concurrency.)

## Novelty assessment (honest)

- **Novel primitives: none.** All mechanisms are known outside a unified LLM-billing
  frame (M1: new-api #5235 + Cancellation Tax; M2: CWE-807 + aperture #247; B0:
  Kettle/Tyk).
- **Novel and defensible:** the *systematization* (one invariant across commit-timing,
  usage-authority, and the race baseline), the *reproducible measurement* (leakage
  efficiency / ASR / detectability across architectures and price tiers), the
  *billing-basis-dependent attack surface* result, and the *defense + overhead + detection
  spectrum* evaluation. Bounded-negative gap claim: we found no prior systematic study of
  client-side LLM metering evasion in our targeted corpus (not a proof of non-existence).

---

## Reproducibility (exact commands)

```bash
# from a clean checkout, Docker running, host has: httpx numpy matplotlib
bash scripts/reproduce_all.sh          # (or) powershell scripts/reproduce_all.ps1
# individually:
docker compose up --build -d
python -m experiments.regression_class6            # 19/19 PASS
python -m experiments.regression_m                 # 16/16 PASS
python -m experiments.run_class6 --affordable 10 --concurrency 1 2 5 10 20 30 50 --reps 30
python -m experiments.summarize_class6             # integrity PASS
python -m experiments.run_m1 --reps 10 && python -m experiments.summarize_m1
python -m experiments.run_m2 --reps 10 && python -m experiments.summarize_m2
python -m experiments.run_overhead
python -m experiments.figures && python -m experiments.tables && python -m experiments.power_analysis
(cd paper && tectonic main.tex && tectonic main.tex)   # -> paper/main.pdf
```

Outputs: `results/raw/` (raw JSON), `results/processed/` (summaries + integrity),
`results/figures/` (4 PNG), `results/tables/` (4 .tex/.md), `paper/main.pdf`.

---

## Reviewer objections (most likely rejections and how the paper answers)

1. *"Not novel — new-api #5235 already shows M1."* → We concede and reframe as
   systematization + measurement + defense; `novelty_matrix.md` states type-B openly.
2. *"Mock model isn't real inference; defense cost is fake."* → Stated as the primary
   threat to validity; overhead claims limited to DB-operation cost. (Partly unresolved.)
3. *"M2 under-report is trivial."* → Refuted by the multi-category model and the
   billing-basis result.
4. *"Statistics: CIs on deterministic quantities."* → We report points for deterministic
   leak and Wilson CIs only for proportions; sample size derived from measured dispersion.
5. *"Only single-node / HTTP/1.1 / no concurrency for M1/M2."* → Scoped in
   threats-to-validity; B0 already saturates the race axis. (Future work.)

Full self-critique: `paper/reviewer_attack.md`.

---

## Publication assessment (honest, not inflated)

- **Workshop (e.g., an LLM-security or systems-security workshop): READY.** A
  reproducible testbed, a clean systematization, real integrity-gated measurements, and
  defenses with overhead constitute a solid workshop paper today.
- **Q1 journal (*Computers & Security* tier): NOT YET.** Needs (a) a real-tokenizer
  overhead measurement for M2, (b) a combined-stress / concurrency evaluation of M1/M2,
  (c) ideally one realism experiment with a small local model, and (d) broader
  architecture coverage. Estimated 1–2 further iterations.
- **Top-tier conference (S&P/USENIX/CCS): NOT AT THIS SCOPE.** The type-B novelty and
  single-node testbed would draw novelty/scope rejections; would require a substantially
  larger measurement (multiple real gateways, real models, multi-tenant contention) and a
  sharper singular contribution.

Novelty confidence: **MEDIUM** (M2 strongest; M1 solid; both type-B reframes with a
credible but bounded gap).
