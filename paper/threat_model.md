# Threat Model

## Parties

- **Provider / application (honest).** Runs the LLM SaaS gateway, meters usage, and
  bills the client. It is not trying to overcharge (that is the orthogonal
  provider-inflation problem studied by CoIn, Invisible Tokens, Token Inflation).
- **Client (dishonest).** Holds a funded account and legitimate credentials. Its goal
  is to obtain metered inference value while paying less than the authoritative cost.
  It is *not* an impersonator (that is LLMjacking / credential theft) and *not* trying
  to exhaust a victim's budget (that is Denial-of-Wallet).

## Attacker model: concrete, application-layer

This is deliberately **not** a symbolic/cryptographic (Dolev-Yao) attacker. Nothing in
this study depends on reasoning about cryptographic protocol messages; the adversary
is an ordinary authenticated API client that behaves dishonestly at the application
layer. Every capability below is **actually exercised by the attack harness** — we
grant no capability we do not use.

### Capabilities (with the harness component that exercises each)

| # | Capability | Exercised by |
|---|---|---|
| C1 | Compose arbitrary **request payloads** to endpoints it is authorized to call, including any client-declared usage fields | `attacks/m2_usage_authority.py` (declared usage vector: under-report a subtotal, drop a category, reclassify to a discounted category, desynchronize total from subtotals, rounding shave) |
| C2 | Set **permitted request headers** (its own API key, content type) | all harness modules |
| C3 | Choose **request concurrency** and sustained offered load | `experiments/run_m1.py`, `run_m2.py` (worker-pool), `attacks/class6_credit_race.py` (burst) |
| C4 | Control the **client connection lifecycle** — in particular, close/abort a streaming response at an arbitrary point | `attacks/m1_stream_abort.py` (abort after *k* delivered tokens) |
| C5 | **Retry** and re-issue requests | worker pools re-issue; B0 burst repeats |
| C6 | Observe **its own** responses, latencies, and its own account balance | all runners; `/admin/accounts/{id}` for its own account |

### Explicitly NOT granted (and not needed)

- **Cannot compromise TLS** or observe/modify other parties' traffic.
- **Cannot access the database** directly (no SQL access, no Postgres credentials).
- **Cannot access Redis internals.**
- **Cannot access the gateway filesystem** or read server configuration/secrets.
- **Cannot compromise the inference backend** or influence what the model generates
  beyond supplying a normal prompt.
- **Cannot forge authenticated upstream/provider usage metadata** — the provider is
  honest by assumption; provider-side dishonesty is the orthogonal problem studied by
  CoIn / Invisible Tokens / Token Inflation.
- **Cannot alter server code**, configuration, or the metering architecture. (The
  architecture is a *property of the deployment under test*, selected by the
  experimenter to compare designs — never something the attacker chooses at runtime.)
- **Cannot read or write another tenant's data**; no cross-tenant side channels.
- **Cannot steal credentials or impersonate another principal** (that is LLMjacking).

### Consequence for interpreting results

Because the attacker holds only C1–C6, every leak measured in this study is
attributable to an **accounting-design defect in the honest provider's own metering
pipeline** — not to a compromise. That is what makes the defenses purely server-side:
each one removes the defect without needing to authenticate or constrain the client
any further.

## Goal and success condition

The client succeeds on a request `r` when it receives inference value `C(r)` but the
account is net-charged less than `C(r)`:

```
Leak(r) = S(r) · C(r) − NetDebit(r),      NetDebit(r) = committed_debit(r) − legitimate_refund(r)
```

A positive `Leak(r)` is under-payment. The safety invariant the provider wants is

```
S(r) = 1  ⇒  NetDebit(r) ≥ AuthoritativeCost(r)
```

("no served inference without a committed, non-refunded debit covering it"), and the
system-level accounting-conservation identity

```
Σ committed_debits (net of refunds)  =  initial_balance − final_balance.
```

## Scope of the study

Three LLM-relevant metering dimensions are evaluated against this threat model:

- **M1 — metering-commit timing:** when is the charge irrevocably committed relative
  to inference delivery? (attacker lever: abort/disconnect timing)
- **M2 — usage-record authority:** who authoritatively sets the billed quantity?
  (attacker lever: the client-declared usage vector)
- **B0 — credit/quota-decrement race (baseline, known):** is the check-and-decrement
  atomic? (attacker lever: concurrency)

M3 (inference-cache billing) was killed at its decision gate (see `m3_decision.md`);
old classes 4 and 5 were killed in Phase 1 (quota race = B0; entitlement tampering =
OWASP API1/API3).

## Ethics boundary (hard rule)

All attacks run only against the locally-built, vulnerable-by-construction testbed.
No third-party, live, or production system is probed; no real credentials, user data,
or provider billing APIs are used. Every attack is paired with a defense.
