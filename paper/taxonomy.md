# Taxonomy of Client-Side Metering Evasion

All mechanisms are unified by one safety property — *no served inference without a
committed, non-refunded, server-authoritative debit* — and differ in **which stage of
the metering pipeline** the integrity boundary sits.

```
        request ─▶ authorize ─▶ [M1: WHEN is the charge committed?] ─▶ inference/stream
                                                                        │
                                 [M2: WHO authoritatively counts usage?]│
                                                                        ▼
                              [B0: is the credit decrement ATOMIC?] ─▶ debit ─▶ response
```

## M1 — Metering-commit timing  *(novel reframe, type B; SURVIVES)*

*What happens when inference is delivered before billing is irrevocably committed?*
Four architectures span the design space:

| architecture | commit point | on abort | safe? |
|---|---|---|---|
| `pre_debit` | before inference | keep charge | yes (may overcharge) |
| `reserve_reconcile` | reserve→settle to delivered | reconcile to delivered | **yes (recommended)** |
| `post_completion` | after full completion | **no debit** | no |
| `reserve_refund_on_abort` | reserve→refund all on missing usage | **refund all** | no (new-api #5235) |

Attacker lever: disconnect after receiving most of the stream but before the commit.
Prior evidence: new-api #5235; the "Cancellation Tax."

## M2 — Usage-record authority  *(novel reframe, type B; SURVIVES — strongest)*

*Who authoritatively determines the billed usage quantity?* Six architectures span
client-authoritative → server-authoritative, giving a detection spectrum:

| architecture | billing basis | detection | safe? |
|---|---|---|---|
| `client` | client-declared (category) | D0 | no |
| `client_logged` | client-declared, recount logged | D1 | no |
| `client_total` | client-declared **total**, flat rate | D0 | no |
| `upstream` | honest provider metadata | D3 | yes (this threat model) |
| `server_recount` | server tokenizer recount | D3 | **yes (recommended)** |
| `hybrid_reconcile` | client + server reconcile/correct | D3 | yes |

Attacker lever: a manipulated usage vector (under-report a subtotal, drop a category,
reclassify to a discounted category, or make the declared total disagree with the
subtotals). Which manipulation pays off depends on the **billing basis** (category vs
total). Prior evidence: CWE-807; aperture #247 (encoding-induced silent zero-debit);
Token Inflation measures the mirror (provider over-report).

## B0 — Credit/quota-decrement race  *(KNOWN BASELINE — not a contribution)*

Non-atomic check-then-decrement TOCTOU on a credit/quota counter; concurrency
multiplies the allowance. Absorbs old Class 4 (shared/multi-tenant quota). Prior art:
Kettle single-packet (2023); CVE-2026-31873 (Tyk, 2026). Used to validate the rig and
to contrast a *generic* economic race with the *LLM-specific* accounting failures
(M1/M2). Gate C test — "would this attack work unchanged against a non-LLM API?" —
**B0: yes** (hence baseline); **M1/M2: no** (they depend on streaming inference and on
token-usage semantics, respectively).

## Killed

- **M3 — inference-cache billing:** killed at its decision gate (reduces to solved
  idempotency + generic cache authorization + a billing-policy choice). See
  `m3_decision.md`.
- **Old Class 4 (adversarial retry on shared quota):** merged into B0.
- **Old Class 5 (entitlement-metadata tampering):** killed in Phase 1 (OWASP
  API1:2023 / API3:2023).
