# Hostile reviewer simulation — journal round

Four reviewers, each attacking from a different discipline. For every one: the strongest
objection they can actually make, whether it is valid, the evidence that answers it, what
weakness *remains*, and what changed in response.

The rule applied throughout: an objection is only "answered" if evidence in the artifact
answers it. Where nothing answers it, it stays open.

---

## Reviewer A — novelty

**Strongest objection.** *"None of this is new. Quota races are CWE-807 and a 2023
single-packet attack; refund-on-disconnect is a bug already filed against a deployed
gateway; 'don't trust client input' predates LLMs by thirty years. Strip the LLM framing
and you have a systematization of three known web-application defects."*

**Valid?** **Substantially yes, and the paper already concedes it.** No mechanism here is a
new primitive. The introduction says so in its second paragraph, names the prior art for
each mechanism, and labels B0 a known baseline rather than a contribution. Two of the
original five candidate classes were killed in the novelty audit and a third (M3) was
killed at a decision gate.

**Evidence that answers what remains.** The contribution is the *combination*, and three
parts of it are not available in the prior art:

1. **A unifying integrity property** over a request lifecycle that admits legitimate
   refunds, under which all three mechanisms are the same violation in different places —
   with the model checked, not asserted.
2. **The orthogonality result.** Reservation and abort-safe finalization are independent
   controls; each alone leaves one of solvency/integrity broken. This is a design rule, it
   is exhaustively established over all four combinations, and it is not in the cited bug
   reports, which fix one instance.
3. **The authority/computation distinction.** An architecture that computes a *correct*
   server-side recount, records it, and still bills the declared number leaks 58.3% of
   delivered value. "Recount the tokens" is the obvious advice and it is insufficient.

**Remaining weakness.** A reviewer who values primitive novelty above systematization will
still rate this below bar, and no amount of further work changes that. The paper is a
systematization-and-measurement contribution and says so.

**Changed in response.** Nothing further — the framing was already bounded in an earlier
round. Adding the formal section strengthens the *first* item above from an argument to a
machine-checked result.

---

## Reviewer B — systems and scalability

**Strongest objection.** *"A single-host Docker Compose testbed with a mock generator, two
concurrent requests in the formal model, and a 135M-parameter toy model. Production
metering is distributed, asynchronous, and sharded. Nothing here transfers."*

**Valid?** **It was the strongest objection against the previous version.** It is now
substantially answered, and the parts that are not are stated.

**Evidence that answers it.**

* **Topologies.** Three: single worker; nginx over four uvicorn workers; a load balancer
  over two gateway containers. 96 accounting cells, 0 mismatches against the control.
* **Storage.** Two families behind one interface — a mutable balance row and an append-only
  ledger with a derived balance. 8 genuinely backend-exercising cells agreed; the count is
  reported honestly at 8 rather than the 17 cells compared, because 5 agree analytically
  and 4 are B0 cells that never touch the abstraction.
* **Asynchrony.** A third family: an event queue with a continuously running worker and a
  controlled reconciliation delay. This directly answers "production is asynchronous", and
  it produced the sharpest systems result in the paper — see below.
* **A real serving stack.** `llama.cpp`'s `llama-server`, third-party serving code, real
  BPE tokenization, real SSE, real usage records. 60 cells, 0 safety disagreements.

**The finding this objection produced.** Under asynchronous settlement, B0's over-serving
appears with **strictly sequential arrivals 20 ms apart** — no concurrency whatsoever —
once the reconciliation delay reaches 100 ms, reaching 4 requests over a 2-request budget
at 500 ms with a negative balance. **The atomic guarded decrement, which is the entire B0
defense, provides nothing if it lands after the next authorization reads the balance.**
The sufficiency condition had to be restated as requiring atomicity *on the path that
authorizes*. A reviewer objection changed a conclusion, which is the point of running one.

**Remaining weakness.** Still one host; no sharded or partitioned credit state; no
consensus failures; no real production traffic. The reconciliation delays are injected
rather than observed in the wild, so the async result is explicitly conditional: *if*
settlement lags authorization by more than the inter-arrival time, then over-serving
follows.

**Changed in response.** The asynchronous accounting family, the real serving stack, and a
restated B0 sufficiency condition.

---

## Reviewer C — formal methods

**Strongest objection.** *"You wrote a TLA+ file and called the paper formal. There is no
refinement proof, the model has two requests and unit pricing, and you check only safety.
The specification could be an arbitrary state machine that has nothing to do with the code
you measured."*

**Valid?** **Partly, and precisely where the paper says it is.**

**Evidence that answers it.**

* The model is *checked*, not decorative: 10 configurations × 4 invariants = 40 independent
  TLC runs, 27,526 distinct states, deterministic under `-workers 1`.
* Every expected outcome is declared **before** the run in `formal/check.py`, which exits
  non-zero on disagreement. All 40 matched.
* The discipline demonstrably works: the *first* specification was wrong — it treated a
  reservation as a hold rather than a committed debit — and TLC rejected the **safe**
  configurations until the settlement semantics were fixed. That failure is recorded in the
  paper, not erased.
* The tie to the implementation is not left as an assertion: every counterexample is paired
  with the measured behaviour it predicts (`paper/formal_empirical_mapping.md`), and the
  B0 trace is the read/read/write/write lost update step for step.
* Each invariant is checked in a *separate* run, which is why it surfaced that M2's defect
  breaks both accounting integrity and the refund bound — a fact a joint check would have
  hidden.

**Remaining weakness — conceded in full.** There is **no refinement proof** from the
specification to `app/`. The correspondence is an argument supported by case-by-case
agreement. The model is finite (2–3 requests, 2 chunks, unit pricing), only safety is
checked (no liveness), no parameterized or inductive result is attempted, and the
asynchronous family is outside the model entirely. A formal-methods venue would want a
refinement mapping or a parameterized proof, and neither exists here.

**Changed in response.** The whole formal section; a three-label evidence discipline
(MODEL-CHECKED / FORMALLY ARGUED / EMPIRICALLY VERIFIED) applied across the paper and the
claim matrix; an explicit exclusion list in `paper/scope_of_formal_claims.md`; and a
standing rule that nothing weaker than a TLC result is ever called "proved".

---

## Reviewer D — economics and measurement

**Strongest objection.** *"Leakage efficiency of 58.3% is an artifact of your pricing
constants and your generator. Change the token mix and the number changes; change the
pricing basis and the ranking of attacks changes. There is no economic model here, just
percentages from a testbed."*

**Valid?** **Yes on the magnitudes — and we now demonstrate it ourselves rather than wait
for the reviewer to.**

**Evidence.**

* Leakage efficiency is deliberately **price-invariant under uniform scaling**; absolute
  dollars are labelled scenario values throughout. Structural repricing *does* change it,
  and that is reported as a finding rather than a nuisance.
* The real-stack experiment quantifies exactly the objection: output under-reporting at 90%
  yields 0.690 there against 0.583 on the mock, because SmolLM2 emits no reasoning tokens.
  **5 of 48 cells flipped effectiveness**, including one manipulation (`drop_reasoning`)
  that becomes completely inert against a model with no reasoning tokens. The paper states
  that the architectural conclusion is generator-independent while the per-manipulation
  magnitudes are not.
* Which manipulation pays off is a property of the *billing function*, not of attacker
  ingenuity: a total/subtotal mismatch is inert under category pricing (0.000) and the
  strongest attack under flat-total pricing (0.741). That is a structural claim, and it
  reproduced on the real stack.
* Attacker knowledge is graded K0/K1/K2 and disclosed. The headline attack is K0 —
  constructible from what the client itself can observe. The two manipulations needing
  privileged knowledge are labelled and excluded from the main claim.

**The finding this objection produced.** On a real serving stack the *honest* cost of a
byte-identical request is not reproducible: the reported prefix-cache split moves with
server cache state, shifting the authoritative charge by 22–32% on 3/3 prompts. Three
consequences follow — the provider's own number is not reproducible; a client cannot verify
its own bill even in principle; and an over-declared cached count carries genuine plausible
deniability, because the true value legitimately varies. That is an economic property of LLM
metering that a fixed-price API does not have.

**Remaining weakness.** There is still no revenue-impact model, and deliberately so: any
such figure would require an assumed attacker population and request volume, and would be
fiction dressed as a number. Pricing tiers are synthetic. The cache-split result is one
stack, one prefix cache.

**Changed in response.** The real-stack economic comparison, the cached-split probe, and
explicit separation of "this manipulation can leak X%" from "a remote client can execute
this manipulation".

---

## Summary

| reviewer | strongest objection | status |
|---|---|---|
| A — novelty | no new primitive | **conceded and framed**; unchanged by this round |
| B — systems | single-host, synchronous, mock | **substantially answered**; produced a new B0 result and a restated sufficiency condition |
| C — formal | no refinement proof, small model | **partly answered, partly conceded in full** |
| D — economics | magnitudes are artifacts | **answered by demonstrating it ourselves**; produced the cache-split finding |

Two of the four objections changed a conclusion in the paper. That is the outcome a
reviewer simulation should aim for; a round in which every objection bounced off would have
meant the questions were too easy.
