# Version changelog — main_cose.tex → main_jisa.tex → main_cn.tex

Three separate, independently-compiling manuscript files exist because three journals
have been targeted in sequence. **None of the three files has been edited after the fact
to match this changelog — this changelog was written by diffing them.** All three remain
on disk unmodified:

```
paper/main_cose.tex / .pdf   submitted to Computers & Security, COSE-D-26-05174, desk/scope rejected
paper/main_jisa.tex / .pdf   prepared for Journal of Information Security and Applications
paper/main_cn.tex   / .pdf   prepared for Computer Networks (this pass)
```

Verified this pass, both by `git diff --stat` against the last commit (empty for both
older files) and by re-reading them: `main_cose.tex` and `main_jisa.tex` were not touched
while producing `main_cn.tex`.

---

## A. Scientific content — unchanged across all three files

Confirmed by direct inspection and by a pagination-normalised text diff of the compiled
PDFs (JISA→CN similarity ratio 0.9155; every non-equal region is either an edit listed in
section B below, or a delete/insert pair of byte-identical text that moved position
because the added framing sentences pushed later content to a different page).

- B0/M1/M2 accounting taxonomy and the definitions of each dimension
- The integrity property `V(r) ≤ N(r)` and its formal statement
- TLA+/TLC formal verification: 10 configurations × 4 invariants = 40 runs, 27,526
  distinct states, 0 disagreements
- `regression_class6` 19/19, `regression_m` 16/16, `metamorphic` 22/22
- `recompute_all` 0 discrepancies, independent M2 validation 0 mismatches
- Controlled M2 leakage 58.3%; real-serving-stack M2 leakage 69.0%
- Server-authoritative billing removing the observed M2 leakage
- The asynchronous/sequential-arrival over-serving result and its conditional framing
- The orthogonality of reservation and abort-safe finalization (M1)
- Cross-architecture validation (three execution topologies, three accounting backends,
  96 + 17 comparison cells respectively)
- llama.cpp / SmolLM2-135M-Instruct real-serving validation
- Tokenizer overhead / economic analysis (three-level measurement)
- The withdrawn-detectability disclosure
- All six figures, all six tables, all equations, all 26 bibliography entries
- The explicit statement that no new attack primitive is claimed

No dataset, script, or measured value was regenerated or altered to produce either the
JISA or the CN version.

---

## B. Venue-specific framing changes

### COSE → JISA (already committed; summarised here for completeness, not redone)

1. `\journal{}`: Computers & Security → Journal of Information Security and Applications.
2. Keywords: 9 → 7 (JISA's guide for authors allows 1–7; C&S had no such cap).
3. Security-boundary paragraph (end of the taxonomy section): the C&S wording argued the
   paper was *not* an AI paper ("The security subject throughout this paper is the
   metering and accounting infrastructure around inference, not the behavior, robustness,
   or output safety of the language model itself"). The JISA wording instead states
   positively what the boundary is, without the defensive framing.
4. Data availability: switched from citing a specific Zenodo version DOI to the concept
   DOI `10.5281/zenodo.22085827`, which resolves to the latest archived version regardless
   of which artifact version is current.

### JISA → CN (this pass)

| # | Change | Exact text location | Why |
|---|---|---|---|
| 1 | `\journal{}`: JISA → Computer Networks | line 40 | Venue change |
| 2 | Keywords: 7 → 6. Dropped `streaming inference`; replaced `model checking` with `protocol verification` | `\begin{keyword}` block | CN's guide for authors caps keywords at 6, not 7. `protocol verification` names the same TLA+/TLC work in CN's own vocabulary (the journal lists "Communication Network Protocols" as a topic area). `streaming inference` was dropped rather than another term because its content is covered in more depth in the body (§10.3, real SSE streaming against llama.cpp) than a single keyword conveyed. |
| 3 | Introduction, opening sentence: "The billed unit of an LLM API" → "The billed unit of a network-accessible LLM API ... delivered to a remote client over that network boundary" | start of §1 | Names the network-accessible setting explicitly, for a networking-journal reader, without adding a claim — LLM APIs are in fact accessed over a network. |
| 4 | One new sentence inserted before the contributions list: "The setting throughout is a network-accessible LLM serving system reached over a metered API: a remote client issues a request, the service streams a response across the network while accounting is still open, and a security-relevant decision — what to charge — is made from state produced on that path." | before `\textit{Contributions.}` | Makes the CN-relevant framing explicit at the exact point a reviewer reads the contribution list, without altering any of the five enumerated contribution items themselves. |
| 5 | Security-boundary paragraph (end of §5, Architectural Taxonomy): reworded from "AI serving system" framing (written for JISA, an information-security-applications venue) to "network-accessible LLM serving system" framing, with one new sentence tying the integrity property to the pricing/quota-enforcement/system-management surface CN's own scope statement names | end of §5 | Task 6: use technically accurate language for *why* token metering at a network-accessible service boundary is a security/integrity problem relevant to CN, rather than reusing language written to argue against a different journal's scope objection. |

Full evidence and the CN scope mapping are in
`paper/submission_forms/CN_SCOPE_NOTES.md`.

**Not changed for CN, on purpose:**

- Title — evaluated and kept. It already names the security property, the LLM context,
  and the threat direction; a networking-specific title was not pursued because no
  concrete discoverability or scope-fit gain outweighed the churn (see §D below).
- The five enumerated contributions themselves — only the sentence introducing them
  changed, not their content or ordering.
- Data availability — already cites the concept DOI from the JISA version; unchanged.
- Every declaration (Acknowledgements, CRediT, Competing interest, Funding).

---

## C. Metadata changes

None beyond the `\journal{}` line and the keyword list (both listed in §B). Author name,
ORCID, both affiliations, both email addresses, and the corresponding-author designation
are byte-identical across all three files.

---

## D. Title — evaluated, not changed

Task 7 asked for a first-preservation note and an exact reason if a change were proposed.
No change is proposed. Reasoning:

- The current title, *"Token-Accounting Integrity in LLM Metering: A Systematic Study of
  Client-Side Under-Payment,"* already communicates the security property (integrity), the
  system context (LLM metering), and the threat direction (client-side under-payment).
- A CN-flavoured alternative would need to work in "network-accessible" or "service"
  without lengthening the title past what Elsevier titles typically run, and no such
  rewording was found that added discoverability rather than just restating the abstract's
  opening clause.
- Changing a title across a third venue conversion, having already kept it through the
  first two, was judged higher-risk (inconsistent self-citation across preprint/version
  history) than the marginal fit gain.

---

## E. Cover-letter changes

`paper/submission_forms/cover_letter_cn.txt` is a new file, not an edit of
`cover_letter_jisa.txt`, but closely modeled on it. Differences:

- Salutation and journal name updated to Computer Networks; article type stated as Full
  Length Article (JISA's own accepted-type language reused, since CN's guide for authors
  does not name a different label for the equivalent type).
- "WHAT THE PAPER IS ABOUT" reframed around the network-accessible-service framing (same
  content as the manuscript's own reframing in §B).
- "METHODS" paragraph expanded to name the three execution topologies explicitly (single
  worker; four workers behind nginx; nginx load balancer over two gateways) and to name
  llama.cpp's real server-sent-event streaming — this is a *disclosure* addition, not a new
  claim: both facts already existed in the manuscript body (§10.1, §10.3) and are now
  surfaced in the letter because a CN editor will look for exactly this kind of evidence.
- "ON LIMITATIONS" gained one sentence stating plainly that all topology variation ran on
  a single host under Docker Compose and that no wide-area or physically distributed
  network claim is made — added because CN readers are the audience most likely to assume
  otherwise if it is left unsaid.
- "PRIOR SUBMISSION" now mentions both prior venues. The Computers & Security paragraph is
  unchanged from the JISA letter (verified facts: COSE-D-26-05174, desk/scope rejection, no
  peer review). One sentence was added stating the manuscript "was subsequently submitted
  to the Journal of Information Security and Applications and is no longer under
  consideration there." **This is deliberately non-specific**: the repository contains no
  verified record of a JISA decision (no manuscript number, decision date, decision-maker,
  or stated reason), so none is asserted. See `CN_SCOPE_NOTES.md` §6 for the flagged gap.
- Signature block: unchanged.

---

## F. Formatting changes

None beyond what B lists. Document class (`elsarticle`, `preprint,3p,authoryear,12pt`),
citation style (natbib author-year), figure/table numbering, and section structure are
identical to the JISA version. `graphicspath` is unchanged — `main_cn.tex` draws from the
same `figures_cose/` directory as the other two versions; no figure was regenerated,
recropped, or renumbered.

---

## Summary

```
Files compared:        main_cose.tex, main_jisa.tex, main_cn.tex
Scientific content:    IDENTICAL across all three (verified: text diff + value re-check)
COSE -> JISA changes:  4  (journal, keywords 9->7, boundary paragraph, DOI form)
JISA -> CN changes:    5  (journal, keywords 7->6, opening sentence, one new sentence,
                            boundary paragraph)
Title:                 unchanged across all three
Declarations:          unchanged across all three
```
