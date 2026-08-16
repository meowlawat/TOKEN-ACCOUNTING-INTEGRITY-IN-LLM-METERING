# Phase P — Related-Work Re-Attack (final novelty audit)

**Date:** 2026-08-16. Run *after* all experiments, before freezing the paper. Purpose:
find anything that would let a reviewer say "this is already known" and record the
exact overlap, the exact difference, and why the study remains useful anyway.

## New sources found in this pass

| source | what it is | adversary | overlap with us |
|---|---|---|---|
| **AEX: Non-Intrusive Multi-Hop Attestation and Provenance for LLM APIs** (arXiv 2603.14283, 2026) | signed attestation binding request→response at the API boundary, incl. streaming prefixes | untrusted **intermediary / shadow API** | none on billing. Explicitly *not* about usage measurement or payment integrity. |
| **Evidence-Bound Gateway-Path Provenance for Third-Party LLM Inference** (arXiv 2606.22560, 2026) | attested gateway runtime (Nitro enclave) binding policy, route, endpoint, **stream commitments**, completion metadata | **gateway operator** (route substitution, stream manipulation, forged provenance) | adjacent: it also "commits" to a stream, but for *authenticity*, not *economic commitment*. Does not model under-payment. |
| **Industry metering guidance** (UsageBox / Solvimon / Flexprice, 2026) | separates *gateway = enforcement point* from *meter = accounting point*; states retries, partial failures and **client disconnects must not cause double billing or token leakage** | n/a (practitioner advice) | **strong**: states our exact M1/M2 concerns as engineering advice. No threat model, no measurement, no defense evaluation. |
| **aperture #247** (lightninglabs, 2026) | strips `Accept-Encoding` so the usage tail is always parseable, treating a non-identity encoding as an error "rather than a silent zero-debit" | dishonest **client** | **strong on M2**: a real deployed mitigation against client-side usage evasion. |

## Effect on the taxonomy

**A third adversary axis exists and we must name it.** Prior work now covers:

1. dishonest **provider** → over-charge (CoIn, Invisible Tokens, Token Inflation),
2. third party → inflate a **victim's** bill (Denial-of-Wallet, LLMjacking),
3. dishonest **intermediary/gateway operator** → misroute, substitute, forge provenance
   (AEX, Evidence-Bound Gateway-Path Provenance),
4. dishonest **client** → under-pay ← **this paper**.

The earlier 2×2 framing was incomplete; the paper's related-work section must present
all four and not imply the field is empty.

## Per-mechanism overlap / difference / why still useful

### M1 — commitment timing
- **Exact overlap:** `new-api` #5235 is this failure in a deployed gateway; the
  "Cancellation Tax" writeup describes the same abort/decode mechanism; industry
  guidance explicitly warns that "client disconnects must not result in token
  leakage"; gateway-provenance work also commits to streams.
- **Exact difference:** all of the above are (a) single bug reports, (b) honest-operator
  cost framing, or (c) *authenticity* commitments. None models an adversarial client,
  none measures leakage as a function of abort position, and none separates which
  primitive closes the failure.
- **Why still useful:** we show leakage is a function of value delivered before commit
  (not of contention), and the ablation isolates *abort-inclusive finalization* as the
  load-bearing primitive, distinct from reservation which closes solvency instead.

### M2 — usage authority
- **Exact overlap:** CWE-807 is the generic principle; aperture #247 is a deployed
  mitigation for one instance (encoding-induced zero-debit); Token Inflation measures
  the *provider* over-report margin under tokenization ambiguity.
- **Exact difference:** nobody measures the *client* under-report margin, and nobody
  shows that the exploitable manipulation set is a function of the **pricing basis**
  (category vs flat-total) — our formal result.
- **Why still useful:** it converts "don't trust client input" into a measured,
  basis-dependent attack surface with a sufficiency result (recount must be *used*, not
  merely computed) and a detection spectrum.

### B0 — synchronization
- **Exact overlap:** complete. Kettle (2023) + CVE-2026-31873 (2026).
- **Exact difference:** none. We use it as a *known baseline* and never claim novelty.
- **Why still useful:** it is the control that makes the M1/M2 concurrency-invariance
  result meaningful — B0 is concurrency-created, M1/M2 are not.

## Language rules for the paper (enforced in the audit)

- Never "first", "novel attack", "nobody has studied".
- Use: *"we found no prior work in our targeted corpus that ..."*, *"to the best of our
  targeted search"*, *"we do not claim proof of non-existence"*.
- State plainly that M1/M2 are **type-B systematization/reframing** contributions and
  that B0 is a known baseline.

## Bounded gap statement (final)

Prior work establishes provider-side over-charge auditing, victim-side economic
exhaustion, and intermediary-side provenance attestation, and practitioner guidance
already warns that disconnects and retries must not cause token leakage. **We found no
prior work in our targeted corpus that evaluates client-side under-payment under an
honest-provider/dishonest-client threat model across representative metering
architectures with a common measurement (leakage efficiency, ASR, detectability,
defense overhead) and an ablation identifying which enforcement primitive closes which
property.** We do not claim proof of non-existence.
