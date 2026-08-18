| architecture | abort | n | tokens delivered | leak ($) | violations | verdict | matches mock |
|---|---|---|---|---|---|---|---|
| post_completion | abort50 | 5 | 24 | +0.212500 | 5 | leaks | yes |
| post_completion | abort90 | 5 | 43 | +0.355000 | 5 | leaks | yes |
| post_completion | complete | 5 | 48 | +0.000000 | 0 | no leak | yes |
| reserve_refund_on_abort | abort50 | 5 | 24 | +0.212500 | 5 | leaks | yes |
| reserve_refund_on_abort | abort90 | 5 | 43 | +0.355000 | 5 | leaks | yes |
| reserve_refund_on_abort | complete | 5 | 48 | +0.000000 | 0 | no leak | yes |
| reserve_reconcile | abort50 | 5 | 24 | +0.000000 | 0 | no leak | yes |
| reserve_reconcile | abort90 | 5 | 43 | +0.000000 | 0 | no leak | yes |
| reserve_reconcile | complete | 5 | 48 | +0.000000 | 0 | no leak | yes |
| pre_debit | abort50 | 5 | 24 | -0.180000 | 0 | overcharges | yes |
| pre_debit | abort90 | 5 | 43 | -0.037500 | 0 | overcharges | yes |
| pre_debit | complete | 5 | 48 | +0.000000 | 0 | no leak | yes |
