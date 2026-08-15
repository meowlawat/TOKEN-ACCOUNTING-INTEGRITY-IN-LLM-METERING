# Threat Model

## Parties

- **Provider / application (honest).** Runs the LLM SaaS gateway, meters usage, and
  bills the client. It is not trying to overcharge (that is the orthogonal
  provider-inflation problem studied by CoIn, Invisible Tokens, Token Inflation).
- **Client (dishonest).** Holds a funded account and legitimate credentials. Its goal
  is to obtain metered inference value while paying less than the authoritative cost.
  It is *not* an impersonator (that is LLMjacking / credential theft) and *not* trying
  to exhaust a victim's budget (that is Denial-of-Wallet).

## Attacker capabilities (what a realistic malicious client controls)

- Full control of its own HTTP requests: timing, concurrency, connection lifetime
  (it can disconnect/abort at any moment), request bodies, and any client-declared
  fields (e.g. a `usage` object or a client-side token estimate).
- It may send many requests, concurrently, and retry.
- It observes only its own responses and its own balance/among its own account state.

## Attacker limitations (explicitly NOT granted)

- Cannot read or write another tenant's data or the provider's server-side state.
- Cannot forge the provider's own upstream usage metadata (the provider is honest).
- Cannot break authentication or steal credentials.
- Cannot attack the network or other tenants; no side channels beyond its own timing.

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
