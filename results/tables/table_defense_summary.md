| mech | architecture | verdict | max req ASR | best detect |
|---|---|---|---|---|
| M1 | pre_debit | safe | 0.00 | D3 |
| M1 | reserve_reconcile | safe | 0.00 | D3 |
| M1 | post_completion | LEAKS | 1.00 | D0 |
| M1 | reserve_refund_on_abort | LEAKS | 1.00 | D0 |
| M2 | client | LEAKS | 1.00 | D0 |
| M2 | client_logged | LEAKS | 1.00 | D1 |
| M2 | client_total | LEAKS | 1.00 | D0 |
| M2 | upstream | safe | 0.00 | D3 |
| M2 | server_recount | safe | 0.00 | D3 |
| M2 | hybrid_reconcile | safe | 0.00 | D3 |
