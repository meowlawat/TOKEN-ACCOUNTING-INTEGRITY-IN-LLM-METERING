# Reproducibility and empirical extension report

Date: 2026-11-06

Baseline commit: `6a18796`

Scope: frozen local evidence only; no model endpoint, cloud host, or external party was used.

## Independent raw-evidence audit (E2)

The independent auditor reads JSON directly and imports no application or experiment
implementation modules. It recomputed record arithmetic, identifiers, headline ratios,
fail-closed behavior, and the preregistered M2 repricing analysis.

Command:

```text
python audit/taisap_upgrade/scripts/audit_raw_results.py --repo . --output audit/taisap_upgrade/results
```

Result: exit 0. It audited 2,400 M1 records, 4,800 M2 records, and 420 B0 trials.
There were zero arithmetic mismatches, duplicate request IDs, and missing required fields.
The stored controlled M2 output-90 efficiency recomputed to 58.3% and the real-stack
counterpart to 69.0% at manuscript precision. The maximum stored recount fraction was
0.023693%, below 0.1%, and the F4 recount failure was fail-closed.

E2 repriced 3,120 frozen records under three locked bases (9,360 record-basis cells).
There were zero positive-leak cells for server-authoritative architectures and zero
pricing-field dependency violations. This supports the preregistered claim only for the
stored datasets and pricing functions; it is not external validation.

Authoritative artifact: `results/independent_audit.json`. Its input section records the
SHA-256 digest of every source file.

## Clean-worktree regeneration

A detached worktree at baseline commit `6a18796` was used so tracked products could not
be mistaken for newly generated products. Direct script invocation failed:

```text
python experiments/summarize_m1.py
ModuleNotFoundError: No module named 'experiments'
```

The supported module invocations succeeded:

```text
python -m experiments.summarize_m1 --input results/raw/m1_20260816T123351Z.json
python -m experiments.summarize_m2 --input results/raw/m2_20260816T123522Z.json
python -m experiments.figures
python -m experiments.tables
```

Regenerated M1/M2 processed JSON, CSV, and Markdown summaries were byte-identical to the
tracked products. All explicitly regenerated table files were also byte-identical.

## Figure provenance defect and repair

The original figure and table entry points selected whichever matching summary had the
newest filesystem modification time. The figure directory was not cleared, so a figure
from an earlier input selection could remain even when the current input could not produce
it. In particular, `fig_m2_concurrency.png` remained in the tracked directory although the
explicit `m2_tiers.summary.json` input has no multi-concurrency output.

Both entry points now accept exact `--m1`, `--m2`, `--b0`, and `--output` paths. The audit
used an isolated output directory:

```text
python -m experiments.figures --m1 results/processed/m1_20260816T123351Z.summary.json --m2 results/processed/m2_tiers.summary.json --b0 results/class6_20260816T123031Z.summary.json --output audit/taisap_upgrade/results/regenerated_figures
python -m experiments.tables --m1 results/processed/m1_20260816T123351Z.summary.json --m2 results/processed/m2_tiers.summary.json --b0 results/class6_20260816T123031Z.summary.json --output audit/taisap_upgrade/results/regenerated_tables
```

Only `fig_architecture_safety.png` was byte-identical. B0, both M1 figures, and the M2
heatmap differed from tracked PNGs; the underlying regenerated tables and summaries did
not differ. The audit preserves the regenerated PNGs separately and does not replace the
original experimental evidence. These differences are therefore classified as stale or
environment-sensitive presentation artifacts, not new empirical results.

## Unexecuted protocols

- **E3 remains PROPOSED_ONLY.** `docker version` found Docker client 29.8.0 but could not
  connect to `DockerDesktopLinuxEngine`; the named pipe did not exist. No one of the 1,200
  planned trials ran.
- **E4 remains HUMAN_APPROVAL_REQUIRED.** It requires an authorized second host and may
  incur cloud cost. No host was provisioned or contacted.

## Reproducibility conclusion

The numerical M1/M2 products and independent headline checks reproduce from the frozen
raw evidence. Figure selection was not reproducible by provenance and has been repaired
for future runs. The manuscript must not imply that E3 or E4 has been executed, and it
must distinguish the stored two-machine evidence from an independent replication.
