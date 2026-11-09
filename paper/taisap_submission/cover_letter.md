Dear Professors Kantarcioglu, McDaniel, and Samtani,

We are pleased to submit our manuscript, "Accounting Integrity in Metered LLM-Serving
Infrastructure: Verified Conditions Against Client-Side Under-Payment," for consideration
in ACM Transactions on AI Security and Privacy.

This paper studies the security of the usage-metering and billing path inside deployed
LLM-serving infrastructure against an authenticated client that seeks to pay less than it
owes for inference it received -- a technical vulnerability of AI-enabled systems that
sits squarely within TAISAP's stated interest in "the security of AI models, such as
adversarial attacks on AI and technical vulnerabilities of AI," evaluated here through
technical and economic methods and reported at the level of models, systems, and the
AI-serving environment, consistent with TAISAP's stated scope. The paper is not a
model-level attack: it targets the serving-layer accounting boundary (authorization,
execution, and settlement paths), not the weights, outputs, or training data of the
language model, and the contribution is a systematic security analysis of that boundary,
not a dependability or availability study -- we verify its properties with model checking
in TLA+/TLC and validate them empirically across three execution topologies, three
accounting families, and a network-separated two-machine deployment, against a real
LLM-serving stack.

In brief, the paper (1) models a metered inference request as a state machine with a
single integrity property, $V(r) \le N(r)$, localizing failures to three architectural
placements -- state synchronization, commitment timing, and usage authority; (2) verifies
the model exhaustively with TLC across ten configurations and four invariants; (3)
measures each failure mode empirically, finding that an architecture which recounts usage
correctly but bills the client-declared value still leaks 58.3% of delivered value in a
controlled setting and 69.0% against a real serving stack; and (4) evaluates the defenses
that close each failure, finding the strongest costs under 0.1% of end-to-end inference
time. Five independently filed public reports from separately developed LLM-serving
gateways corroborate that the underlying architectural ingredients occur outside our own
testbed.

The manuscript has not been published and is not currently under review at any other
venue. All experiments were run against our own locally deployed testbed; no third-party
or production system was probed or attacked. Source code, the attack harness, defense
implementations, the TLA+ specifications, and all raw experimental data are publicly
archived with a DOI. We have no competing interests to declare.

Thank you for your consideration.

Sincerely,
Hardik (corresponding author)
Natasha Kaila

---
**[DRAFT NOTE, remove before sending -- not part of the letter body]**
The "has not been published and is not currently under review elsewhere" sentence is
written as a statement of fact because you told me directly that all four prior
submissions (Computers & Security, JISA, JSS, and FGCS, the last on 2026-11-01) were
desk rejections, i.e. concluded, not active reviews. I have not independently re-verified
that with FGCS's own editorial system -- please confirm this is still accurate at the
moment you actually submit, since TAISAP's own submission warranty rests on it being true
on the submission date, not the date this letter was drafted.
