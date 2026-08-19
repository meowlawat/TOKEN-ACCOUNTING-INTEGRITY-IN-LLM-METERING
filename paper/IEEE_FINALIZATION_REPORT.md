# IEEE finalization report

*Conversion of the validated manuscript to an IEEE journal article. No experiment was
re-run for editorial reasons and no experimental value changed. Two things did change in
the manuscript's factual content, both because verification exposed a defect: one citation
was wrong and has been removed, and one citation's title was incorrect and has been
corrected.*

---

## IEEE class

`\documentclass[journal]{IEEEtran}` — two-column journal mode, compiled with tectonic
(XeTeX). IEEEtran is used correctly: title/author block with `\thanks` footnotes,
`abstract`, `IEEEkeywords`, `\IEEEPARstart`, numbered sections and equations, IEEE table
and figure conventions, IEEE-style numbered bibliography.

## Final title

**Token-Accounting Integrity in LLM Metering: A Systematic Study of Client-Side
Under-Payment**

Chosen over the previous subtitle ("Measuring Client-Side Under-Payment in LLM Metering
Architectures") because the paper is no longer a measurement study alone — it now carries
model checking, cross-architecture validation and defense conditions, and "systematic
study" reflects that without inflating it.

## Author

Hardik
Enrollment: 03517713524

No affiliation was invented. The enrollment number appears in a `\thanks` footnote, which
is where IEEEtran expects non-affiliation author data.

## Build metrics

| item | value |
|---|---|
| Pages | 13 |
| Sections | 15 |
| Tables | 9 (2 authored inline, 7 generated from raw data) |
| Figures | 5 |
| References | 26 |
| In-text citations | 47 |
| Abstract length | 273 words |
| Undefined references | 0 |
| Undefined citations | 0 |
| Uncited bibliography entries | 0 |
| Duplicate references | 0 |
| Duplicate labels | 0 |
| Overfull boxes | 0 |
| Underfull boxes | 23 (justified two-column text; visually harmless) |
| Blank pages | 0 |
| Pages after bibliography | 0 |

## Reference hardening

Every entry was retrieved from an authoritative source before being cited — arXiv abstract
pages, Crossref DOI records, the MITRE CWE database, the GitHub REST API, the WHATWG HTML
standard, and the OWASP GenAI project page. Nothing was taken from a search-result snippet.
Full provenance per entry is in `paper/ieee_reference_audit.md`.

**Two corrections came out of that process, and both are substantive:**

1. **A wrong citation was removed.** The manuscript cited `CVE-2026-31873` as a Tyk API
   Gateway non-atomic quota check/decrement race. Both the MITRE CVE Services record and
   the NVD record show that identifier belongs to an unrelated Unhead URI-scheme
   sanitization bypass. A web search returned a blog asserting the Tyk attribution; two
   authoritative registries contradict it, so the registries win. The citation is gone. B0
   remains supported by CWE-807 and by Kettle's web race-conditions research, both
   verified.
2. **A citation title was wrong and is fixed.** Kettle's 2023 PortSwigger research was
   cited as "The single-packet attack: making remote race-conditions 'local'". The actual
   article is "Smashing the state machine: the true potential of web race conditions",
   confirmed from the page itself.

An unattributed "industry metering guidance" entry with no retrievable source was also
removed rather than given a URL found after the fact.

The reference set grew from 13 to 26 and now covers LLM billing and token accounting,
economic attacks on LLM and serverless systems, gateway provenance, generic security
foundations, streaming and cancellation semantics, transactional counter methods,
tokenization, inference serving, and formal methods. Every entry supports a specific
statement; none is padding.

## Humanization

Every section was rewritten rather than word-substituted. Concretely: the abstract was
rebuilt from 450 words across four paragraphs to a single 273-word block; list-shaped prose
was converted to argument-shaped prose; and the AI-tell constructions were removed —
no "taken together", "it is worth noting", "this highlights", "comprehensive", "novel
approach", or paragraph-terminal "in conclusion". Sentence length is deliberately varied,
and each paragraph follows claim → evidence → interpretation, with a limitation where one
is genuinely owed. Technical density was preserved: no number, hedge or caveat was dropped
to improve readability.

**Humanization pass: COMPLETE**

## Scientific content

### TLA+ results

TLC 2.19. Ten architecture configurations × four invariants = 40 exhaustive runs over
**27,526 distinct states**, with every expected outcome declared before the run and all 40
matching. Runs use a single worker deliberately: with parallel workers a run that halts at
a counterexample explores a nondeterministic number of states, and the totals drifted
between runs. The section records that our first specification was wrong — it treated a
reservation as a hold, and TLC rejected the *safe* configurations until the settlement
semantics were corrected. That failure is reported, not erased.

The section states explicitly: *we do not provide a mechanized refinement proof from the
abstract specification to the implementation.*

### Asynchronous accounting

With an honest pipeline, asynchronous accounting is **delayed rather than lossy**: the mean
exposure window tracks the configured delay (0/10/50/100/500 ms → 14.0/14.9/54.3/103.7/504.1
ms) and the leak reconciles to exactly zero. Duplicates are suppressed idempotently across
all 25 injected cases; a lost event leaks permanently. Whether a straggler looks lost or
merely late is a property of the observation horizon, and the horizon used is stated.

### B0 revised conclusion

The paper no longer implies that B0 requires concurrency. With **strictly sequential
arrivals 20 ms apart**, over-serving appears once the reconciliation delay reaches 100 ms
and reaches four requests over a two-request budget at 500 ms, with the balance driven
negative. The condition is restated throughout — abstract, B0 section, sufficiency
conditions, asynchronous section, discussion and conclusion — as:

> The authorization decision must be atomically coupled to the economic commitment on the
> path that authorizes service.

Concurrency is one way to break that coupling; delayed settlement is another, and it needs
no concurrency at all. The conclusion section says plainly that this changed, and that the
earlier framing was too weak rather than wrong.

### M1 orthogonality

Presented as the 2×2 matrix it is, with its own table: reservation alone gives solvency and
loses integrity; abort-safe finalization alone gives integrity and drives the balance
negative; only the conjunction gives both. All four cells are model-checked, and the
diagonal cells are also measured.

### M2 authority result

Presented as a chain — true usage → computation → stored usage → billing authority → debit —
with the observation that a system can compute and store the correct usage while billing
from a different, attacker-influenced representation. Measured leakage: **58.3 %** in the
controlled setting, **69.0 %** against the real serving stack, each attributed to its own
setting. The headline manipulation is K0-feasible; K1 and K2 manipulations are labelled and
kept out of the main claim. No commercial-provider claim is made.

### Real serving validation

Integrated into the main narrative in Section X, not a footnote: `llama.cpp` serving
SmolLM2-135M-Instruct on CPU, third-party serving code with a real subword tokenizer, real
SSE streaming and server-produced usage records. Zero safety disagreements across 60 cells;
five cells changed attack effectiveness and are reported. It is described as local,
controlled, one stack, one small model — explicitly not commercial validation. The
deterministic generator remains the main controlled environment.

### Withdrawn claim

Detectability remains withdrawn. The D0–D3 vocabulary does not appear anywhere in the
manuscript, and the withdrawal is documented in its own subsection with the root cause.

## Independent audit after editing

Re-run after all editorial changes, to confirm that editing did not alter experimental
truth:

| check | result |
|---|---|
| `audit/recompute_all.py` (zero project imports) | **0 discrepancies** |
| `audit/m2_independent_check.py` (spec-derived truth) | **0 mismatches** |
| `formal/check.py` | 40/40 matched, 27,526 states, **0 disagreements** |
| Claim-evidence matrix | 44 claims, **0 unsupported** |

**Unsupported claims: 0**

## Files produced

| file | purpose |
|---|---|
| `paper/main_ieee.tex` | IEEE journal manuscript |
| `paper/main_ieee.pdf` | compiled manuscript, 13 pages |
| `paper/ieee_reference_audit.md` | per-entry provenance and citation gates |
| `paper/ieee_format_audit.md` | log scan plus rendered-PDF inspection |
| `paper/reference_verification.json` | raw retrieval log |
| `results/tables/ieee/` | IEEE float variants, generated from raw data |
| `paper/accounting_state_model_ieee.tex` | full-width state-machine figure |

The validated original manuscript (`paper/main.tex`, `paper/main.pdf`) is untouched.

**No anonymous variant was produced.** *Computers & Security* and IEEE TDSC both use
single-blind review, where author identity is visible to reviewers, so an anonymized build
would be effort spent on a version neither target venue asks for. If a double-blind venue
is chosen later, the variant is a one-line change to the author block.

## What this report does not claim

The manuscript is **journal submission-ready**. That is a statement about completeness and
internal consistency, not about outcome. It is not accepted, not guaranteed publishable,
and not "Q1-ready". The known gaps remain exactly as stated in the paper: no mechanized
refinement proof, a finite formal model, an asynchronous family that is measured but not
formally modelled, one physical host, one local serving stack, and no commercial-provider
validation.
