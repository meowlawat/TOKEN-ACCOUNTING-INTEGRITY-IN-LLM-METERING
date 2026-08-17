# Audit Baseline

State frozen before any auditor action.

| item | value |
|---|---|
| Commit | `f533d69880cfc2492fb17e34d04ce8964e844fc1` |
| Branch | `master` |
| Working tree | clean |
| Auditor start | 2026-08-17 |
| Host Python | 3.13.5 |
| Container Python | 3.11 |
| Docker | 29.7.2 / Compose 5.3.1 |
| PostgreSQL / Redis | 16.15 / 7.4.10 |
| Stack at audit start | `sepaper` (single-worker control) running on :8000 |

## Auditor independence measures

- All recomputation code is newly written in `audit/` and imports **nothing** from
  `app/`, `attacks/`, `defenses/`, `experiments/`, or `benchmarks/`.
- Ground truth (true usage vectors, token counts) is re-derived from the documented
  mock specification using an independent SHA-256 implementation, **not** read from the
  gateway's own `extra["true"]` field.
- Pricing, all seven attacker transformations, and the per-architecture billing basis
  are independently re-implemented from the specification.
- Raw JSON and the live database are treated as authoritative over processed summaries,
  tables, and the paper.

## Audit artifacts

| file | purpose |
|---|---|
| `audit/AUDIT_BASELINE.md` | this file |
| `audit/recompute_all.py` | independent recomputation (no project imports) |
| `audit/recompute_results.json` | machine-readable recomputation output |
| `AUDIT_REPORT.md` | findings and verdict |
