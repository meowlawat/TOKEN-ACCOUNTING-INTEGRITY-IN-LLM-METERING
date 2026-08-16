| id | failure injected | architecture | delivered | net debit | refund | leakage | invariant |
|---|---|---|---|---|---|---|---|
| F1 | client disconnect mid-stream | post_completion | yes | 0.0000 | 0.0000 | 0.2375 | VIOLATED |
| F1 | client disconnect mid-stream | reserve_reconcile | yes | 0.2375 | 0.2175 | 0.0000 | HELD |
| F2 | client disconnect before first token | post_completion | yes | 0.0000 | 0.0000 | 0.0275 | VIOLATED |
| F2 | client disconnect before first token | reserve_reconcile | yes | 0.0275 | 0.4275 | 0.0000 | HELD |
| F8 | partial/truncated stream near completion | post_completion | yes | 0.0000 | 0.0000 | 0.4325 | VIOLATED |
| F8 | partial/truncated stream near completion | reserve_reconcile | yes | 0.4325 | 0.0225 | 0.0000 | HELD |
| F9 | audit read before settle grace period | post_completion | yes | 0.0000 | 0.0000 | 0.2375 | VIOLATED |
| F9 | audit read before settle grace period | reserve_reconcile | yes | 0.2375 | 0.2175 | 0.0000 | HELD |
| F5 | missing/unknown usage metadata | client | yes | 0.6725 | 0.0000 | 0.0000 | HELD |
| F5 | missing/unknown usage metadata | server_recount | yes | 0.6725 | 0.0000 | 0.0000 | HELD |
| F7 | duplicate usage metadata (replayed request_i | client | yes | 0.2750 | 0.0000 | 0.3975 | VIOLATED |
| F7 | duplicate usage metadata (replayed request_i | server_recount | yes | 0.6725 | 0.0000 | 0.0000 | HELD |
| F6 | delayed/out-of-order usage metadata | client | yes | 0.4550 | 0.0000 | 0.2175 | VIOLATED |
| F6 | delayed/out-of-order usage metadata | server_recount | yes | 0.6725 | 0.0000 | 0.0000 | HELD |
| F4 | tokenizer/recount engine unavailable | bench/server_recount | no | 0.0000 | 0.0000 | 0.0000 | HELD |
