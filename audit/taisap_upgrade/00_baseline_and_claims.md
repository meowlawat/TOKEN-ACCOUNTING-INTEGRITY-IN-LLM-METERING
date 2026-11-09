# Phase 0 baseline and claim audit

Date: 2026-11-06

Branch: `research/taisap-scientific-upgrade-2026`

Branch point: `95103f1faafa62d926a1350295551f91d57e0f2f`

## Scope and preservation

This is an independent baseline, not an endorsement of prior audit reports. Historical
manuscripts, release artifacts, and raw results remain read-only. New checks and outputs
live under `audit/taisap_upgrade/`. The untracked, user-owned `AGENTS.md` is not part of
this work. Two inherited working-tree edits (Hardik's ORCID and six ACM figure
descriptions in the named and anonymous TAISAP sources) are preserved for venue-phase
verification and are not treated as baseline evidence.

The requested `TAISAP_Codex_Research_Upgrade_Prompt.md` was not present. The supplied
`E:/downloads/Codex_Journal_Fit_Scientific_Rebuild_Master_Prompt_v2.md` was read in full
and is the governing specification because its phase structure and constraints match the
request. This filename substitution is explicit so it cannot be mistaken for provenance.

## Inventory completed

The generator records branches and recent commits; named, anonymous, and historical
manuscripts; submission files; application and accounting implementations; experiment
drivers; formal specifications and configurations; raw and processed results; deployment
definitions; figures; and reproduction scripts. `baseline/sha256_manifest.csv` fixes the
content identity of the evidence-bearing tree without hashing this new audit into itself.
`baseline/environment.txt` records the branch point, current head, branch, dirty state,
Python runtime, and platform.

The following sources were read as code or scientific evidence rather than accepted from
their summaries:

- the complete `paper/main_taisap.tex`, including claims, limitations, ethics, and data
  availability;
- `formal/TokenAccounting.tla`, `formal/AsyncSettlementTOCTOU.tla`, their configurations,
  `formal/check.py`, and `formal/README.md`;
- B0 debit primitives, M1/M2 architecture descriptors, accounting backends, asynchronous
  worker and routing entry points;
- TAISAP final audit, QA report, verification log, and change log.

## Baseline scientific position

The manuscript studies under-payment by an authenticated dishonest client against an
honest provider. Its central safety property is per-request accounting integrity,
`V(r) <= N(r)`, with solvency and ledger conservation treated separately. B0 is explicitly
a known synchronization baseline. The claimed contribution is a unified lifecycle model,
the M1 reservation/finalization ablation, the M2 distinction between computing a recount
and making it authoritative for billing, finite-state model checking, empirical
realizability, and measured defense cost.

The code contains deliberately vulnerable modes alongside hardened controls. B0's
vulnerable implementation performs a stale absolute write; the hardened control uses an
atomic guarded decrement. M1 enumerates the two-by-two reservation/finalization design
space. M2 separates client, logged-client, upstream, recount, and reconcile authorities.
The asynchronous family uses a PostgreSQL outbox and idempotent application but retains a
vulnerable deferred-authorization mode for experiments.

No claim is marked `REPRODUCED` at this checkpoint. Existing files establish only that
evidence is present and internally described. `claim_evidence.csv` therefore begins with
all rows `UNVERIFIED`; later phases must independently rebuild, rerun, or rederive each
claim and update the status without rewriting historical data.

## Defects and reviewer risks found at baseline

1. **Evidence pointers had drifted.** The first ledger draft cited a nonexistent B0 raw
   timestamp, a nonexistent async-summary filename, and directories rather than files for
   several claims. A failing test exposed this; all ledger paths now resolve to concrete
   files.
2. **The principal invariant is local, not sufficient by itself.** B0's synchronous lost
   update can satisfy per-request accounting integrity while violating ledger conservation;
   the asynchronous admission race can satisfy both per-request integrity and conservation
   while violating solvency. Any abstract or conclusion that calls `V(r) <= N(r)` the sole
   global integrity condition would be incomplete. The manuscript mostly distinguishes
   these properties, but Phase 1 must test the framing consistently.
3. **Formal results are bounded model checking.** The primary model checks small request
   counts and unit pricing under strong consistency. The async model is untimed and checked
   at two finite `(N,k)` points. Neither is an implementation refinement proof, a distributed
   systems proof, nor evidence about arbitrary pricing/tokenizer behavior.
4. **The two B0 models encode different races.** `TokenAccounting.tla` models a blind
   stale overwrite and predicts a ledger-conservation failure; the async model predicts a
   solvency failure without a lost write. This distinction is scientifically useful but
   must remain explicit to avoid presenting one formalization as general validation of the
   other.
5. **Generality remains narrow.** The real-stack evidence uses one small CPU model, one
   serving stack, and one prompt family. Physical distribution is one host pair. Backend
   parity genuinely exercises only eight sensitive cells, and B0 bypasses the backend
   abstraction. These are limitations, not external validation.
6. **The headline defense-cost claim is configuration-bound.** The under-0.1-percent
   ratio is for real autoregressive inference on the tested CPU configuration. The same
   recount is expensive relative to the zero-cost deterministic generator at long inputs;
   the manuscript reports both, and later analysis must preserve that qualification.
7. **Detectability is a withdrawn result.** Stored detectability labels were assigned from
   architecture metadata and the ground-truth-rich harness prevents the intended
   distinction. The manuscript correctly makes no detectability claim; no later phase may
   resurrect the metric without new instrumentation and preregistration.
8. **Prior venue and submission reports are secondary evidence.** Existing TAISAP audit
   notes document page, anonymity, ORCID, and accessibility conclusions, but Phase 2 must
   rebuild in a clean directory and measure the PDFs directly. Recorded 31/32-page and
   81/85-reference discrepancies remain unresolved until that build.
9. **Anonymous artifacts require a fresh identity scan.** Repository/DOI links, body
   sections, PDF metadata, source filenames, acknowledgements, and author-contribution text
   can defeat double anonymity even when the title block is anonymous.
10. **Artifact version statements need reconciliation.** The manuscript names Git tag
    `v1.1.0` and Zenodo concept/version DOIs while the repository has continued to evolve.
    Later packaging must prove that every claimed file/result exists in the cited release
    or narrow the statement; it must not update or publish an archive without authorization.
11. **External issue numbers are not our measurements.** The OpenGateLLM 254,347-token
    statement is a third-party report and requires source-level verification and wording
    that cannot imply independent reproduction.
12. **Venue fit is not yet decided.** Existing TAISAP framing is plausible, but the
    governing specification requires the literature/novelty review and a documented venue
    gate before scientific restructuring or new manuscript claims.

## Claim ledger contract

Statuses are restricted to `REPRODUCED`, `SUPPORTED_BY_EXISTING_DATA`, `UNVERIFIED`,
`FAILED`, `PROPOSED_ONLY`, and `HUMAN_APPROVAL_REQUIRED`. Every evidence path is a concrete
existing file. A claim can advance to `REPRODUCED` only after an independent command in
this upgrade produces matching output. `SUPPORTED_BY_EXISTING_DATA` means the stored data
were independently rederived but the generating experiment was not rerun. Proposed
experiments remain `PROPOSED_ONLY` until execution.

## Immediate next checkpoint

Task 2 performs clean named and anonymous builds, reconciles `.bib`, `.bbl`, and cited
keys, counts physical pages and rendered references, scans visible text and PDF metadata
for identity leaks, and records every command. That build evidence is required before the
literature/venue gate or manuscript restructuring.
