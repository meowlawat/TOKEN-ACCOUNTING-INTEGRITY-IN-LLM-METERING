| architecture | pricing basis | manipulation T | vector change T(U) | leak eff. | why it succeeds / fails |
|---|---|---|---|---|---|
| client | category | honest | unchanged | +0.000 | T is identity (honest) |
| client | category | under_report_output_50 | output:60->30, total:98->68 | +0.324 | T lowers a category the basis prices |
| client | category | under_report_output_90 | output:60->6, total:98->44 | +0.583 | T lowers a category the basis prices |
| client | category | under_report_input_50 | input:8->4, total:98->94 | +0.014 | T lowers a category the basis prices |
| client | category | drop_reasoning | reasoning:30->0, total:98->68 | +0.324 | T lowers a category the basis prices |
| client | category | inflate_cached | output:60->30, cached_input:0->30 | +0.313 | T lowers a category the basis prices |
| client | category | total_mismatch | total:98->24 | +0.000 | T changes only the declared total; category basis never reads it |
| client | category | rounding_shave | input:8->7, output:60->57, total:98->94 | +0.036 | T lowers a category the basis prices |
| client_total | flat-total | honest | unchanged | -0.058 | T is identity (honest) |
| client_total | flat-total | under_report_output_50 | output:60->30, total:98->68 | +0.266 | T lowers the declared total the basis prices |
| client_total | flat-total | under_report_output_90 | output:60->6, total:98->44 | +0.525 | T lowers the declared total the basis prices |
| client_total | flat-total | under_report_input_50 | input:8->4, total:98->94 | -0.014 | T's change is priced at (near) the same rate |
| client_total | flat-total | drop_reasoning | reasoning:30->0, total:98->68 | +0.266 | T lowers the declared total the basis prices |
| client_total | flat-total | inflate_cached | output:60->30, cached_input:0->30 | -0.058 | T changes only subtotals; flat-total basis never reads them |
| client_total | flat-total | total_mismatch | total:98->24 | +0.741 | T lowers the declared total the basis prices |
| client_total | flat-total | rounding_shave | input:8->7, output:60->57, total:98->94 | -0.014 | T's change is priced at (near) the same rate |
