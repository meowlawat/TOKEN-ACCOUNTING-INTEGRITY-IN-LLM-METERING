# TAISAP bibliography — independent reference verification

All 81 entries in `paper/references_taisap.bib` checked directly against external
sources (Crossref API, arXiv, GitHub, standards bodies, or targeted web search) —
not against the manuscript's own metadata, and not inherited from any prior pass.
Four parallel subagents were launched to do this and all four failed on an account
rate limit before producing results; everything below was done by direct, serial
verification instead, after confirming the rate limit was fork-specific and did not
block direct tool calls.

**Summary: 81/81 checked. 81/81 classified "Verified published source" or
"Verified preprint" or "Verified technical report or public issue." 0 fabricated,
0 non-existent, 0 citation-claim mismatches found.** Two items below are flagged as
worth the author's attention even though neither is an error (see "Notes worth
reading" at the end).

| # | Key | Classification | Evidence checked | Notes |
|---|---|---|---|---|
| 1 | coin | Verified preprint | arXiv:2505.13778, title/authors/abstract confirmed | Claim match confirmed: paper shows hidden reasoning tokens can be counted/audited "only with effort" (94.7% detection rate, not 100%) |
| 2 | invisible | Verified preprint | arXiv:2505.18471, confirmed | Claim match confirmed |
| 3 | tokeninflation | Verified preprint | arXiv:2605.30040, confirmed | Confirms the ~50.85% under-reporting figure referenced elsewhere in this project's history |
| 4 | dow | Verified preprint | arXiv:2104.08031, confirmed | Claim match confirmed |
| 5 | dowreview | Verified preprint | arXiv:2508.19284, confirmed | Confirmed as a literature review as cited |
| 6 | owasp | Verified technical report | genai.owasp.org live page fetched, confirmed LLM10:2025 | none |
| 7 | llmjacking | Verified technical report | Sysdig blog post fetched, confirmed | none |
| 8 | aex | Verified preprint | arXiv:2603.14283, confirmed | none |
| 9 | gwprov | Verified preprint | arXiv:2606.22560, confirmed | none |
| 10 | cwe807 | Verified technical report | cwe.mitre.org/data/definitions/807.html fetched live | Version 4.20 matches exactly |
| 11 | newapi5235 | Verified public issue | GitHub issue #5235 fetched, confirmed title/content | Issue is actually closed "not planned" — paper doesn't claim a status for this one, so nothing to correct, but see notes below |
| 12 | aperture247 | Verified public issue | GitHub PR #247 fetched, confirmed merged, confirmed encoding-guard mechanism | none |
| 13 | kettle | Verified technical report | portswigger.net/research page fetched, confirmed | none |
| 14 | cashier | Verified published source | Crossref 10.1109/SP.2011.26, confirmed | none |
| 15 | acidrain | Verified published source | Crossref 10.1145/3035918.3064037, confirmed | none |
| 16 | armbrust | Verified published source | Crossref 10.1145/1721654.1721672, confirmed | none |
| 17 | bass | Verified published source | WebSearch confirmed real book, correct edition/year/publisher | none |
| 18 | sponge | Verified preprint | arXiv:2006.03463, confirmed | none |
| 19 | saltzer | Verified published source | Crossref 10.1109/PROC.1975.9939, confirmed | none |
| 20 | escrow | Verified published source | WebSearch confirmed, correct title/volume/pages | Discoverable DOI (10.1145/7239.7265) not in the current citation — optional completeness addition |
| 21 | sse | Verified technical report | html.spec.whatwg.org fetched live, confirmed | none |
| 22 | rfc9110 | Verified technical report | rfc-editor.org/rfc/rfc9110.html fetched live | Claim is a fair paraphrase of the RFC's general error-handling stance, not a verbatim quote — normal for a citation |
| 23 | berenson | Verified published source | Crossref 10.1145/223784.223785, confirmed | none |
| 24 | adya | Verified published source | Crossref 10.1109/ICDE.2000.839388, confirmed | none |
| 25 | sagas | Verified published source | Crossref 10.1145/38713.38742, confirmed | none |
| 26 | helland12 | Verified published source | Crossref 10.1145/2181796.2187821, confirmed | none |
| 27 | bailis | Verified published source | Crossref 10.14778/2735508.2735509, confirmed | none |
| 28 | linearizability | Verified published source | Crossref 10.1145/78969.78972, confirmed | none |
| 29 | vogels | Verified published source | Crossref 10.1145/1435417.1435432, confirmed | none |
| 30 | kleppmann | Verified published source | WebSearch confirmed, correct title/year/publisher | none |
| 31 | bpe | Verified preprint | arXiv:1508.07909, confirmed | none |
| 32 | sentencepiece | Verified preprint | arXiv:1808.06226, confirmed | none |
| 33 | vllm | Verified published source | WebSearch confirmed SOSP'23, authors match | none |
| 34 | llamacpp | Verified technical report | github.com/ggml-org/llama.cpp fetched, confirmed | none |
| 35 | smollm2 | Verified preprint | arXiv:2502.02737, confirmed as the SmolLM2 family paper | 135M variant not named in the checked abstract excerpt, but is a real public checkpoint released under this family paper — standard practice |
| 36 | tiktoken | Verified technical report | github.com/openai/tiktoken fetched, confirmed | none |
| 37 | sarathi | Verified preprint | arXiv:2403.02310, confirmed | none |
| 38 | distserve | Verified preprint | arXiv:2401.09670, confirmed | none |
| 39 | sglang | Verified preprint | arXiv:2312.07104, confirmed | none |
| 40 | leviathan | Verified preprint | arXiv:2211.17192, confirmed | none |
| 41 | petrov | Verified preprint | arXiv:2305.15425, confirmed | none |
| 42 | tla | Verified published source | WebSearch confirmed volume/pages | none |
| 43 | lamportspec | Verified published source | WebSearch confirmed, correct ISBN/year/publisher | none |
| 44 | tlc | Verified published source | WebSearch confirmed, correct venue/volume/pages | none |
| 45 | clarke | Verified published source | Crossref 10.1145/5397.5399, confirmed | none |
| 46 | spin | Verified published source | Crossref 10.1109/32.588521, confirmed | none |
| 47 | alloy | Verified published source | Crossref 10.1145/505145.505149, confirmed | none |
| 48 | awsformal | Verified published source | WebSearch confirmed, correct authors/volume/pages | Discoverable DOI (10.1145/2699417) not in the current citation — optional completeness addition |
| 49 | woodcock | Verified published source | Crossref 10.1145/1592434.1592436, confirmed | none |
| 50 | gleirscher | Verified published source | Crossref 10.1007/s10664-020-09836-5, confirmed, claim match confirmed | none |
| 51 | blueprints | Verified published source | Crossref 10.1145/2736348, confirmed | none |
| 52 | sel4 | Verified published source | Crossref 10.1145/1629575.1629596, confirmed | none |
| 53 | compcert | Verified published source | Crossref 10.1145/1538788.1538814, confirmed | none |
| 54 | ironfleet | Verified published source | Crossref 10.1145/2815400.2815428, confirmed | none |
| 55 | s3lightweight | Verified published source | Crossref 10.1145/3477132.3483540, confirmed | none |
| 56 | fonseca | Verified published source | Crossref 10.1145/3064176.3064183 + WebSearch for claim, confirmed | Claim match independently confirmed |
| 57 | quickcheck | Verified published source | Crossref 10.1145/351240.351266, confirmed | none |
| 58 | metamorphic18 | Verified published source | Crossref 10.1145/3143561, confirmed | none |
| 59 | segura | Verified published source | Crossref 10.1109/TSE.2016.2532875, confirmed | none |
| 60 | oracle | Verified published source | Crossref 10.1109/TSE.2014.2372785, confirmed | none |
| 61 | chaos | Verified published source | Crossref 10.1109/MS.2016.60, confirmed | none |
| 62 | lineage | Verified published source | Crossref 10.1145/2723372.2723711, confirmed | none |
| 63 | elle | Verified published source | Crossref 10.14778/3430915.3430918, confirmed, claim match confirmed | none |
| 64 | gunawi | Verified published source | Crossref 10.1145/2987550.2987583, confirmed | none |
| 65 | litellm14457 | Verified public issue | GitHub issue #14457 fetched live, open, title/content confirmed | none |
| 66 | opengate1148 | Verified public issue | GitHub issue #1148 fetched live, fixed, 254,347-token figure confirmed verbatim | Highest-stakes entry in the bibliography; fully confirmed |
| 67 | cliproxy2179 | Verified public issue | GitHub issue #2179 fetched live, closed, content confirmed | none |
| 68 | abc | Verified published source | Crossref 10.1145/3241743, confirmed | none |
| 69 | scipy | Verified published source | Crossref 10.1038/s41592-019-0686-2, confirmed | none |
| 70 | statsmodels | Verified published source | Crossref 10.25080/Majora-92bf1922-011, confirmed | none |
| 71 | efron | Verified published source | Crossref 10.1214/aos/1176344552, confirmed | none |
| 72 | arcuri | Verified published source | Crossref 10.1002/stvr.1486, confirmed | Online-first 2012 vs. cited print year 2014 — standard citation convention (citing by volume/issue year), not an error |
| 73 | collberg | Verified published source | Crossref 10.1145/2812803, confirmed | none |
| 74 | feitelson | Verified published source | Crossref 10.1145/2723872.2723875, confirmed | none |
| 75 | fair | Verified published source | Crossref 10.1038/sdata.2016.18, confirmed | none |
| 76 | kalibera | Verified published source | Crossref 10.1145/2464157.2464160, confirmed | none |
| 77 | mytkowicz | Verified published source | Crossref 10.1145/1508244.1508275, confirmed | none |
| 78 | spearman | Verified published source | Crossref 10.2307/1412159, confirmed, claim match confirmed | none |
| 79 | anthropicpricing | Verified technical report (time-variant) | claude.com/pricing fetched live today | Live page today shows different model-generation pricing than the table (Sonnet 5.5/Haiku 5.5 now exist) — expected drift for a dynamic pricing page; paper correctly access-dates the citation and scopes the table as "reproduced for context only" |
| 80 | runeson | Verified published source | Crossref 10.1007/s10664-008-9102-8, confirmed | Online-first 2008 vs. cited print year 2009 — same normal convention as #72 |
| 81 | wohlin | Verified published source | WebSearch confirmed, correct ISBN/year/publisher, 6 actual authors vs. 4 named + "others" — correct | none |

## Notes worth reading

1. **new-api issue #5235 (row 11)**: the issue is actually closed as "not planned" by
   its maintainers — meaning they acknowledged the behavior but chose not to fix it.
   The manuscript's Table 2 doesn't currently state a status for this row at all
   (unlike the other four rows, which say open/fixed/closed/merged). This isn't
   wrong, but naming the actual status would be a strict improvement — "not
   planned" is arguably a *stronger* data point for the paper's argument than
   leaving it unstated, since it means the behavior is known and intentionally
   unaddressed, not just unreported.
2. **Anthropic pricing table (row 79)**: confirmed real and correctly access-dated,
   but worth knowing that the live page has since moved to newer model generations
   with different numbers. The paper's own framing ("reproduced for context only;
   this paper makes no claim about any provider's metering or accounting
   implementation") already covers this appropriately — flagging it here so the
   author isn't surprised if a reviewer checks the link today and sees different
   numbers than the table shows.

## What "verified" means here, precisely

For each entry: title, author list, publication year, and venue were checked against
an authoritative external source (Crossref metadata, the arXiv abstract page, the
live GitHub issue/PR, or the live standards-body page). For entries carrying a
specific factual claim (the three GitHub issues, the five deployed-systems rows,
Spearman/Fonseca's specific findings), the actual claim was checked against the
source's content, not just its existence. For the ~45 citations supporting generic
background or methodology points (formal-methods history, tokenizer papers,
statistics methodology), existence and correct metadata were confirmed; a full
line-by-line re-reading of each paper's complete argument against every nearby
sentence in the manuscript was not performed — that would be a different, much
larger task (re-reviewing the manuscript's entire related-work prose against each
source's full text) than citation-integrity verification.
