# Cover letter — Computers & Security

Dear Editors,

Please consider the enclosed manuscript, *Token-Accounting Integrity in LLM Metering: A
Systematic Study of Client-Side Under-Payment*, for publication in *Computers &
Security*.

**What the paper is about, and what it is not.** The security object of this work is
metering and accounting infrastructure: authorization, reservation, debit,
reconciliation, and billing authority in a usage-metered API. It is a study of billing
integrity, quota enforcement, and economic security at an API boundary. Large language
models appear only as the workload that makes that boundary interesting, because a single
LLM request combines progressive value delivery, usage that is unknown at authorization
time, multi-category token vectors, and asynchronous settlement. **The paper is not about
the security of the model itself** — it contains no adversarial-ML, prompt-injection,
model-robustness, or model-privacy content. We mention this explicitly because that
distinction determines whether the work falls inside the journal's scope, and we believe
it clearly does.

**Threat model.** We study an under-examined direction: an honest provider facing a
legitimate, authenticated client that wants inference without paying for it. Existing
work on this surface addresses dishonest providers inflating hidden token counts, third
parties draining a victim's budget, and dishonest intermediaries forging provenance — all
of which assume the client is honest, impersonated, or irrelevant. We complete that
quadrant.

**Contribution, stated conservatively.** We claim no novelty at the primitive level, and
we say so in the abstract, the introduction, and the discussion. Every enabling mechanism
is individually known: trusting a client-supplied value in a security decision is
CWE-807; disconnect-related accounting gaps appear in a deployed gateway issue and in a
shipped mitigation; racing a shared counter is a classical web race. What is missing in
the literature is not a primitive but a frame. Placed on a single request lifecycle,
these failures are the same integrity property, $V(r) \le N(r)$, violated at three
different points — state synchronization, commitment timing, and usage authority — and
that framing yields results the individual bug reports do not.

**Principal results.**

- *Reservation and abort-safe finalization are orthogonal.* Each alone secures exactly one
  of solvency and accounting integrity; only both secure both. Established exhaustively by
  model checking over all four combinations, not by the two architectures we happened to
  implement.
- *Computing usage correctly is not the same as billing from it.* An architecture that
  performs an accurate server-side recount, stores the result, and still charges the
  client-declared number leaks 58.3% of delivered value in our controlled setting and
  69.0% against a real serving stack. Server-authoritative billing removes the observed
  leakage. This contradicts the obvious advice that "the server should recount."
- *The synchronization condition is not fundamentally about concurrency.* Deferring
  settlement produces over-serving under strictly sequential arrivals, with no two requests
  ever in flight together. The correct condition is that authorization be atomically
  coupled to economic commitment on the path that authorizes service.

**Methods.** The lifecycle is specified in TLA+ and checked exhaustively with TLC across
ten architecture configurations and four invariants, with every expected outcome declared
before the runs. Empirically, the study spans three execution topologies, three accounting
families (mutable balance row, append-only ledger, and an asynchronous event pipeline),
and two independent inference data planes — our own deterministic generator and
third-party serving code substituted for it. Integrity gates fail closed and are validated
by fault injection; a separate audit re-derives every reported quantity from raw data
using code that imports nothing from the project.

**On limitations.** We have tried to be explicit rather than flattering about what this
work does not establish. There is no mechanized refinement proof from the specification to
the implementation; the formal model is finite and checks safety only; the asynchronous
family is measured but not formally modelled; reconciliation delays are injected rather
than observed in production; and no commercial provider was tested, by deliberate ethical
constraint. We also withdraw a detectability claim made in an earlier version of this
work, after our own audit showed the instrumentation restated experimenter-assigned labels
rather than measuring evidence. That withdrawal is documented in the paper.

**Artifact.** The testbed, attack harness, defense implementations, TLA+ specification,
and complete raw data are publicly released. Every table and figure in the manuscript
regenerates from raw data; none is hand-edited. Every attack in the artifact is paired
with a defense.

**Ethics.** All experiments ran against a local testbed whose harness defaults to
`localhost` and contains no third-party endpoints. No credentials, real user data, or
production billing APIs were used, and this work produced no vulnerability findings
against any third-party or production system.

The manuscript is original, is not under consideration elsewhere, and has not been
published previously. The author declares no competing interests.

Thank you for your consideration.

Sincerely,
Hardik
Department of Computer Science and Data Analytics
Indian Institute of Technology Patna, India
