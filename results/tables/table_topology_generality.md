| mech | cell | topology | single | topology value | abs diff | diff in tokens | distinct procs | verdict |
|---|---|---|---|---|---|---|---|---|
| M1 | post_completion @0% | multiworker | 0.0045 | 0.0047 | 0.0002 | 0.15 | 4 | WITHIN 1 TOKEN |
| M1 | post_completion @25% | multiworker | 0.0285 | 0.0285 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | post_completion @50% | multiworker | 0.0540 | 0.0540 | 0.0000 | 0.01 | 4 | WITHIN 1 TOKEN |
| M1 | post_completion @75% | multiworker | 0.0810 | 0.0810 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | post_completion @90% | multiworker | 0.0960 | 0.0960 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | post_completion @100% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @0% | multiworker | -0.1020 | -0.1019 | 0.0001 | 0.09 | 4 | WITHIN 1 TOKEN |
| M1 | pre_debit @25% | multiworker | -0.0780 | -0.0780 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @50% | multiworker | -0.0525 | -0.0525 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @75% | multiworker | -0.0255 | -0.0255 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @90% | multiworker | -0.0105 | -0.0105 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @100% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @0% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @25% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @50% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @75% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @90% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @100% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @0% | multiworker | 0.0045 | 0.0045 | 0.0000 | 0.03 | 4 | WITHIN 1 TOKEN |
| M1 | reserve_refund_on_abort @25% | multiworker | 0.0285 | 0.0285 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @50% | multiworker | 0.0540 | 0.0540 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @75% | multiworker | 0.0810 | 0.0810 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @90% | multiworker | 0.0960 | 0.0960 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @100% | multiworker | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | post_completion @25% | distributed | 0.0285 | 0.0285 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | post_completion @50% | distributed | 0.0540 | 0.0540 | 0.0000 | 0.01 | 4 | WITHIN 1 TOKEN |
| M1 | post_completion @90% | distributed | 0.0960 | 0.0960 | 0.0000 | 0.03 | 4 | WITHIN 1 TOKEN |
| M1 | pre_debit @25% | distributed | -0.0780 | -0.0780 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @50% | distributed | -0.0525 | -0.0525 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | pre_debit @90% | distributed | -0.0105 | -0.0105 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @25% | distributed | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @50% | distributed | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_reconcile @90% | distributed | 0.0000 | 0.0000 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @25% | distributed | 0.0285 | 0.0285 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @50% | distributed | 0.0540 | 0.0540 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M1 | reserve_refund_on_abort @90% | distributed | 0.0960 | 0.0960 | 0.0000 | 0.00 | 4 | IDENTICAL |
| M2 | client/drop_reasoning | multiworker | 0.324 | 0.324 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/honest | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/inflate_cached | multiworker | 0.313 | 0.313 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/rounding_shave | multiworker | 0.036 | 0.036 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/total_mismatch | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/under_report_output_50 | multiworker | 0.324 | 0.324 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/under_report_output_90 | multiworker | 0.583 | 0.583 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/drop_reasoning | multiworker | 0.324 | 0.324 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/honest | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/inflate_cached | multiworker | 0.313 | 0.313 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/rounding_shave | multiworker | 0.036 | 0.036 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/total_mismatch | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/under_report_output_50 | multiworker | 0.324 | 0.324 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/under_report_output_90 | multiworker | 0.583 | 0.583 | 0.0000 | - | 3 | IDENTICAL |
| M2 | client_total/drop_reasoning | multiworker | 0.266 | 0.266 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/honest | multiworker | -0.058 | -0.058 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/inflate_cached | multiworker | -0.058 | -0.058 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/rounding_shave | multiworker | -0.014 | -0.014 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/total_mismatch | multiworker | 0.741 | 0.741 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/under_report_output_50 | multiworker | 0.266 | 0.266 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/under_report_output_90 | multiworker | 0.525 | 0.525 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/drop_reasoning | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/honest | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/inflate_cached | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/rounding_shave | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/total_mismatch | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/under_report_output_50 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/under_report_output_90 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/drop_reasoning | multiworker | 0.000 | 0.000 | 0.0000 | - | 3 | IDENTICAL |
| M2 | server_recount/honest | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/inflate_cached | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/rounding_shave | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/total_mismatch | multiworker | 0.000 | 0.000 | 0.0000 | - | 3 | IDENTICAL |
| M2 | server_recount/under_report_output_50 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/under_report_output_90 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/drop_reasoning | multiworker | 0.000 | 0.000 | 0.0000 | - | 3 | IDENTICAL |
| M2 | upstream/honest | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/inflate_cached | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/rounding_shave | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/total_mismatch | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/under_report_output_50 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/under_report_output_90 | multiworker | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/honest | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/total_mismatch | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client/under_report_output_90 | distributed | 0.583 | 0.583 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/honest | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/total_mismatch | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_logged/under_report_output_90 | distributed | 0.583 | 0.583 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/honest | distributed | -0.058 | -0.058 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/total_mismatch | distributed | 0.741 | 0.741 | 0.0000 | - | 4 | IDENTICAL |
| M2 | client_total/under_report_output_90 | distributed | 0.525 | 0.525 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/honest | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/total_mismatch | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | hybrid_reconcile/under_report_output_90 | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/honest | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/total_mismatch | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | server_recount/under_report_output_90 | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/honest | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
| M2 | upstream/total_mismatch | distributed | 0.000 | 0.000 | 0.0000 | - | 3 | IDENTICAL |
| M2 | upstream/under_report_output_90 | distributed | 0.000 | 0.000 | 0.0000 | - | 4 | IDENTICAL |
