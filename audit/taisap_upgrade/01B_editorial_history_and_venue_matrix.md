# Editorial history and venue matrix

Observed 2026-11-06. Missing decision letters are `UNKNOWN`; repository summaries are not
upgraded into primary editorial evidence.

## Reconstructed history

| Venue | Verifiable local status | Evidence limit |
|---|---|---|
| Computers & Security | Submitted 2026-08-25 as COSE-D-26-05174; same-day scope desk rejection; no external review | Repository records quote an AI/ML moratorium, but the original email/portal export is absent |
| JISA | No longer under consideration | Manuscript number, date, reason, and decision letter are `UNKNOWN` |
| Computer Networks | Package prepared; not submitted | No editorial decision exists |
| Journal of Systems and Software | Repository records manuscript JSSOFTWARE-S-26-03217 as submitted | Current disposition and decision letter are `UNKNOWN` |
| FGCS | Repository contains a resubmission audit naming FGCS-D-26-05286 | Original decision/status export is absent; current exclusivity is `UNKNOWN` and requires author confirmation |
| TAISAP | Package prepared; not submitted | No editorial history |

The unknown exclusivity state is a human gate: no submission can occur until the authors
confirm that no venue is currently considering the work.

## Venue facts

- **TAISAP:** official ACM guidance retrieved by the user and recorded locally requires
  double-anonymous review and places security of AI systems/environments, including
  technical and economic methods, in scope. The live ACM page is
  <https://dl.acm.org/journal/taisap/author-guidelines>; automated access returned 403 in
  this pass, so the full policy text is locally page-verified but not freshly fetched.
- **Wiley Security and Privacy:** its official author page explicitly welcomes broad
  information security, cloud security, applied case studies, testbeds, simulations, and
  theoretical work; review is single-anonymous.
  <https://onlinelibrary.wiley.com/page/journal/24756725/homepage/forauthors.html>
- **ACM TOPS:** a high-fit security venue in subject but a harder novelty/impact bar. The
  official page is <https://dl.acm.org/journal/tops/author-guidelines>; automated access
  returned 403, so requirements beyond general ACM policy remain `UNKNOWN` here.
- **IJIS:** the official scope covers theory, applications, and implementations of
  information security. It uses single-blind review and currently requests Springer
  two-column LaTeX. <https://link.springer.com/journal/10207/aims-and-scope> and
  <https://link.springer.com/journal/10207/submission-guidelines>.

## Weighted scorecard

Scores are 1–5. Weights: scope 30%, contribution-type fit 25%, evidence fit 20%, package
cost 10%, desk-risk inverse 15%.

| Venue | Scope | Contribution fit | Evidence fit | Package cost | Inverse desk risk | Weighted / 5 | Ruling |
|---|---:|---:|---:|---:|---:|---:|---|
| TAISAP | 5 | 4 | 4 | 5 | 3 | 4.20 | Primary, conditional |
| Wiley Security and Privacy | 4 | 4 | 4 | 3 | 4 | 3.95 | Fallback |
| TOPS | 4 | 3 | 3 | 4 | 2 | 3.20 | Too high-risk before stronger extension |
| IJIS | 4 | 3 | 4 | 2 | 3 | 3.35 | Viable second fallback; costly reformat |

TAISAP wins because the AI-serving security boundary and economic method are explicit
rather than incidental, and the current package already fits its format. Wiley is the
best fallback because applied testbeds and simulation/theory combinations are explicitly
welcomed. TOPS should become primary only if the decisive extension materially expands
the scientific result, not merely the dataset.

