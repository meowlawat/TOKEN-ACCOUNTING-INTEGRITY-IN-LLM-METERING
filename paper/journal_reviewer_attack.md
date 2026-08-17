# Journal Reviewer Attack

Five hostile reviews of the *cross-architecture* version of this work. Each objection is
answered from **measured evidence**, and every objection that survives is recorded as a
limitation. No evidence is fabricated; where an answer is scope-limiting rather than
empirical, it is labelled as such.

---

## REVIEWER A — "This is generic API security."

> "Streaming aborts, trusting client input, and racing a counter are ordinary web-API
> problems. Rename the variables and this paper is about any metered REST service. Where
> is the LLM content?"

**Partly valid, and conceded in the manuscript.** We do not claim these are uniquely
LLM-possible mechanisms; B0 in particular is presented as a *generic* baseline precisely
because it would behave identically in any metered API.

**Answer from evidence.**
1. **We apply the test and let B0 fail it.** B0 is labelled a known baseline, is never
   counted as a contribution, and exists partly to *demonstrate* what a generic race
   looks like next to the other two dimensions.
2. **The dimensions are experimentally distinguishable, not editorial.** B0's leakage is
   created by concurrency (slope 0.099 per additional concurrent request, R² = 1.0000),
   while M1 and M2 per-request leakage did not change across concurrency 1–100 under
   fixed request volume. A generic-API framing does not predict that split; the
   lifecycle/authority model does.
3. **M1 needs progressive delivery.** The leak is a function of *value already streamed*
   before commitment: 0.0045 → 0.0285 → 0.0540 → 0.0960 as the abort moves from ~1 token
   to 90% of the stream, collapsing to 0.0000 at completion. A request/response API has
   no such interior.
4. **M2 needs token-vector pricing.** The exploitable manipulation set is a function of
   the *pricing basis over usage categories*: a total/subtotal mismatch is inert under
   category pricing (0.000) and maximal under flat-total pricing (0.741), while
   reclassifying output into a discounted cached category is the reverse. That result has
   no analogue where the billed unit is a scalar request count.

**Remaining limitation.** The mechanisms are combinations of known primitives. A venue
requiring primitive-level novelty can still reject; the contribution is
systematization + measurement + sufficiency analysis. **Response type: scope-limiting +
empirical.**

---

## REVIEWER B — "Single-worker results do not generalize."

> "Everything was measured inside one event loop. Real deployments run many workers behind
> a load balancer. Your accounting conclusions may be artifacts of having no true
> parallelism."

**This was valid, and it is now answered empirically.** We built the topologies and
re-ran the experiments.

**Answer from evidence.**

| topology | shape | evidence |
|---|---|---|
| single (control) | 1 uvicorn worker, no proxy | original matrix |
| multi-worker | nginx → **4** uvicorn workers (4 event loops) | full B0/M1/M2 matrix |
| distributed | nginx LB → **2 gateway containers × 2 workers** | reduced but matched matrix |

- **96 accounting cells** were compared against the single-worker control:
  **0 mismatches.** Differences are either exactly zero or bounded by the price of one
  delivered token, which is the disconnect-timing jitter already documented.
- **Load demonstrably spread.** Each ledger row records the serving process. In the
  multi-worker run, four distinct worker processes served M1 requests (101/164/79/136
  requests); in the distributed run both gateway containers served traffic.
- **B0 behaves the same everywhere.** Hardened leaks exactly 0 at every concurrency in
  every topology — *including across two separate containers* — because atomicity is
  enforced by the database, not by process locality. Distributed vulnerable reproduced
  the control exactly: 0.8910 at c=10 and 4.8510 at c=50.
- **Building the topology surfaced two real defects, which we report as findings rather
  than hiding:** (i) the B0 runtime posture was per-process state and would have reached
  only one of four workers — it now lives in Redis; (ii) four workers racing
  `create_all` at boot crashed with `UniqueViolation` on `pg_class` — now serialized with
  a PostgreSQL advisory lock. Both are genuine multi-worker deployment requirements.

**Remaining limitation.** All instances still run on **one physical host**, sharing one
PostgreSQL and one Redis. We have removed the single-event-loop and single-process
confounds; we have **not** tested multi-host networking, replica lag, cross-region
latency, or a partitioned datastore. **Response type: empirical, with a residual
scope limit.**

---

## REVIEWER C — "The second backend produces different conclusions."

> "You store the balance as a mutable row. Event-sourced billing systems don't. Your
> 'atomic decrement' defense is an artifact of that choice and will not transfer."

**Valid as a hypothesis; refuted by measurement.**

We implemented a second accounting backend behind the *same semantic interface*, so the
attack harness, architectures, and integrity gates are unchanged:

- **Backend A (`mutable`)** — one mutable `credits.balance` row; atomicity from a
  conditional `UPDATE ... WHERE balance >= :cost`.
- **Backend B (`ledger`)** — `credits.balance` is never mutated by the accounting path;
  every movement is an immutable row in `ledger_entries`, and the balance is **derived**
  as `opening_balance + SUM(delta)`. The atomic reserve becomes a conditional *append*
  serialized on an anchor row.

**Result: 17 of 17 strongest B0/M1/M2 cases produced byte-identical outcomes** — same
leakage, same leakage efficiency, same invariant-violation counts, same reconciliation
verdicts. Examples: `M2/client` 0.594 both; `M2/server_recount` 0.000 both;
`M1/post_completion/abort90` 0.0950/req both; `B0/vulnerable/c50` 5.1695 both;
`B0/hardened/c50` 0.000000 both.

This supports the paper's structural claim: the outcomes follow from *where*
synchronization, commitment and authority sit, not from how money is stored. The
sufficiency conditions in `defense_sufficiency.md` are stated over the accounting model,
and both backends are instantiations of it.

**Remaining limitation.** Two backends is two, not all. Both are single-datastore,
strongly-consistent designs. A backend with **eventual consistency**, sharding, or an
asynchronous settlement pipeline could break condition (B0-a) or (M1-a) and is untested.
**Response type: empirical, with an explicit generalization boundary.**

---

## REVIEWER D — "The formal model does not prove defense sufficiency."

> "You call these 'sufficiency conditions' but there is no theorem and no machine-checked
> proof. This is an empirical ablation dressed in formal notation."

**Substantially valid, and the manuscript now says so explicitly.**

`paper/defense_sufficiency.md` opens with the disclaimer that the arguments are
**model-level and deductive, not machine-checked, and not a universal theorem about
deployed systems**. It separates, per mechanism, what is sufficient *within the model*
from what is **implementation-specific** — for example:

- M1 requires that the terminal accounting event be *durable even under client
  disconnect*; the model states this, but our implementation achieves it with a
  cancellation-shielded settlement task. A framework that cancelled that task would
  satisfy the architecture on paper and violate the condition in practice.
- M2's `upstream` architecture satisfies the authority condition **only because the
  provider is honest by assumption** — under a dishonest-provider model it would not.
- B0's atomicity can be obtained by conditional UPDATE, by an anchor-row lock, or by
  serializable isolation with retry; the model requires the *property*, not a mechanism.

The document also states plainly what is **not** claimed: that no other sufficient
condition set exists, and that the conditions are sufficient in any deployed system.
What we do claim, and support: the conditions are sufficient in the model; removing any
one of them produces a measured violation in our implementation; and the conditions hold
across two topologies and two accounting backends.

**Remaining limitation.** No mechanized proof (TLA+, Coq, Alloy). A reviewer who requires
formal verification will find this insufficient, and we do not dispute that.
**Response type: theoretical, bounded — the honest answer is "argued, not proved".**

---

## REVIEWER E — "The economic analysis is synthetic."

> "Your dollar figures come from invented price tiers. They tell me nothing about real
> money."

**Valid about the dollars; that is why the dollars are not the headline.**

**Answer from evidence.**
1. **Scenario labelling.** Every dollar figure is explicitly a *scenario* value under
   synthetic tiers. We never present them as commercial pricing, and we use no real
   provider billing data.
2. **The headline metric is price-independent.** Leakage *efficiency* — the fraction of
   delivered value evaded — is invariant under uniform price scaling. Measured: efficiency
   is identical between the `low` and `medium` tiers (an exact ×10 uniform scaling) for
   every architecture/manipulation pair.
3. **We report which conclusions depend on pricing structure, not just scale.** The
   `high` tier deliberately changes the *ratio* (output/input 3 → 5), not merely the
   scale, and efficiency then shifts by at most 0.012. So: conclusions are invariant to
   price *level*; they shift slightly, and predictably, under a price *structure* change.
4. **Token-normalized measures are reported alongside** (leaked tokens, leakage per 1K and
   per 1M tokens) so a reader can substitute their own price vector.
5. This distinction was itself caught by our metamorphic suite, which initially asserted
   tier-invariance too strongly; we corrected the property rather than the data.

**Remaining limitation.** No validation against real commercial billing. Absolute
economic impact for any specific provider is **not** established, and the paper does not
claim it. **Response type: scope-limiting + empirical (normalized metrics).**

---

## Summary

| reviewer | objection | status after this work | survives as limitation? |
|---|---|---|---|
| A | generic API security | partly conceded; dimensions shown experimentally distinguishable | **yes** — type-B novelty |
| B | single-worker doesn't generalize | **answered empirically** — 96 cells, 0 mismatches, 3 topologies | **yes** — one physical host |
| C | second backend will differ | **refuted empirically** — 17/17 identical | **yes** — no eventual-consistency backend |
| D | no proof of sufficiency | conceded; model-level argument, clearly scoped | **yes** — no mechanized proof |
| E | synthetic economics | conceded on dollars; efficiency is price-invariant | **yes** — no real billing data |

All five objections leave a residual limitation. Two (B and C) moved from *open
weaknesses* to *bounded* ones by new measurement; three (A, D, E) are scope statements the
paper now makes explicitly rather than defending.
