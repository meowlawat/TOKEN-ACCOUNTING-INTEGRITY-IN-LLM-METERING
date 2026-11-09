# Manuscript Integration Plan

Produced per the integration-authorization instruction, before any edit to
`paper/main_fgcs.tex`. Read directly for this plan: `paper/main_fgcs.tex` (full structural
map below), `FINAL_HARDENING_BASELINE.md`, `FINAL_HARDENING_AUDIT.md`,
`DURABILITY_HARDENING_AUDIT.md`, `FORMALIZATION_AUDIT.md`, `FINAL_EXPERIMENT_AUDIT.md`
(the retracted/corrected one), and the raw result artifacts cited inline below (not just
the audits' prose summaries — the actual `results/two_machine/*.summary.json` cells).

Current `main_fgcs.tex` section map (line numbers as of HEAD `15def0a`):

```
71   Introduction (Contributions list: 141-171)
191  Threat Model and Security Property
255  Background and Related Work
427  Accounting State Model (Mechanism localization: 495-558)
559  Architectural Taxonomy
603  System and Experimental Methodology
666  Formal Verification (sec:formal)                — TokenAccounting.tla only
779  Empirical Results
955  Defenses and Sufficiency Conditions (sec:sufficiency; tab:practical: 1006-1043)
1088 Cross-Architecture and Asynchronous Validation (sec:generality)
       1098 Execution topologies
       1107 Accounting backends
       1122 A real serving stack
       1149 The provider's own number is not reproducible
       1165 Asynchronous accounting (sec:async)
       1184 B0 revisited (sec:b0revised) — tab:asyncb0, single-host, UNCHANGED
1229 Economic and Pricing Analysis
1293 Discussion
1344 Threats to Validity (sec:limits)
1412 Responsible Disclosure and Ethics
1423 Conclusion
```

No manuscript text currently overclaims Redis/queue durability, "exactly once," physical
hardware separation, or production prevalence — confirmed by the grep audit below. The
gap is integration, not retraction. One paragraph (`sec:limits`, Formal) will become
**stale**, not wrong, once the new formal model is added (§F below) — it currently says
the async family "lies outside" the formal model entirely, which stops being true the
moment `AsyncSettlementTOCTOU.tla` exists.

---

## A — Where the real two-machine experiment goes

**Location:** new subsection immediately after `sec:b0revised` (after line 1227, before
`\section{Economic and Pricing Analysis}` at 1229), inside
`\section{Cross-Architecture and Asynchronous Validation}`. Not a new top-level section —
it is the direct escalation of the question `sec:b0revised` already asks ("is this
fundamentally about concurrency?") to "does it survive physical network separation?",
and `sec:generality`'s own framing paragraph (1090-1096) already lists "execution
topology" as one of the varied dimensions this section tests, but §1098 Execution
topologies currently states all three tested topologies "ran on a single host" — this is
exactly the sentence the new subsection extends.

**New subsection: "Network-separated validation."**

Content, from verified raw data (not the audit prose, the actual summary JSONs):

- Topology: Machine A (gateway only) and Machine B (Postgres + Redis + worker) on two
  separate hosts connected over the real internet (Azure VM, Central India region, public
  IP), not loopback. This is `experiments/two_machine/docker-compose.machineA.yml` /
  `.machineB.yml`.
- Corrected sequential-arrivals-with-deferred-settlement sweep, `results/two_machine/
  C2_sequential_20261007T123546Z.summary.json`, commit `f0a41ba`, $N=6$, $k=2$ (budget
  units), 5 reps per delay, delays $D \in \{0, 200, 500, 1000, 2000, 5000, 10000\}$ ms:

  | $D$ (ms) | over-served (5 reps) |
  |---|---|
  | 0, 200, 500, 1000, 2000 | 0, 0, 0, 0, 0 |
  | 5000 | 3, 2, 2, 2, 2 |
  | 10000 | 4, 4, 4, 4, 4 |

  A clean transition from zero over-serving to over-serving that saturates at $N-k=4$,
  consistent with the scaling bound (§F below). Note for the prose: this sweep's $D$ is
  the worker-side settlement delay, independent of (and larger than) the achieved
  client-side inter-arrival gap (513-857 ms, measured directly from `sent_at_utc`
  timestamps, real-network RTT-dominated) — the manuscript must say so explicitly so a
  reviewer does not read $D=2000$ "no effect" as contradicting the achieved-gap number.
- Strict-serial negative control over the same topology, `results/two_machine/
  C2_strict-serial_20261007T125009Z.summary.json`, $D \in \{0, 500, 2000, 10000\}$ ms, 3
  reps each: over-served $=0$ in **every one of the 12 cells**, served $=2=k$ exactly.
  (A 1-rep pilot, `C1_strict-serial_20261007T123415Z.summary.json`, agrees at $D\in\{0,
  500, 2000\}$.)
- Preferred sentence (verbatim, per the task's own wording, to appear in this subsection
  and be echoed, compressed, in the abstract and the contributions list):

  > "The B0 mechanism persisted under a network-separated two-machine deployment, while
  > strict serialization of authorization and settlement produced no observed
  > over-serving across the tested settlement delays."

- Explicit non-claims in the same paragraph: this is one topology (two hosts, one cloud
  region, one provider), not a claim about production deployments, physical hardware
  separation beyond the tested VM/host pair, or distributed systems generally; "achieved"
  vs. "configured" delay are different quantities and both are reported where relevant.

**Table.** One small table in this new subsection presenting the corrected sequential
sweep (the table above) is justified — it is the one number that answers "is the
single-host result a loopback artifact?" and the paper does not yet have it anywhere.
The strict-serial result is three sentences, not a table (12 cells, all zero, no
interesting internal structure to tabulate).

## B — Where the strict-serial negative control is described (mechanism, not just result)

**Location:** same new subsection as A (not split out), immediately after the sequential
sweep table, as the "and here is a control that cannot race by construction" counterpart.

**Required explanation (mechanism, exact wording constraint):** the harness dispatches
request $i+1$ only after polling the account's authoritative balance
(`experiments/two_machine/run_distributed_experiment.py`, `strict-serial` arrival mode)
until it equals the expected post-settlement value for request $i$ — i.e., it waits for
confirmed settlement, not for the Redis queue to report empty.

**Do NOT present queue-depth polling as the mechanism.** It was the first implementation,
tried and rejected: polling `queue_depth == 0` produced false positives because
`async_worker.py::drain()` pops a not-yet-due event into a local list and only re-pushes
it after the full scan completes, so `queue_depth` can read 0 while an event is still "in
transit." This version measured over-serving at $D=500,2000$ ms with achieved gaps far
below the configured delay (raw data preserved, tagged
`C1_strict-serial_20261007T123240Z.SUPERSEDED_QUEUEDEPTH_BUG`). The plan is to mention
this **only as one sentence of methodology/audit context** — "an earlier queue-depth-based
implementation was found to have a transient false-empty window and was replaced with
balance-based confirmation" — not to give it a table or a figure. This satisfies the
"only if useful for methodology discussion, and if included must say queue-depth polling
had a transient pop/requeue race" instruction without devoting real estate to a
superseded, buggy measurement.

## C — Where the sequential-arrival-pacing-confound discovery belongs

**Location:** split in two places, by audience:

1. A short methodological note inside the new subsection from A/B (one or two sentences):
   the original sequential-arrival harness paced requests by sleeping a nominal interval
   after each full round trip; over the real two-machine network the round trip itself
   inflated the *achieved* inter-arrival gap to 513-857 ms, which is why the corrected
   sweep in A reports $D$ starting at 0 and specifically brackets that achieved-gap range.
   This is reporting a methodology correction, not a new result — it explains why the
   table in A uses the delay values it uses.
2. **Do not touch the single-host Table~\ref{tab:asyncb0}/sec:b0revised result.** That
   result used a 20 ms nominal pacing on loopback, where round-trip inflation is
   negligible (the paper's own stated ~45 ms loopback floor, `sec:limits` Internal
   paragraph, is for the gateway path, not this harness, but the order of magnitude is
   consistent and the result was re-verified this session, exact match: 0,0,0,1,4). The
   confound is specific to the two-machine, real-network measurement; it is not evidence
   against the existing single-host table, and the plan is explicit that the existing
   table is not retracted, only extended by a network-separated counterpart.

No manuscript text currently claims the single-host sequential result generalizes to a
distributed deployment — it is their own open limitation (`sec:limits`, "Distribution"
paragraph, item I below) — so there is nothing to retract in `main_fgcs.tex` itself; the
retraction already happened in `FINAL_EXPERIMENT_AUDIT.md` (an internal audit document,
not the manuscript) and stays there.

## D — Where the Redis durability discovery and the transactional-outbox defense belong

**Two separate insertion points, deliberately:**

1. **Discovery, as a validation finding:** new subsection, same location as A/B (end of
   `sec:generality`), titled "Durability of the queued settlement event." Content:
   - OLD: the pre-fix architecture held the only record of a pending settlement event in
     the Redis queue; nothing durable existed until the worker actually applied the
     debit.
   - FAILURE (directly tested, not simulated): a queued, not-yet-due event was confirmed
     in the queue, the Redis container was hard-killed (`SIGKILL`), restarted, and the
     event was **permanently lost** — queue empty, balance never debited. Evidence:
     `DURABILITY_HARDENING_AUDIT.md` §"failure matrix" row "Redis hard crash (SIGKILL)."
   - ROOT CAUSE: no durable (PostgreSQL) record of the pending settlement existed
     independent of Redis.
   - Explicit wording constraint satisfied: this is described as a property of *this
     implementation's queue*, discovered by direct fault injection, not as a claim about
     message queues, Redis, or production messaging systems in general.
2. **Fix, as a sufficiency-condition / defense update:** `\section{Defenses and
   Sufficiency Conditions}` (955), specifically the existing **"Async" row of
   `tab:practical`** (lines 1036-1040). This is the single most important and easiest
   update in the whole integration: that row's "Model-level condition" column *already
   says* "Durable, idempotent accounting events with bounded reconciliation lag" — the
   condition was stated correctly before the fix existed. Its "Implementation pattern"
   column currently says only "Idempotency key per event, at-least-once delivery with
   duplicate suppression, and authorization that accounts for in-flight events" — true
   but, pre-fix, incomplete: it describes idempotency, not durability, and the
   architecture that satisfied it was not actually durable against a Redis crash. The fix
   is to update only the **Implementation pattern** cell to add the outbox:

   > "PostgreSQL transactional outbox (settlement event committed durably, in the same
   > transaction as the accounting record, before being handed to Redis); idempotency key
   > per event; at-least-once delivery with duplicate suppression; Redis-independent
   > reconciliation scan recovers any event Redis does not deliver."

   The "Failure mode" and "Property at risk" cells of that row are unchanged — they
   already correctly name "Usage event lost, duplicated, or applied after the next
   authorization" and "Accounting integrity; conservation," which the outbox addresses
   without changing the stated failure mode or property.

   Also add one sentence to the `\paragraph{Implementation-specific caveats}` (992-998),
   parallel to the existing M1/M2/B0 caveats, stating that the async family's durability
   claim is scoped to the specific failure points tested (process kill before/during/after
   consumption, Redis SIGKILL, duplicate delivery) and not to arbitrary-scale distributed
   failure or a VM/host restart.

**Exact delivery/application wording (binding constraint):** "at-least-once delivery"
describes what Redis plus the reconciliation fallback guarantee; "idempotent application"
or "duplicate delivery does not result in duplicate debit" describes what the atomic
claim-and-debit (`ledger.claim_and_debit_outbox`) guarantees. Never write "exactly-once
delivery." Grep of the current draft for "exactly" and "exactly once" returns nothing, so
this is a constraint on new text only, not an existing error to fix.

## E — Which existing figures/tables should be extended vs. left alone

- **`tab:asyncb0`** (single-host sequential, 1195-1212): left alone, byte-for-byte.
- **`tab:practical`** (955 section, 1006-1043): one cell edited (Async row,
  Implementation pattern column), per D above. Caption needs no change.
- **`tab:formalmatrix`** (704-726): left alone — it is `TokenAccounting.tla` only, and
  the new model is a separate specification, not an extension of this one (see F).
- **New table:** one small table in the new A/B subsection (corrected two-machine
  sequential sweep). No new figure is justified — the data is seven delay values times a
  single over-served count per rep-set; a table is more honest than a plot here given
  only two non-trivial delay points (5000, 10000 ms) show variation.
- No existing figure (`fig:statemachine`, `fig:b0`, `fig:m1`, `fig:m1conc`, `fig:m2`,
  `fig:toklat`) needs modification; none of them encode anything the hardening work
  touched.

## F — Formal model: include or omit, and how

**Decision: include, as a short new subsection, not a parallel full section.** The new
`AsyncSettlementTOCTOU.tla` model is a genuine, materially-strengthening result — it is
the formal counterpart of exactly the empirical finding in `sec:b0revised`/the new
network-separated subsection, and without it the paper's formal-verification story is
silent on the mechanism the empirical sections now spend the most new space on. Omitting
it would leave `sec:limits`'s Formal paragraph's claim that the async family "lies
entirely outside" the formal model accurate but the paper weaker than its own evidence
supports.

**Location:** new subsection at the end of `\section{Formal Verification}` (after
"Validating the specification," before `\section{Empirical Results}` at 779), titled
e.g. "A second model: the asynchronous-settlement race." Kept deliberately short (roughly
the length of "Validating the specification," not the length of "Counterexamples").

**Content, precise and bounded:**
- A second, separate TLA+ specification (`formal/AsyncSettlementTOCTOU.tla`), because the
  mechanism it models is different in kind from `TokenAccounting.tla`'s: a
  **causal-ordering-based**, untimed interleaving of CREATED → ADMITTED/REJECTED →
  SETTLEMENT\_PENDING → SETTLED (and RELEASED), not a millisecond-timed model and not an
  extension of the first specification's state machine.
- Checked with TLC at two $(N,k)$ points: $(6,2)$ (matching the primary empirical
  workload exactly) and $(4,2)$. Results, stated as a model-checking fact, not prose
  praise:
  - Vulnerable configuration: `Solvency` **violated** at both points (shortest
    counterexample at $(6,2)$: 3 non-simultaneous, staggered admissions against a 2-unit
    budget, reproduced exhaustively over 91,921/22,521 generated/distinct states for
    `AccountingIntegrity` alone, with no violation found there); `AccountingIntegrity` and
    `LedgerConservation` **hold** exhaustively at both points.
  - Atomic configuration: all three invariants hold at both points.
- This complements, and does not duplicate, `tab:formalmatrix`: the first model's
  vulnerable B0 configuration violates `LedgerConservation` and holds `Solvency` (the
  synchronous lost-update signature); the second model's vulnerable configuration violates
  `Solvency` and holds `LedgerConservation` (the TOCTOU-admission signature). State this
  contrast explicitly — it is a genuinely interesting, non-obvious consistency check (two
  mechanistically distinct races leave different invariant-violation fingerprints), not
  noise to smooth over.
- Explicit limitation sentence, required: this specification is an abstract,
  causal-ordering model of the mechanism studied empirically in the new network-separated
  subsection; it is checked exhaustively as a model, and we do not claim it verifies the
  implementation, a timed/network behavior, or anything beyond the two finite $(N,k)$
  points checked. Same three evidence labels as the existing Formal Verification section
  (model-checked / formally argued / empirically verified) apply unchanged.

**Consequence for `sec:limits` (Formal paragraph, 1365-1372):** the sentence "The model
assumes strongly consistent accounting state, so the asynchronous family of
Section~\ref{sec:async} lies outside it and its results are labeled empirical only" is
now **stale**, not wrong — it was true of `TokenAccounting.tla` alone and stops being
true once a second, purpose-built model exists for exactly that family. Rewrite to say
the *first* model assumes strong consistency and does not cover the asynchronous family,
while a second, separate, untimed abstraction now covers the asynchronous-settlement
mechanism specifically, with its own, narrower limitations (no timing, no network, no DB,
finite $(N,k)$) restated rather than silently dropped. This is a required correction, not
optional polish — leaving it as-is after adding the new model would make the manuscript
internally inconsistent with itself.

## G — Which claims need wording changes (beyond D/F already covered)

- Abstract (39-61): the existing sentence "Asynchronous settlement reproduces
  over-serving under strictly sequential arrivals, so the synchronization condition
  concerns not concurrency but whether authorization is atomically coupled to economic
  commitment on the authorizing path" stays, but gets one short appended clause carrying
  the network-separation result, since this is the paper's headline systems claim and the
  abstract currently has no hint that it was tested beyond one host. Proposed minimal
  addition (not a rewrite): "...authorizing path; this persists under a network-separated
  two-machine deployment, while a settlement-confirmed serialization control shows none."
  The durability/outbox fix is **not** added to the abstract — it is a robustness finding
  about the testbed's own queue, not one of the paper's three headline results, and
  adding a fourth storyline to an already-dense abstract risks exactly the "generic
  distributed-systems paper" drift the task warns against. It is fully described in the
  body (D, F) and limitations (I).
- Contributions list, item 4 (157-161, the "distributed-settlement result" bullet): add
  one clause noting the network-separated replication and the strict-serial control,
  mirroring the abstract change, so the contributions list and abstract stay consistent
  with each other. Do not add a sixth bullet for durability — fold one clause into the
  existing item 5 (empirical validation, 162-165) instead ("...two independent inference
  data planes, and a network-separated deployment, with fail-closed integrity gates..."),
  since durability-of-the-queue is validation infrastructure hardening, not a new
  empirical axis the way B0/M1/M2 are.
- `sec:async` (1165-1182): no change to the injected lost-event-fault result (1176-1177,
  "A lost event, by contrast, leaks permanently at every delay") — this is a *different*,
  pre-existing, deliberately-injected synthetic fault (`--fault lost_event`), not the
  Redis-crash finding. Add one clarifying clause so a reader does not conflate the two:
  "(this is an injected application-level fault, distinct from the infrastructure-level
  Redis failure discussed in Section~\ref{sec:generality})" or similar, with a forward
  pointer once the new subsection exists.
- `sec:sufficiency` B0 paragraph (982-990) and `sec:b0revised` (1214-1227): both already
  state the corrected, general B0-a condition correctly ("authorization atomically
  coupled to economic commitment on the authorizing path... concurrency is one way to
  break that coupling; delayed settlement is another"). No change needed; the
  network-separated result is additional evidence for a claim already stated this way,
  not a reason to restate it.

## H — "Sequential" occurrences: ambiguity audit

Full grep (7 hits, `paper/main_fgcs.tex`):

| Line | Text | Disposition |
|---|---|---|
| 55 | Abstract: "strictly sequential arrivals" | Unambiguous: paired with "so the synchronization condition concerns not concurrency," i.e. the no-overlap, deferred-settlement sense. No change. |
| 158 | Contributions item 4: "strictly sequential arrivals and no concurrency at all" | Same sense, same pairing. No change. |
| 505 | Mechanism localization: "strictly sequential arrivals, with no overlap at all" | Same sense, explicit "no overlap." No change. |
| 801 | Figure caption (`fig:b0`'s surrounding text, "...with strictly sequential arrivals.") | Need to re-check in context during editing (see note below) — same section as 782-791 (B0: synchronization), likely referring to the same deferred-settlement sense; confirm it is not accidentally describing the *concurrent* B0 baseline sweep before finalizing. |
| 1189 | `sec:b0revised`: "We issued requests strictly sequentially, 20 ms apart" | The single-host result. Describes the harness's intended pacing; this is the sentence that should get a short cross-reference once the two-machine subsection exists, noting that the two-machine replication additionally distinguishes this deferred-settlement sense from genuine settlement-confirmed serialization (the strict-serial control) — because after this integration, "sequential" and "strict serialization" are two named, distinct things in the same paper and a reader needs the distinction stated once, here, where both first matter together. |
| 1197 | `tab:asyncb0` caption: "strictly sequential arrivals 20 ms apart" | Same as 1189, no change needed beyond the cross-reference added at 1189. |
| 1303 | Discussion: "the third fails under sequential arrivals if settlement lags" | Same deferred-settlement sense, consistent. No change. |

**Conclusion: no existing occurrence is actually ambiguous on inspection** — all seven
already use "sequential" in the single, consistent "arrivals do not overlap in time"
sense, never in the new "strict serialization of authorization and settlement" sense,
because that second concept does not exist in the manuscript yet. The task's required
terminology distinction is therefore satisfied by **introducing "strict serialization"
as a new, separate term in the new subsection** (A/B) and adding one short cross-reference
at line 1189 — not by rewriting any of the seven existing occurrences, none of which are
wrong. New text written for A/B/C must consistently say "sequential arrivals with
deferred settlement" when referring to the existing mechanism and "strict serialization
of authorization and settlement" (or "strict-serial," matching the harness's own flag
name, once introduced) for the new control, and never use "sequential" alone to mean the
new control.

## I — Statements that could imply Redis/event durability, now inaccurate

Full grep for "durable"/"durability" (6 hits) plus manual check of the async section:

| Line | Text | Accurate after the fix? |
|---|---|---|
| 75 | Intro: "holds economic state that is authoritative for billing but not yet durable" | Yes — describes the general problem statement (the gap between authorization and durable commitment), not any specific implementation. No change. |
| 328 | Related work: "between value delivery and durable debit in the asynchronous family is an instance of the..." | Generic, no change. |
| 966 | M1 sufficiency condition: "committed and durable" | Scoped to M1's terminal-path totality condition, unrelated to the B0-async queue. No change. |
| 993 | Implementation-specific caveats: "The model says 'committed and durable'... our implementation achieves it with a cancellation-shielded settlement task" | Scoped to M1's `asyncio.shield` mechanism specifically (confirmed in the prior audit pass). Does not describe the B0-async Redis queue. No change — this caveat was never about the component that had the durability gap. |
| 1174 | `sec:async`: "exposure window between value delivery and durable debit" | Accurate: refers to the moment the debit is actually applied to PostgreSQL, which has always been durable once applied. The gap that was *not* durable was the pending-event record *before* application, which this sentence does not claim anything about. No change needed, but see D/G above for the new subsection that states the actual pre-fix gap explicitly. |
| 1317 | Discussion, Engineering implications: "Every terminal path of the request lifecycle must reach a durable accounting event, which in our implementation required a cancellation-shielded settlement task" | Same scope as 966/993 — M1's terminal-path property, phrased as a general engineering implication but immediately tied to "a cancellation-shielded settlement task," which is the M1 mechanism, not the B0-async queue. Arguably this sentence's generality invites a reader to wonder whether B0-async's queue satisfies it; given the fix now exists, it is worth adding one clause here pointing at the new outbox durability subsection so the engineering-implications paragraph does not read as if it forgot the queue existed. |

**Conclusion:** no existing sentence makes a false durability claim — confirmed by
checking each hit's actual scope, not just the keyword. The one actionable change is
adding a forward pointer at line 1317 to the new outbox subsection, so the Discussion's
general durability claim and the async-specific fix are visibly connected rather than
sitting in two unconnected parts of the paper.

## J — Claims that should remain unchanged

- `tab:asyncb0` and all of `sec:b0revised`'s prose (single-host result, mechanism
  explanation, restated B0-a condition): unchanged, re-verified this session.
- `sec:sufficiency`'s M1 and M2 paragraphs, and the Implementation-specific caveats'
  M1/M2/B0 sentences (963-991, 993-998 except the one addition in D): unchanged — none
  touch the async queue.
- `tab:formalmatrix` and the entire existing Formal Verification narrative for
  `TokenAccounting.tla` (666-777): unchanged.
- The "Scope of empirical claims" paragraph (1385-1392) and the M2 pricing-monotonicity
  framing (977) and the "Limits of detectability measurement" paragraphs (932-951,
  1361-1362): already correctly scoped; nothing to do.
- Every number in `sec:results` (B0/M1/M2 empirical sections, 779-954): unchanged, not
  touched by any of the hardening or durability work.
- The "Distribution" paragraph in `sec:limits` (1394-1410): **not deleted**, but needs one
  surgical edit (see below) — it currently states flatly that no second machine was used
  and a two-machine replication "was not performed here." That sentence becomes false the
  moment the new subsection is added, so this is a required correction, tracked here
  rather than left implicit: reword to state that a two-machine replication of the
  deferred-settlement mechanism *was* performed (pointing at the new subsection) and
  survived, while the specific things still not established — $D$'s relationship to a
  production network path, clock skew, cross-machine queueing behavior beyond the one
  tested cloud-region pair, VM-restart durability, and any production deployment — remain
  exactly as stated. This paragraph is the second most important edit in the whole
  integration (after the `tab:practical` Async row), because it is the only paragraph in
  the current manuscript that is flatly contradicted by evidence already in hand.

---

## Summary of concrete edits to make, in order

1. `sec:limits` → "Distribution" paragraph (1394-1410): reword to report the
   network-separated replication and narrow the remaining limitation claims accordingly.
2. `sec:limits` → "Formal" paragraph (1365-1372): reword to account for the second model.
3. New subsection(s) at the end of `sec:generality` (after 1227): "Network-separated
   validation" (A, B, C) and "Durability of the queued settlement event" (D-discovery).
4. `tab:practical` Async row, Implementation pattern cell (1036-1040): add the outbox (D-fix).
5. `\paragraph{Implementation-specific caveats}` (992-998): one added sentence scoping the
   outbox's tested failure points.
6. New subsection at the end of `\section{Formal Verification}` (after 777): the second
   TLA+ model (F).
7. Abstract (39-61) and Contributions item 4/5 (157-165): minimal wording additions (G).
8. `sec:async` (1176-1177): one clarifying clause distinguishing the injected
   lost-event fault from the Redis-crash finding (G).
9. `sec:b0revised` (1189) and Discussion (1317): two short cross-reference clauses (H, I).

No other file changes. No new experiments. No change to any number in `sec:results`,
`sec:economics`, or any existing table/figure other than the single `tab:practical` cell
in item 4 above.

After these edits: run the full compilation/reference/grep check list and produce
`POST_INTEGRATION_AUDIT.md`, then the final seven-question hostile-reviewer self-check,
per the task's own closing instructions.
