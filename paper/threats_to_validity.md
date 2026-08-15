# Threats to Validity

## Construct validity

- **Mock model.** Token counts, timing, and "reasoning" tokens are synthetic. This is
  intentional for reproducibility, but it means the M2 server-recount defense is
  nearly free here; a real tokenizer pass is the true cost and is **not** measured.
  Absolute latencies reflect the mock's inter-token delay, so only *relative* overhead
  between architectures is meaningful.
- **Authoritative cost definition.** For M1 we define the value obtained as the cost of
  *delivered* tokens (what the client consumed). An alternative accounting (bill for
  tokens *generated* regardless of delivery) would change the operator-exposure story
  but not the client-evasion result; we record generated vs delivered so either view
  is derivable.
- **Synthetic price tiers.** Chosen to be shaped like cheap/mid/frontier models, not
  scraped from a provider. Leakage *efficiency* is tier-invariant, so conclusions do
  not depend on the exact prices; only absolute dollars do.

## Internal validity

- **Timing dependence.** M1 leakage tracks tokens delivered before disconnect; the
  disconnect-detection lag makes "abort at 0%" deliver ~1 token (small nonzero leak).
  This is reported, not hidden. The effect magnitude is deterministic (std = 0), so it
  is a property of the architecture, not noise.
- **Single-node PostgreSQL, one credit row.** No replica lag or cross-shard effects;
  results characterize a single primary under `READ COMMITTED`.
- **Observation locking (B0).** The vulnerable path uses `SELECT … FOR UPDATE` only to
  *observe* the pre-image; it does not repair the race (documented in
  `class6_methodology.md`).
- **Determinism.** Because the workload is deterministic, we do not manufacture
  variance; confidence intervals on leak collapse to points and we say so, reporting
  proportion CIs (Wilson) where the randomness (scheduling) actually lives.

## External validity

- **Architecture selection.** M1 (4) and M2 (6) architectures are representative, not
  exhaustive; real gateways may combine them or add reconciliation windows we did not
  model (e.g. deferred batch reconciliation → D1 rather than D3).
- **Local, single-client for M1/M2.** M1/M2 do not exercise concurrency (that is B0's
  axis); a production system faces all three simultaneously. We do not claim
  internet-scale or multi-tenant-contention results.
- **HTTP/1.1.** B0 uses ordinary concurrency, not HTTP/2 single-packet; the effect is
  already saturated (trial-ASR 1.0 for concurrency ≥ 2), so single-packet is not
  required, but tighter windows could only increase leakage.

## Novelty validity (the honest one)

- The **mechanisms are not new primitives** (type B). M1 is grounded in a deployed-
  gateway bug (new-api #5235) and an ops writeup; M2's principle is CWE-807 with an
  in-the-wild mitigation (aperture #247); B0 is Kettle/Tyk. The contribution is the
  **systematization + measurement + defense**, and the paper must not overclaim
  discovery. A reviewer who demands novel primitives should be pointed to the
  systematization/benchmark framing.

## Search validity

- The "no prior systematic study" claim is a **bounded negative** from targeted search
  (`phase1_sources.json`, `novelty_recheck.md`), not a proof of non-existence. We use
  "we found no prior work in our targeted corpus", never "nobody has studied this".

## Mitigations already applied

Integrity gates (independent re-derivation + accounting conservation on every trial),
control experiments that separate exploitation from ordinary behavior, data-driven
sample sizing, and raw-data-first pipelines so every figure regenerates from data.
