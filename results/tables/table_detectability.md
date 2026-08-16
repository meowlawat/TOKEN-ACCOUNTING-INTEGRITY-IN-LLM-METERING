| mech | architecture | req logs | usage ledger | reconciliation | final balance | real-time | level | detection latency |
|---|---|---|---|---|---|---|---|---|
| B0 | vulnerable (non-atomic) | no | yes | yes | no* | no | D1 | until a reconciliation pass |
| B0 | hardened (atomic CAS) | n/a | n/a | n/a | n/a | yes | D3 | 0 (prevented) |
| M1 | post_completion | partial | no | no | no | no | D0 | never (no record is written) |
| M1 | reserve_refund_on_abort | partial | yes | yes | yes | no | D1 | until a reconciliation pass |
| M1 | reserve_reconcile | n/a | n/a | n/a | n/a | yes | D3 | 0 (prevented) |
| M2 | client | no | no | no | no | no | D0 | never (ledger records the lie) |
| M2 | client_logged | no | yes | yes | no | no | D1 | until a reconciliation pass |
| M2 | server_recount | n/a | n/a | n/a | n/a | yes | D3 | 0 (prevented) |
| M2 | hybrid_reconcile | yes | yes | yes | n/a | yes | D3 | 0 (detected and corrected in-request) |
