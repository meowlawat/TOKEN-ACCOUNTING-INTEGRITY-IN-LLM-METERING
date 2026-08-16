| architecture | reservation | abort-finalization | worst leak/req | integrity | served (budget 2) | solvency |
|---|---|---|---|---|---|---|
| pre_debit | yes | n/a (pre-committed) | -0.0090 | held | 2/6 | ok |
| reserve_reconcile | yes | yes | +0.0000 | held | 2/6 | ok |
| reserve_refund_on_abort | yes | no | +0.0845 | VIOLATED | 6/6 | ok |
| no_reserve_settle | no | yes | +0.0000 | held | 6/6 | NEGATIVE |
| post_completion | no | no | +0.0845 | VIOLATED | 6/6 | ok |
