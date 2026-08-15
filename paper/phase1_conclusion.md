# Phase 1 Conclusion — Novelty Gate

**Date:** 2026-08-15. **Posture:** adversarial (assume a skeptical *Computers &
Security* reviewer). This document decides whether the taxonomy can support a
security-paper contribution. Evidence: [`novelty_matrix.md`](./novelty_matrix.md),
[`false_positive_check.md`](./false_positive_check.md),
[`phase1_sources.json`](./phase1_sources.json).

**Headline:** the original 5-class taxonomy does **not** survive intact. Two classes
are killed, three survive only as **mechanism-based reframes** (none is a wholly
novel primitive), and one class is the known baseline. The defensible contribution is
a **systematization + reproducible measurement + defense evaluation** of *client-side*
LLM metering evasion — not the discovery of new attack primitives. Under that
framing the gate **passes**, with Class 3 flagged as fragile.

---

## A. Surviving classes (as reframes)

All three survive as **type B** (known/observed mechanism, not systematically studied
in LLM billing under the dishonest-client model with measurement + defense). Each is
experimentally testable on the existing Phase 0 rig and each has a bounded literature
gap.

### M1 — Metering-commit-timing evasion  *(was Class 1: stream-abort accounting gap)*
- **Mechanism (LLM-specific):** streamed inference is long-running; if the app commits
  the usage record *after* stream completion (post-hoc accounting), a client that
  aborts/disconnects mid-stream obtains delivered tokens with no committed debit — or,
  worse, triggers a reserve **refund** (new-api #5235).
- **Reframe axis:** *accounting-after-completion vs accounting-before-inference.*
- **Testable claim:** `$-leak` as a function of abort timing and metering architecture
  (post-hoc commit vs pre-authorized reserve-then-reconcile).
- **Gap:** the mechanism exists as one in-the-wild bug (new-api #5235) and an ops
  writeup (Cancellation Tax, framed as honest over-pay); it has never been modelled as
  an adversarial client class, measured, or defended systematically.
- **Confidence:** medium-high.

### M2 — Usage-record authority evasion  *(was Class 2: client-declared token trust)*
- **Mechanism (LLM-specific):** the billed unit is *tokens*; tokenization is
  nondeterministic across implementations; apps that meter on a client-side tokenizer
  estimate or a blindly-trusted upstream `usage` field let a client under-report.
- **Reframe axis:** *server-authoritative recount vs client/upstream-authoritative usage.*
- **Testable claim:** residual under-report margin a client can sustain below a
  server-side recount / anomaly threshold (the mirror of Token Inflation's measured
  50.85% *provider* over-report margin).
- **Gap:** the provider-over-report margin is measured; the symmetric client-under-report
  margin, and whether a server recount closes it, is not.
- **Confidence:** medium-high. **Cleanest measurable LLM-specific hook of the three.**

### M3 — Inference-cache billing evasion  *(was Class 3: cache / recompute dodging)*  — **WEAK**
- **Mechanism (LLM-specific):** gateway exact/semantic caches return responses with
  zero tokens/quota; if cache hits are unmetered and/or cache access is keyed on prompt
  content rather than entitlement, a client farms inference-equivalent value, or reads
  cached premium output without credits.
- **Reframe axis:** *inference idempotency vs billing idempotency; cache authorization
  vs cache correctness.*
- **Testable claim:** value obtained per metered charge under induced (semantic) cache
  hits; entitlement bypass via content-keyed cache.
- **Gap / risk:** overlaps solved idempotency (Stripe) and authorization (OWASP API3);
  the clean client-underpay story is the least developed. **Candidate for demotion or
  folding into M2/authorization.**
- **Confidence:** low.

**Unifying safety property (ties the survivors to the existing rig):** all three are
violations of *"no served/completed inference without a committed, non-refunded,
server-authoritative debit."* This is the exact invariant the Phase 0 class-6 rig
already checks — so the testbed generalizes to M1–M3 with modest extension.

---

## B. Killed classes

### Class 4 — Adversarial retry on shared quota → **KILLED (merge into baseline)**
Its mechanism is a non-atomic check-then-decrement TOCTOU race on a quota counter,
identical to Class 6. **CVE-2026-31873 (Tyk Gateway, 2026, CVSS 7.5)** is exactly this
(`GET` then `DECR`, concurrency multiplies the allowance); Kettle's single-packet
attack is the generic technique. "Shared pool / thundering herd / priority inversion"
is a deployment variant, not a distinct LLM-specific mechanism. **Reason to kill:**
type D (rebrand of the credit/quota-decrement race). Fold in as the baseline's
"shared/multi-tenant quota" variant.

### Class 5 — Entitlement-metadata tampering → **KILLED (remove)**
Textbook **OWASP API3:2023** (Broken Object Property Level Authorization / Mass
Assignment — inject `tier:premium`, tamper price) and **OWASP API1:2023** (BOLA).
Mature, generic, non-LLM. Reaching higher-tier *models* is BFLA/BOLA applied to model
routing. **Reason to kill:** type D. Keep at most a one-line note that model-tier
authorization is an instance of a solved class; do not claim it as a contribution.

---

## C. Revised taxonomy

Smaller and stronger. Direction fixed as **honest provider, dishonest client, goal =
receive metered inference while under-paying** — the quadrant the literature leaves
open.

| id | name | mechanism axis | status | prior art a reviewer cites |
|---|---|---|---|---|
| **M1** | Metering-commit-timing evasion | accounting after completion vs before inference | novel reframe (B) | new-api #5235; Cancellation Tax |
| **M2** | Usage-record authority evasion | server recount vs client/upstream-declared usage | novel reframe (B), strongest | CWE-807; Token Inflation |
| **M3** | Inference-cache billing evasion | inference vs billing idempotency; cache authz | novel reframe (B/E), weak | Stripe idempotency; Auditing Prompt Caching |
| **B0** | Credit/quota-decrement race | non-atomic check+decrement TOCTOU (incl. shared pools) | **BASELINE (known)** | Kettle 2023; CVE-2026-31873 |

Removed: old Class 4 (→ B0 variant), old Class 5 (→ OWASP, out of scope).
All four are unified by the single safety property in §A.

---

## D. Research gap (bounded statement — for the paper's intro/related work)

Existing security work on LLM billing establishes two directions. First, a dishonest
**provider** can overcharge an honest client: CoIn (2025) and Invisible Tokens,
Visible Bills (2025) formalize hidden-token quantity inflation and quality downgrade
and build third-party auditors, and Token Inflation (2026) measures that tokenization
ambiguity alone permits ~50.85% over-reporting below detection and hidden-reasoning
inflation up to ~1469%. Second, a third party can inflate a **victim's** bill:
Denial-of-Wallet / Economic Denial of Sustainability (OWASP LLM10) and LLMjacking
(Sysdig, 2024) drive unsustainable spend or run inference on stolen credentials. Both
directions assume the *client* is honest (or is an impersonated victim).

What this literature does **not** establish is the inverse: a *legitimate but
dishonest client* exploiting LLM-billing-specific weaknesses to obtain metered
inference while under-reporting or evading payment. The enabling mechanisms exist, but
only outside a unified LLM-billing frame and without adversarial measurement: the
stream-abort/refund gap appears as a single deployed-gateway bug (new-api #5235) and
an operations writeup (the "Cancellation Tax," framed as honest over-pay, not client
fraud); "trust the reported token count" is the generic CWE-807 with an unmeasured
LLM instantiation; concurrent quota-decrement races are a known web-race primitive
(Kettle 2023) with a recent CVE (Tyk CVE-2026-31873); cache/idempotency reuse is a
deliberately-built cost-saving feature (semantic caching, Stripe idempotency); and
plan tampering is OWASP API3:2023.

Concretely, **no prior work evaluates client-side LLM metering evasion under a
dishonest-client threat model on a controlled testbed with a common measurement
(`$-leak`, attack-success-rate, detectability) across metering architectures, paired
with server-side defenses and their latency/throughput overhead.** Prior work
establishes *provider-side over-charge auditing* (CoIn, Invisible Tokens, Token
Inflation) and *availability/economic exhaustion* (DoW, LLMjacking), but does not
measure *client-side under-payment* under threat model *T = honest provider / dishonest
client* using measurement *M = ($-leak, ASR, detectability, defense overhead)*.

*Uncertainty:* this is a bounded negative from targeted search (which returned only
provider-inflation, DoW, credential theft, and performance benchmarking), not a proof
of non-existence. The framing must therefore claim *systematization + measurement*,
not *first discovery*.

---

## E. Candidate paper contribution (for abstract/intro)

1. **A taxonomy and unifying safety property for client-side LLM metering evasion.** We
   define the honest-provider/dishonest-client quadrant left open by provider-inflation
   and Denial-of-Wallet work, and reduce three LLM-specific evasion mechanisms
   (metering-commit-timing, usage-record authority, inference-cache billing) plus the
   known credit/quota-decrement race to a single invariant: *no served inference
   without a committed, non-refunded, server-authoritative debit.*
2. **A reproducible, vulnerable-by-construction testbed** (FastAPI + Postgres + Redis +
   deterministic mock LLM, runs on commodity hardware, no GPU) with per-request
   auditable ledgers, and a measurement rig reporting `$-leak`, request/trial ASR,
   detectability, and defense overhead — already validated end-to-end on the baseline
   credit-decrement race (class-6, integrity-checked over 420 trials).
3. **Adversarial measurement of the two strongest mechanisms** — the stream-abort/refund
   commit-timing gap (grounded in a real deployed-gateway bug, new-api #5235) and the
   client-under-report margin under tokenization nondeterminism (the mirror of Token
   Inflation's provider-over-report measurement) — quantifying leakage across post-hoc
   vs pre-authorized metering architectures.
4. **Server-side defenses with measured cost:** pre-authorization/reserve-before-inference
   and reconcile-on-completion (M1), authoritative server-side recount (M2), and atomic
   compare-and-decrement (B0, already implemented), each evaluated for latency/throughput
   overhead and against the safety property.

*If reviewers reject M3:* the paper still stands on M1 + M2 + the baseline as a focused
measurement paper on **metering-commit-timing and usage-authority evasion**.

---

## Phase 1 gate (verbatim block reproduced at end of report)

- Surviving *distinct, experimentally-testable, LLM-specific* mechanisms: **3** (M1,
  M2, M3) — of which 2 are solid and 1 (M3) is weak — plus a validated baseline (B0).
- Credible literature gap: **yes**, bounded (§D).
- Novel *primitives*: **0** (all survivors are type-B reframes). The contribution is
  systematization + measurement + defense.

**Decision: PASS** — via the clause "revised taxonomy contains at least 3 distinct,
experimentally-testable LLM-specific mechanisms with a credible literature gap." The
pass is **conditional** on repositioning the paper as a systematization/measurement
contribution (not novel-primitive discovery) and is robust to losing M3 (M1 + M2 + B0
remain a viable focused paper). Proceed to Phase 2 **only** under that framing.
