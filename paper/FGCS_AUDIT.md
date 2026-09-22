# FGCS Submission Audit

Written before any FGCS-specific edit to the manuscript. Source examined:
`paper/main_jss.tex` (the most recent prepared version, 1,676 lines, 2 authors, 82
references, not yet submitted anywhere), cross-checked against `paper/main_cn.tex`,
`paper/claim_evidence_matrix.{md,csv}`, `paper/novelty_matrix.md`,
`paper/phase1_sources.json`, and the repository history (`git log`).

## 1. Current manuscript state

- Title: "Token-Accounting Integrity in LLM Metering: A Systematic Study of
  Client-Side Under-Payment". Authors: Hardik (IIT Patna; VSET, VIPS-TC), Natasha
  Kaila (VIPS-TC). elsarticle class, 32 compiled pages.
- Submission history: desk-rejected by Computers & Security (COSE-D-26-05174,
  scope/AI-ML moratorium, no review); submitted to JISA, no longer under
  consideration there; a Computer Networks package was prepared but never
  submitted; a JSS package was prepared and submitted (Editorial Manager,
  manuscript JSSOFTWARE-S-26-03217). No FGCS submission exists yet.
- Content is unchanged in substance since the CN version: an accounting model
  ($V(r) \le N(r)$), a three-mechanism taxonomy (B0 synchronization, M1
  commitment timing, M2 usage authority), TLA+/TLC verification (10
  configurations, 4 invariants, 27,526 states, 40/40 matched), empirical
  measurement (B0/M1/M2 sweeps, real-stack validation with llama.cpp +
  SmolLM2-135M-Instruct, 3 execution topologies, 2 accounting backends, an
  asynchronous settlement family), defense sufficiency conditions, and a
  documented withdrawn detectability claim.
- The JSS pass added 56 references (26 -> 82, each verified against
  Crossref/DataCite before insertion) and reframed the introduction/contributions
  around software architecture and verification. That framing is JSS-specific
  and does not fit FGCS's distributed/cloud-systems scope as well as it fit JSS.

## 2. Current contribution statement

No new attack primitive is claimed. B0 is a known baseline (non-atomic
check-then-decrement); M1 and M2 are individually-known mechanisms
(CWE-807, a documented gateway disconnect bug, a documented proxy mitigation)
whose contribution is systematization, formalization, measurement, and defense
analysis, not discovery. This framing is stated in the abstract, introduction,
and discussion, and it is intellectually honest — it should not be strengthened
for FGCS.

## 3. FGCS scope alignment

FGCS's stated scope covers, among other things: distributed and parallel
computing, cloud and edge computing, resource management, and the security and
dependability of large-scale computing systems. This manuscript's actual content
maps onto that scope as follows:

- **Fits directly:** the accounting/settlement model is a distributed-systems
  problem (shared mutable state under concurrency; the B0 mechanism is a lost
  update in the sense of the ANSI isolation-level literature already cited);
  the asynchronous settlement family is a consistency/staleness problem; the
  cross-topology and cross-backend validation is a distributed deployment
  question; TLA+/TLC is a systems-verification method with a long track record
  in this community.
- **Fits by extension:** LLM inference serving is a cloud computing workload;
  metering/billing is a resource-accounting concern of any multi-tenant service.
- **Does not fit, and should not be forced:** the manuscript is not a
  distributed-systems paper about scale, fault tolerance, or performance at
  the cluster level. Its testbed is single-host Docker Compose; the "three
  execution topologies" are processes and containers on one machine, not a
  geographically or administratively distributed deployment. This is already
  stated as a limitation and must stay a limitation, not be reframed as a
  strength.

**Verdict:** legitimate fit exists (accounting integrity as a distributed-systems
resource-management problem, demonstrated on an LLM-serving workload), but the
manuscript must not be rewritten to claim distributed-systems contributions
(consensus, replication, scale) that it does not have. The honest frame is
exactly the one already used for JSS's "software architecture" pitch, translated
into distributed-systems vocabulary: shared state, concurrency, consistency,
and verification, not "we built a distributed system."

## 4. Major strengths

- A single accounting model localizes three previously-unrelated failure
  reports to three distinct state transitions, and this is verified two
  independent ways (TLA+/TLC exhaustive checking and empirical measurement)
  that agree.
- The M1 vs. B0 distinction (per-request lifecycle defect vs. shared-state
  race) is exactly the kind of state-management distinction FGCS reviewers who
  work on distributed systems will recognize from the isolation-level and
  linearizability literature already cited (Berenson et al., Adya et al.,
  Herlihy and Wing).
- The asynchronous-settlement finding (Section 12 of `main_jss.tex`,
  "B0 revisited") is the strongest systems result in the paper: it shows the
  synchronization failure is not fundamentally about concurrency but about
  where in the pipeline the atomic commitment sits, which generalizes beyond
  LLM billing to any deferred-settlement accounting system.
- Independent recomputation, fault-injection-validated integrity gates, and
  full public artifact release are the reproducibility standard this venue's
  reviewers will look for.

## 5. Major risks

- **Prior desk rejection on scope grounds.** C&S rejected it as out of scope
  for an AI/ML moratorium; that is a different journal's policy and not
  informative about FGCS's actual scope, but an FGCS editor doing due diligence
  may notice the manuscript circulating under multiple venue-specific framings
  (CN, JSS) and ask why. This is a legitimate risk that no amount of rewriting
  removes; the honest response is the truth (each version adapts framing, not
  content, and only one is under review at a time).
- **"Is this an LLM security paper wearing a distributed-systems costume?"**
  A skeptical reviewer could read the FGCS framing as opportunistic. The
  manuscript's own content answers this: B0 is generic (any metered service
  with shared credit state), and the asynchronous-settlement result is stated
  in fully general terms already. The fix is to foreground that generality,
  not to invent new distributed-systems content.
- **Single-host testbed.** Already a stated limitation; FGCS reviewers care
  about this more than JSS or CN reviewers would, because "distributed" is
  closer to this venue's core vocabulary. It must stay explicit, not softened.
- **No production/commercial-provider evidence.** By deliberate ethical
  constraint, already stated. Section 5A of the brief asks for public
  deployed-system evidence; see Section 6 below.

## 6. Desk-rejection risks

- Editor reads the abstract and concludes this is a security paper for a
  security venue. Mitigated only by genuine framing, not by removing the
  security content (the brief itself says not to hide it).
- Editor notices the model is finite, single-host, and non-production, and
  judges the empirical scope too narrow for FGCS's usual systems-scale papers.
  This is a real risk that cannot be fully engineered away without new
  experiments FGCS's own space and time here do not support (see Section 8).

## 7. Reviewer risks

Addressed in full in Section 8 (reviewer attack) below.

## 8. Required and optional new work (Section 5 of the brief)

**A. Public deployed-system evidence — completed.** Web search plus direct
fetch-and-verify of the actual issue pages (not the search summaries) turned up
three real, currently-inspectable GitHub issues directly on point for M1
(commitment timing / terminal-path accounting), beyond the two already cited
(`newapi5235`, `aperture247`):

| System | Public evidence | Architectural ingredient | What it establishes | What it does NOT establish |
|---|---|---|---|---|
| LiteLLM | Issue #14457, opened 2025-09-11, open as of 2026-09-23. Client disconnect before the provider's final usage chunk arrives causes total loss of usage tracking for that request. | Terminal path (client disconnect) with no committed accounting event — exactly the M1 mechanism. | That the M1 failure mode is not a testbed artifact: an independently developed, widely used LLM gateway exhibits the same architectural gap. | Nothing about LiteLLM's exploitability, severity, or whether it is fixed by the time of publication; not a claim that LiteLLM is "vulnerable" in a security sense, only that the architectural ingredient is present and documented by its own maintainers. |
| OpenGateLLM | Issue #1148, opened 2026-09-21, fixed in commit `f0022333`. Interrupted streamed completions are neither billed nor released; one reproduced test case measured 254,347 completion tokens delivered and never billed. | Terminal path without a committed debit, with a directly measured leaked-value instance. | An independently measured, non-trivial instance of exactly the $V(r) > N(r)$ condition this paper studies, in a real deployed gateway, already fixed by its maintainers once identified — which also shows the defect is fixable, consistent with this paper's defense-sufficiency claims. | Nothing about the financial scale of the issue in production, and it is already fixed, so it is historical evidence, not a live claim about OpenGateLLM today. |
| CLIProxyAPI | Issue #2179, opened 2026-03-16, closed. Streaming responses occasionally complete with HTTP 200 and delivered content but no usage metadata, causing downstream billing to record zero tokens. | Usage record production failure at the ACCOUNTED transition — an M1-adjacent gap where the value-delivery and usage-accounting paths desynchronize. | That usage-record loss on the happy path (not just on abort) occurs in practice, broadening the empirical relevance of the accounting-event lifecycle this paper models. | Nothing about root cause parity with this paper's B0/M1/M2 taxonomy; CLIProxyAPI's fix is not analyzed here and no claim is made about its current behavior. |

No claim is made that any of these systems is currently vulnerable, and no
attack was attempted against any of them. This is public evidence of the
*architectural ingredient*, gathered and verified by reading the actual issue
pages (not search-engine summaries) on 2026-09-23.

**B. Two-machine asynchronous experiment — not completed; reporting the
limitation rather than fabricating it.** This work has no second host or
network path available in its environment (single laptop, no cloud account
provisioned for this project, per `CLAUDE.md`'s stated hardware constraints).
The existing asynchronous-settlement result already isolates the causal
mechanism (a controlled reconciliation delay $D$, not network topology) on a
single host, and the paper already states this is a modeled delay, not a
measured cross-host effect. Attempting to fake a two-machine result, or to
silently relabel the existing single-host delay injection as a distributed
experiment, would be exactly the kind of fabrication the brief prohibits.
**Decision: do not claim this experiment was run. Strengthen the existing
limitation instead** so a reviewer cannot mistake the injected-delay result for
a physically distributed measurement.

**C. Realistic price-ratio table — completed, narrowly.** I directly fetched
Anthropic's current public pricing page (`https://claude.com/pricing`, accessed
2026-09-23) and verified the cache-read-to-input ratio myself rather than
trusting a search-result summary. I did not get a clean primary-source fetch
for OpenAI (its pricing page returned HTTP 403 to automated fetches) or Google,
so the table below cites only the one provider I could verify directly, rather
than mixing verified and unverified figures in one table. This is used only to
contextualize the economic model (Section 8 of `main_jss.tex`, "flat-total vs.
category-additive pricing"); it makes no claim about any provider's
accounting architecture or exploitability.

| Provider / model | Input | Cached input (read) | Output | Cache-read : input ratio |
|---|---|---|---|---|
| Anthropic Sonnet 5 | $2 / MTok | $0.20 / MTok | $10 / MTok | 0.10 |
| Anthropic Haiku 4.5 | $1 / MTok | $0.10 / MTok | $5 / MTok | 0.10 |
| Anthropic Opus 5.5 | $4 / MTok | $0.20 / MTok | $20 / MTok | 0.05 |

Source: Anthropic, "Pricing," https://claude.com/pricing, accessed 2026-09-23.
This is used only to show that commercial category-differentiated pricing with
a large input/cached-input ratio is a real, current practice (supporting the
paper's existing claim that the cached-token category is economically
significant), not to imply anything about Anthropic's own metering
architecture, which this paper does not study and makes no claim about.

## 9. Unsupported claims found

None. A full grep of `main_jss.tex` for "first," "novel," "new attack,"
"real-world vulnerability," "commercial provider," "production," "guarantee(s/d),"
"prove(s),"" secure," "general(ly)," "all," "always," "no prior work,"
"practical," and "realistic" (82 raw hits) was checked in context. Every hit is
either an ordinal ("First, the standalone tokenizer..."), a correctly-hedged
technical statement ("No new attack primitive is claimed"), a formally scoped
usage ("...conditions sufficient... to guarantee Equation (1)", which is a
precise statement about the accounting model, not the world), or a stated
non-claim ("no commercial provider was tested, by deliberate ethical
constraint"). No claim needs downgrading. This matches the result of the same
sweep already performed for the CN and JSS versions.

## 10. Reproducibility issues

None found. `paper/claim_evidence_matrix.csv` already maps every major
manuscript claim to its generating script and result file, with a
VERIFIED/UNSUPPORTED/WITHDRAWN classification per row; this is reused rather
than rebuilt for FGCS (Section 9 of the brief asks for exactly this artifact,
and duplicating it would only create a second document to keep in sync).
`scripts/check_cn_submission.py`-style headline-number verification will be
re-run against the compiled FGCS PDF before submission (see Section 12,
Final Output, of this process).

## 11. Proposed edits (FGCS-specific only)

1. Journal metadata -> Future Generation Computer Systems; new header comment
   recording lineage from `main_jss.tex`.
2. Abstract and introduction reframed around the brief's central question
   (Section 2) and around accounting integrity in metered computational
   services generally, with LLM inference as the concrete workload — not
   around "software architecture" (that was the JSS-specific frame).
3. Contribution list restated to foreground the distributed-systems reading
   already latent in the model (shared-state race, lifecycle commitment,
   data-authority boundary) without inventing new distributed-systems content.
4. Trim the JSS-specific "Software engineering for AI systems" and narrow the
   "Testing and validation" framing subsections; they do not serve FGCS and
   read as scope-mismatched filler there. Keep every citation that is genuinely
   about distributed systems, consistency, or cloud computing (already the
   majority of the 56 references added for JSS).
5. Add a new subsection, "Evidence from Deployed Systems," with the verified
   evidence table from Section 8A above, placed in Related Work or as its own
   short section per the brief's suggested structure.
6. Add the price-ratio context (Section 8C above) as two or three sentences
   plus the small table in the Economic Analysis section; do not expand it
   into a standalone study.
7. Strengthen (not soften) the single-host and non-distributed limitation
   language so the asynchronous-settlement result cannot be misread as a
   cross-host measurement.
8. New cover letter arguing FGCS fit on the actual scope match identified in
   Section 3, not a generic resubmission letter.
9. No numeric result, table, figure, or equation changes anywhere.

## 12. What is explicitly not being done

- No two-machine experiment (infeasible here; reported as a limitation).
- No new attack, no third accounting backend, no GPU/vLLM campaign, no
  liveness/refinement proof, no parameterized TLA+ model, no third-party
  exploitation, no disclosure campaign — all explicitly out of scope per the
  brief and not needed to fix any real gap in the manuscript.
- No restructuring into the brief's suggested 14-section outline where the
  existing structure already serves the material better; the existing
  section order is preserved except for the one new subsection in Section 11.
