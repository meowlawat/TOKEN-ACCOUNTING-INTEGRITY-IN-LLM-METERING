# TAISAP Scientific Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently audit, reproduce, scientifically strengthen, and honestly repackage the LLM metering manuscript, ending with an evidence-based venue decision and submission-readiness verdict.

**Architecture:** Work claim-first through versioned audit artifacts under `audit/taisap_upgrade/`, leaving historical sources and raw evidence unchanged. Each phase produces a machine-checkable report or testable artifact consumed by later phases; manuscript changes occur only after the venue/contribution gate and are traced back to the claim-evidence ledger.

**Tech Stack:** Python 3.11+, pytest, FastAPI, PostgreSQL, Redis, Docker Compose, TLA+/TLC, LaTeX/acmart, BibTeX, Tectonic, PowerShell, Git.

**Spec:** `E:/downloads/Codex_Journal_Fit_Scientific_Rebuild_Master_Prompt_v2.md` (the requested `TAISAP_Codex_Research_Upgrade_Prompt.md` was not present; this supplied file matches the requested workflow and is treated as the intended specification).

## Global Constraints

- Preserve original raw data, historical manuscript versions, release tags, and archived artifacts; write fresh evidence to new versioned paths.
- Never invent scientific novelty, measurements, citations, external validation, reviewer outcomes, or editorial status.
- No pushes, submissions, public releases, editor contact, paid cloud resources, or internet-facing services without explicit authorization.
- Run security experiments only against the local authorized testbed; never probe third-party services.
- Record hypothesis, proposed-only, executed, reproduced, failed, and unresolved states distinctly.
- Commit logical local milestones without AI-attribution trailers and without adding the untracked user-owned `AGENTS.md` unless explicitly requested.
- Treat prior audit reports as claims to verify, not authority.
- Do not restructure the manuscript before the Phase 1.5 venue/contribution gate.
- Keep the inherited figure-accessibility and Hardik-ORCID edits preserved but uncommitted until Phase 7, where they are verified against the selected venue.

## Review Focus

- A clean build must independently settle the 31/32-page and 81/85-reference discrepancies, including stale generated artifacts.
- Anonymous output must not leak identities through body text, URLs, file metadata, DOI/artifact links, acknowledgements, or filenames.
- Reproduction scripts must fail closed on missing, duplicated, truncated, or internally inconsistent raw records.
- Formal checks must distinguish expected counterexamples from unexpected failures and must not report bounded TLC checks as proofs.
- Infrastructure tests must preserve vulnerable-by-design experiment modes while safe defaults prevent accidental external exposure.

---

### Task 1: Branch-safe baseline inventory and immutable manifest

**Files:**
- Create: `audit/taisap_upgrade/00_baseline_and_claims.md`
- Create: `audit/taisap_upgrade/claim_evidence.csv`
- Create: `audit/taisap_upgrade/baseline/sha256_manifest.csv`
- Create: `audit/taisap_upgrade/baseline/environment.txt`
- Create: `audit/taisap_upgrade/baseline/repository_inventory.txt`
- Create: `audit/taisap_upgrade/scripts/check_baseline_inventory.py`
- Test: `audit/taisap_upgrade/tests/test_baseline_inventory.py`

**Interfaces:**
- Consumes: repository state at branch point `95103f1`, current working-tree changes, and the governing specification.
- Produces: stable file/evidence identifiers and the canonical claim list consumed by Tasks 2–10.

- [ ] Write inventory tests asserting required claim rows, SHA-256 format, explicit status vocabulary, and preservation of historical/raw paths.
- [ ] Run `python -m pytest audit/taisap_upgrade/tests/test_baseline_inventory.py -v` and confirm RED because artifacts do not yet exist.
- [ ] Inventory branches, commits, manuscript variants, decisions, code, tests, formal specs, Docker definitions, raw/processed results, figures, and submission files; create manifest and claim matrix.
- [ ] Read the complete current manuscript, both TLA+ specs, implementation entry points, accounting/worker code, and submission notes; record defects and exact evidence links.
- [ ] Run the inventory test and confirm GREEN.
- [ ] Commit only Task 1 artifacts with message `audit: establish TAISAP upgrade baseline`.

### Task 2: Clean manuscript build and bibliography reconciliation

**Files:**
- Create: `audit/taisap_upgrade/baseline/build_named.log`
- Create: `audit/taisap_upgrade/baseline/build_anonymous.log`
- Create: `audit/taisap_upgrade/baseline/pdf_inspection.md`
- Create: `audit/taisap_upgrade/baseline/bibliography_reconciliation.csv`
- Create: `audit/taisap_upgrade/scripts/audit_submission_build.py`
- Test: `audit/taisap_upgrade/tests/test_submission_build_audit.py`

**Interfaces:**
- Consumes: Task 1 manifest and current named/anonymous LaTeX/BibTeX sources.
- Produces: independently measured page/reference/citation counts and anonymity findings for Tasks 3, 8, and 9.

- [ ] Write failing tests for physical page count, `.bib`/`.bbl`/cited-key reconciliation, duplicate/missing/unused keys, undefined citations, and identity-token scans.
- [ ] Run the focused test and confirm RED before the auditor exists.
- [ ] Build in a clean temporary directory with recorded tool versions and warnings; compare hashes and rendered significant pages with existing PDFs.
- [ ] Implement the independent build auditor without importing manuscript-generation code.
- [ ] Classify bibliography entries as directly verified, inherited/unchecked, broken, or uncertain; reconcile 31/32 and 81/85 claims.
- [ ] Run focused tests and the repository's existing manuscript checks; confirm GREEN or record named baseline failures.
- [ ] Commit with message `audit: reconcile TAISAP builds and bibliography counts`.

### Task 3: Adversarial literature review and venue/contribution gate

**Files:**
- Create: `audit/taisap_upgrade/01_novelty_and_venue_fit.md`
- Create: `audit/taisap_upgrade/prior_work_matrix.csv`
- Create: `audit/taisap_upgrade/01B_editorial_history_and_venue_matrix.md`
- Create: `audit/taisap_upgrade/01C_primary_contribution_decision.md`
- Create: `audit/taisap_upgrade/01D_submission_route_recommendation.md`
- Create: `audit/taisap_upgrade/tests/test_venue_gate.py`

**Interfaces:**
- Consumes: Tasks 1–2 evidence and current official journal/literature sources.
- Produces: exactly one primary paper identity, one target venue, one fallback, a GO/CONDITIONAL GO/NO-GO decision, and falsifiable switch conditions for Tasks 4–10.

- [ ] Write a failing structural test requiring 15–25 prior works, all candidate journals, three hostile-editor abstracts, weighted scorecard fields, citation URLs, observation dates, and one explicit gate result.
- [ ] Verify RED.
- [ ] Search and verify primary literature and official venue policies; separate direct verification from inference and UNKNOWN fields.
- [ ] Reconstruct editorial history only from local primary evidence; mark missing decisions UNKNOWN.
- [ ] Write the three reviewer perspectives, venue matrix, alternative abstracts, four hostile-editor sentences, and decisive gate artifacts.
- [ ] Run the gate test and confirm GREEN.
- [ ] Commit with message `research: decide contribution identity and journal route`.

### Task 4: Preregistered decisive extension plan

**Files:**
- Create: `audit/taisap_upgrade/02_preregistered_extension_plan.md`
- Create: `audit/taisap_upgrade/protocols/experiment_manifest.schema.json`
- Test: `audit/taisap_upgrade/tests/test_preregistered_plan.py`

**Interfaces:**
- Consumes: Task 3 selected identity and unresolved objections.
- Produces: 3–5 falsifiable experiments, including one designed to falsify the central claim, with locked metrics/criteria consumed by Tasks 5–6.

- [ ] Write a failing test requiring hypotheses, null outcomes, controls, sample sizes, exclusions, metrics, interpretation under positive/null results, resources, and execution status for each experiment.
- [ ] Verify RED.
- [ ] Write the minimal decisive preregistration and machine-readable manifest schema; label cloud-dependent work `HUMAN_APPROVAL_REQUIRED` and local work `PROPOSED_ONLY` until run.
- [ ] Run tests and confirm GREEN.
- [ ] Commit before any new scientific run with message `research: preregister decisive TAISAP extension tests`.

### Task 5: Formal-model independent rerun and bounded extension

**Files:**
- Create: `audit/taisap_upgrade/03_formal_review.md`
- Create: `audit/taisap_upgrade/formal_runs/`
- Modify only if evidence requires: `formal/*.tla`, `formal/*.cfg`, formal runner scripts
- Test: existing formal regressions plus new focused tests under `audit/taisap_upgrade/tests/`

**Interfaces:**
- Consumes: Task 4 formal hypotheses and existing TLA+/TLC models/configurations.
- Produces: captured 40-outcome rerun, async state counts, counterexamples, and carefully bounded necessary/sufficient/conditional statements for Task 8.

- [ ] Add failing regression checks for declared configuration/outcome counts and any proposed model extension.
- [ ] Verify RED for new checks.
- [ ] Read specs line by line; rerun TLC with pinned/reported tooling and capture commands, versions, exits, states, and traces.
- [ ] Implement only preregistered bounded extensions that materially answer the gate objection; preserve original models and outputs.
- [ ] Run full formal regression; document unexpected failures and scope.
- [ ] Commit with message `formal: independently verify accounting safety models`.

### Task 6: Empirical reproduction, independent auditor, and local extensions

**Files:**
- Create: `audit/taisap_upgrade/04_reproducibility_and_experiments.md`
- Create: `audit/taisap_upgrade/run_manifests/`
- Create: `audit/taisap_upgrade/results/`
- Create or modify: independent raw-results auditor and focused tests
- Modify only as preregistered: experiment runners/figure generators

**Interfaces:**
- Consumes: Task 4 experiment definitions and Task 1 evidence paths.
- Produces: fresh local reproduction outputs, old-vs-new comparisons, independent recomputation, and any executed extension results for Tasks 8–10.

- [ ] Write failing tests for raw-record conservation, debit/refund recomputation, duplicate/missing events, fail-closed behavior, and paper-value tolerances.
- [ ] Verify RED.
- [ ] Record environment and reproduce existing results from clean local dependencies where feasible; never overwrite original raw data.
- [ ] Implement and run the independent auditor without importing measurement-producing application code.
- [ ] Run only zero-cost authorized preregistered local extensions; preserve proposed cloud/two-machine reruns as unexecuted protocols unless already locally reproducible.
- [ ] Regenerate figures/tables by script and compare to manuscript values.
- [ ] Run focused and full suites; commit with message `experiment: reproduce and audit metering results`.

### Task 7: Artifact security hardening without erasing experimental variables

**Files:**
- Create: `audit/taisap_upgrade/05_artifact_security_review.md`
- Modify: Docker/config/deployment files and tests only for confirmed defects
- Test: focused security regression tests plus existing suite

**Interfaces:**
- Consumes: Task 1 topology inventory and Task 6 runnable environment.
- Produces: safe defaults, preserved vulnerable profiles, and verified setup/teardown behavior for Task 9 packaging.

- [ ] Write failing tests for loopback/default binds, secret/default credential rejection, Redis authentication/TLS declarations where applicable, tenant request-ID isolation, replay/idempotence, fail-closed errors, and cleanup interruption.
- [ ] Verify RED for each confirmed defect before fixing it.
- [ ] Harden only confirmed infrastructure defects; isolate and label intentionally vulnerable experimental modes.
- [ ] Run focused tests and the full suite.
- [ ] Commit with message `security: harden reproducibility artifact defaults`.

### Task 8: Evidence-bound scientific manuscript revision

**Files:**
- Create: selected-venue manuscript source from current source without modifying historical versions
- Create: `audit/taisap_upgrade/06_manuscript_change_log.md`
- Update: `audit/taisap_upgrade/claim_evidence.csv`
- Create/modify: numeric-regression and claim-linkage checks
- Test: manuscript build, numeric regression, citation linkage, and claim-status tests

**Interfaces:**
- Consumes: Tasks 3, 5, 6, and 7 decisions/results.
- Produces: one coherent selected-venue manuscript and tracked evidence map for Tasks 9–10.

- [ ] Write failing claim-regression tests for the selected intellectual spine, workload scoping, bounded-formal language, closest-prior-work confrontation, and unresolved limitations.
- [ ] Verify RED.
- [ ] Create the selected-venue source and revise title/abstract/introduction/related work/threat model/formal/empirical/discussion/limitations/conclusion only where evidence warrants.
- [ ] Preserve author identities/contributions and all historical sources; document every substantive change with evidence.
- [ ] Run builds, claim tests, numeric regression, and citation checks.
- [ ] Commit with message `paper: rebuild manuscript around verified contribution`.

### Task 9: Selected-journal compliance and reproducible package

**Files:**
- Create: `audit/taisap_upgrade/07_submission_preflight.md`
- Update/create: selected-venue cover-letter draft, named/anonymous PDFs as policy requires, source archive, final manifest
- Update: figure descriptions and verified ORCID metadata only where policy/evidence permits
- Test: PDF/anonymity/reference/package checks

**Interfaces:**
- Consumes: Task 8 manuscript and current official selected-journal instructions.
- Produces: local submission package with every criterion marked PASS, FAIL, UNVERIFIED, or REQUIRES AUTHOR ACTION.

- [ ] Write failing preflight tests for physical pages, reference counts, missing markers, figures/tables, metadata, anonymity, ORCID presence, source completeness, and author-confirmation blockers.
- [ ] Verify RED.
- [ ] Apply the preserved accessibility/Hardik-ORCID edits if compatible with the selected venue; never invent Natasha's ORCID.
- [ ] Build exact package from committed sources and inspect rendered key pages.
- [ ] Keep exclusivity and coauthor/ORCID actions as explicit blockers until supplied by the author.
- [ ] Run preflight tests and commit with message `submission: assemble verified journal package`.

### Task 10: Independent adversarial review and final scientific verdict

**Files:**
- Create: `audit/taisap_upgrade/08_adversarial_review.md`
- Create: `audit/taisap_upgrade/09_final_scientific_integrity_audit.md`
- Create: `README_UPGRADE_SUMMARY.md`
- Create: one-page internship research-evidence brief

**Interfaces:**
- Consumes: all prior tasks and branch diff.
- Produces: four independent specialty reviews, resolved major findings, exact execution record, final readiness verdict, and human-only decisions.

- [ ] Prepare review package and dispatch independent reviewers for venue novelty, distributed systems, formal/reproducibility, and methodology/external validity as permitted by the governing spec.
- [ ] Re-grade findings; for every Critical/Important issue write a failing regression test, verify RED, fix once, verify GREEN, and rerun the full suite.
- [ ] Record deferred minors and rulings explicitly.
- [ ] Run final builds, tests, formal checks, manifest generation, and repository status audit.
- [ ] Write the final integrity audit, evidence brief, and exact upgrade summary with changed files, commands, actual results, reduced/removed claims, strongest objection, venue fit, readiness, and author actions.
- [ ] Commit with message `audit: issue final scientific upgrade verdict`.
