# Evidence-bound manuscript change log

Date: 2026-11-07

Selected source: `paper/main_taisap_upgrade.tex`

Baseline source: committed `paper/main_taisap.tex` at `fc0d5c6`

Historical sources: preserved; the inherited uncommitted `main_taisap.tex` and
`main_taisap_anon.tex` changes remain outside this Task 8 commit for the later compliance
phase.

## Scientific changes

1. Replaced the title's unqualified “Verified Conditions” with “Bounded Evidence” and
   changed the abstract to say bounded exhaustive model checking. This reflects the finite
   TLA+ scope and avoids implying an implementation proof.
2. Updated the asynchronous formal section from two tested points to the six preregistered
   `(N,k)` points. The text now reports the 36-run extension, repeated-state aggregate,
   and the exact scope limits: untimed causal ordering, not a timed, network, database, or
   unbounded theorem.
3. Added an explicit comparison with the September 2026 PTIA paper and the pay-per-token
   auditing work. Those papers study dishonest providers and honest payers; this paper
   studies an honest provider and a dishonest authenticated client. The comparison is a
   threat-model distinction, not a novelty claim for a new primitive.
4. Added the independent raw-data audit outcome: 2,400 M1 records, 4,800 M2 records, 420
   B0 trials, 9,360 repriced E2 cells, zero arithmetic/duplicate/field/dependency errors,
   and a 0.023693% maximum stored recount fraction.
5. Added the explicit workload and external-validity boundary: one controlled testbed,
   one llama.cpp/SmolLM2 stack, one small CPU model, and one prompt family.
6. Added the status of unexecuted work. The 1,200-trial E3 terminal-path matrix was not
   run because Docker was unavailable, and no independent second-host replication was
   performed in this upgrade. Neither is presented as a result.

## Numerical and citation changes

- No measured headline value was changed. The selected source retains 58.3%, 69.0%,
  27,526 distinct primary-model states, 91,921 generated / 22,521 distinct async holding
  states, and the recorded overhead values.
- Added two directly cited bibliography entries: PTIA (`arXiv:2609.20370`) and
  `Auditing Pay-Per-Token in Large Language Models` (`arXiv:2510.05181`). The selected
  build therefore contains 87 bibliography items rather than the baseline 85.

## Build and regression evidence

Command, executed from `paper/`:

```text
C:\Users\hardi\bin\tectonic.exe --keep-logs --keep-intermediates \
  --outdir ../audit/taisap_upgrade/manuscript_build main_taisap_upgrade.tex
```

Observed result: exit 0; 33 physical PDF pages; 87 `\\bibitem` entries; zero `[?]` or
`(?)` markers in extracted PDF text. Tectonic emitted existing font-substitution and
underfull-box warnings but no undefined-citation or LaTeX error. The full build outputs,
including PDF, log, BBL, BLG, AUX, and extracted text scan, are retained under
`audit/taisap_upgrade/manuscript_build/`.

The source-level regression suite contains five focused tests covering the title/spine,
bounded formal language, PTIA contrast, scope/unexecuted protocols, headline numbers, and
claim-ledger statuses. The baseline inventory tests also pass against the updated ledger.

## Post-preflight abstract revision

The abstract was revised after the submission preflight to use the venue allowance without
exceeding it. The active named and anonymous sources now contain the same 281-word abstract.
An automated regression test requires an abstract length from 280 through 299 words.
