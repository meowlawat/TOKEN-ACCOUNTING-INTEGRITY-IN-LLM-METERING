# Change log — TAISAP reframing pass

Every sentence-level change made to `paper/main_taisap.tex` in this pass, grouped by
section. Nothing in this list touches an experimental result, number, configuration
count, or protected claim — verified by grepping every protected number/phrase (see
`qa_report.md`, "Numerical consistency") before and after editing. You asked for your own
voice back on all of this later; treat every "new" cell below as a draft, not final prose.

## Abstract

| Old | New | Reason |
|---|---|---|
| "The contribution is a systematic security analysis of deployed AI-serving infrastructure, **not a new model-level attack**: B0 is a known baseline, and M1/M2 systematize, formalize, and measure mechanisms with prior individual precedent." | "The contribution is a systematic security analysis of deployed AI-serving infrastructure: B0 is a known baseline, and M1/M2 systematize, formalize, and measure mechanisms with prior individual precedent." | Your instruction, Step 1.2: the phrase "not a new model-level attack" reads as arguing against TAISAP's own scope statement ("adversarial attacks on AI and technical vulnerabilities of AI" is explicitly in-scope). Removed; the honest novelty statement (B0 known baseline, M1/M2 systematize prior-precedent mechanisms) is unchanged and now carried in full in the new "Scope and novelty" paragraph in Related Work instead. |

## Introduction (Section 1)

The two opening paragraphs were reordered and lightly rewritten at the seams; no
sentence inside either paragraph's technical content was altered beyond the stated
changes.

| Old | New | Reason |
|---|---|---|
| Para 1 opened: "Metered computational services sell work whose quantity is not known when the work is authorized..." (generic framing first; LLM appears only in para 2) | Para 1 now opens: "LLM inference APIs bill for tokens that are produced at runtime and streamed to the client before the charge is settled, which places the metering and billing path inside the attack surface of the AI-serving system." (your suggested sentence, used close to verbatim), followed by the rest of the former para-2 content | Your instruction, Step 1.1: open on AI-serving security, not generic distributed-state management. The rest of former para 2 (billed-unit-as-runtime-produced, security-critical state) follows this new opening sentence unchanged. |
| Para 1's old closing sentence: "Whether the service can be relied on to charge for what it delivered is therefore a question about distributed state management, not about accounting policy." (the sentence you specifically flagged) | Moved to the new paragraph 2 (see below) and changed to: "...is therefore a question about distributed state management that the LLM case above makes concrete and security-relevant, not merely an accounting-policy question." | Your instruction, Step 1.1: this sentence is what you flagged as reading like the paper's closing argument against AI-specificity. It's now a bridge *from* the AI-security framing, not an independent generic conclusion. |
| (new sentence, start of new para 2) | "This is a structural property of metered computational services generally, not an accident of one implementation, which is why the lifecycle we study is stated over the request lifecycle of a metered service rather than tied to language-model inference." | Added as the transition the brief asked for ("move the general metered-service argument after it, as the reason the problem is structural"). States explicitly *why* the generality claim exists, rather than leaving it to read as a hedge. |
| Former para 1's middle sentences ("A client asks for computation... asynchronously behind both.") | Unchanged in content, now forms the middle of the new paragraph 2 | Reordering only. |

## Contributions list (Section 1)

| Old | New | Reason |
|---|---|---|
| "An accounting-state model of a metered service request (Section~\ref{sec:statemodel}) connecting execution, value delivery, authorization, reservation, debit, reconciliation, and refund..." | "...(Section~\ref{sec:statemodel}), **motivated by token-metered, streamed LLM inference**, connecting execution, value delivery, authorization, reservation, debit, reconciliation, and refund..." | Your instruction, Step 1.4: name the AI-serving context in the contribution bullets. The existing generality claim ("is not specific to language-model inference") is kept verbatim right after — this is additive framing, not a retraction of that claim. |
| "A taxonomy of three experimentally distinguishable failure dimensions (Section~\ref{sec:taxonomy}) -- synchronization, commitment timing, and usage authority -- each localized to a distinct lifecycle element (a shared-state transition, a terminal path, a data-authority boundary), with known, systematized, and defensive boundaries stated explicitly." | Same, with "...a data-authority boundary) **of a token-metered LLM-serving request**, with known..." | Same reason. |

## Background and Related Work (Section 3)

| Change | Location | Reason |
|---|---|---|
| Added one sentence: "The direction of error we study is under-payment by the client; the opposite direction, a platform over-accounting resource usage against its own declared billing model, is also documented and is unrelated to any client action \citep{serverlesscosts}." | After the armbrust/bass sentence in "Prior adversary framings" (§3.1) | Step 2: adds a verified, directly relevant new citation on billing-accounting integrity in metered cloud systems, contrasting the direction of error studied here. |
| Added a new subsection, "Scope and novelty" (§3.7), after "The gap" and before "Accounting State Model" | New subsection, ~230 words | Your instruction, Step 1.2 and Step 2: "Put the precise positioning (what is and is not new, model-level vs system-level) in Related Work or a 'Scope and novelty' paragraph" and "Write one short paragraph that distinguishes this paper from model-level attacks... and states why serving-layer economic integrity is an AI-security problem." States plainly: not a model-level attack; three specific reasons the serving-layer accounting boundary is an AI-security problem (runtime-produced quantity, provider-defined multi-category usage vector, tokenizer nondeterminism); cites three new, independently verified references grounding "LLM serving is attack surface" empirically (`unveilinglandscape`, `grief`, `gift`); restates the honest novelty position (B0 baseline, M1/M2 systematize prior-precedent mechanisms) that was removed from the abstract's closing sentence, so it is not lost, only relocated to where it reads as positioning rather than a concession. |

## Back matter

| Old | New | Reason |
|---|---|---|
| `\section*{CRediT authorship contribution statement}` | `\section*{Author Contributions}` | Your instruction, Step 3: "Remove any leftover traces of previous venues... CRediT blocks that ACM does not use." CRediT is an Elsevier-associated taxonomy label; I could not confirm TAISAP specifically requires or forbids it (the live `dl.acm.org/journal/taisap/author-guidelines` page was blocked — see `verification_log.md`), so I made the minimal, safe change: kept the content (the actual contribution statement, which is accurate and unchanged) and renamed only the Elsevier-branded heading. |

## New bibliography entries (`references_taisap.bib`)

Four new entries, each independently opened and verified (full detail in
`verification_log.md`): `unveilinglandscape` (arXiv:2505.02502), `grief`
(arXiv:2605.11202), `gift` (arXiv:2608.25431), `serverlesscosts` (arXiv:2506.01283).

## Things checked and found to need no change

- **No "dependability" framing risk found.** Grepped the entire manuscript for
  "reliab," "dependab," "fault-toleran," "availability" applied to the system itself
  (as opposed to "Data availability," the standard ACM section heading). Found only the
  section heading. The paper does not describe B0/M1/M2's defenses as reliability or
  fault-tolerance properties anywhere — they are already framed as security properties
  against an adversarial client throughout. No edit needed.
- **Threat model placement**: already its own section (`Threat Model and Security
  Property`, §2) immediately after the Introduction, already in adversarial terms
  (explicit adversary capabilities list, K0/K1/K2 knowledge grading). No edit needed.
- **Limitations / Ethics / Data availability / Competing interests / Funding**: all
  already present and already accurate against the paper's actual content (`Threats to
  Validity` §13 functions as Limitations; `Responsible Disclosure and Ethics` §14 is
  present and already states correctly that all experiments ran against the authors' own
  local testbed, no third-party service was attacked; `Data availability`, `Declaration
  of competing interest`, `Funding` all present and accurate). No edit needed.
