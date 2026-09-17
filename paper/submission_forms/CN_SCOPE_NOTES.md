# Computer Networks — scope notes

Verified against official/authoritative sources at the time of writing (September 2026).
Two Elsevier author-facing pages (`elsevier.com` and `sciencedirect.com` guide-for-authors
URLs) returned HTTP 403 to automated fetching; the facts below were cross-checked through
search results that quote or summarize those same official pages, and are reported as
**verified via search-indexed official content**, not assumed from a generic template.
Where a figure could not be confirmed this way, it is marked accordingly.

---

## 1. What Computer Networks actually says it covers

**Aims (as stated by the journal):** to explore methodologies, protocols, algorithms, and
applications that enhance the design, performance, and security of computer networks.
Audience: researchers, managers, operators, designers and implementors of networks.

**Topic areas listed by the journal**, in full:

| Area | Named sub-topics |
|---|---|
| Communication Network Architectures | LAN/MAN/WAN, wired/wireless/mobile/cellular/sensor/optical/IP/ATM, switching, integration of networking paradigms |
| Communication Network Protocols | (protocol design/standardization/adoption) |
| Network Services and Applications | — |
| **Network Security and Privacy** | security protocols, authentication, denial of service, anonymity, smartcards, intrusion detection, key management, viruses and other malicious codes, information flow, **data integrity**, mobile code and agent security |
| **Network Operation and Management** | **network pricing**, network system software, quality of service, signaling protocols, mobility management, power management, network planning, network dimensioning, network reliability, network performance measurements, network modeling and analysis, overall system management |

**Guide-for-authors mechanics:** abstract ≤ 250 words; **keywords ≤ 6**; no rigid section
structure mandated (Elsevier "Your Paper Your Way" applies at initial submission — any
consistent reference style is accepted pre-review); hybrid journal — subscription
publication carries no fee, optional gold OA APC ≈ €3,090 (geo-priced, waivable under
Elsevier's standard agreements).

**Why this matters for the two limits actually enforced in this conversion:** the
manuscript's abstract was already within limit (245–248 words across versions); the
keyword list was not — JISA allowed up to 7, this manuscript carried 7, and CN caps at 6.
One keyword had to go. See §3.

---

## 2. Genuine fit, not a forced one

Two of CN's named sub-topics are a direct, unforced match to this manuscript's actual
content — not a reframing invented to fit the venue:

- **"network pricing"** (Network Operation and Management) is, in this paper's own
  vocabulary, exactly what B0/M1/M2 are about: the accounting and settlement path that
  determines what a network-accessible service charges a client.
- **"data integrity"** (Network Security and Privacy) is, in this paper's own vocabulary,
  the property `V(r) ≤ N(r)` — the accounting-integrity invariant the whole taxonomy is
  organized around.

A third point of genuine (not invented) relevance: **Section 10.1 of the manuscript
("Execution topologies")** already reports real, previously-run experiments across three
network-relevant deployment shapes — a single worker as control, four workers behind an
nginx reverse proxy sharing one PostgreSQL instance and one Redis instance, and an nginx
load balancer over two independent gateway containers, with 96 accounting cells validated
for agreement against the control. Section 10.3 ("A real serving stack") already reports
real server-sent-event streaming against llama.cpp serving code the authors did not write.
None of this had to be added for the CN conversion — it already existed in the frozen
science and simply had not been foregrounded for a networking-journal reader.

**What is genuinely NOT there, and was not invented to fill the gap:** there is no
new networking protocol, no cryptographic construction, and no wide-area or
physically-distributed network experiment. All topologies in Section 10.1 ran on one host
under Docker Compose. The cover letter and the manuscript both say so explicitly (see
`cover_letter_cn.txt`, "ON LIMITATIONS").

---

## 3. Section-by-section mapping

| CN scope point | Manuscript section(s) | Nature of the fit |
|---|---|---|
| Network Security and Privacy — data integrity, information flow | §2 Threat Model and Security Property; §4 Accounting State Model | The paper's central object, `V(r) ≤ N(r)`, is a data-integrity property of a networked service's accounting state. |
| Network Operation and Management — network pricing, overall system management | §11 Economic and Pricing Analysis; §9 Defenses and Sufficiency Conditions | Billing-function analysis and defense cost accounting are exactly "network pricing" + "system management" in CN's own terms. |
| Network Security and Privacy — authentication, intrusion-adjacent misuse | §3 Background and Related Work (Table 1, adversary quadrant) | Positions the threat model (authenticated-but-dishonest client) against the existing provider/third-party/intermediary literature. |
| Communication Network Architectures / protocols | §7 Formal Verification; §5 Architectural Taxonomy | The TLA+ specification models the request as a state machine / protocol over the client-service boundary; CN readers will recognize this as protocol/state-machine verification, which is why "protocol verification" replaces "model checking" as a keyword (§4 below). |
| Network Operation and Management — performance measurements | §12 (tokenizer/recount overhead), §9.2 (defense cost) | Latency/throughput measurement of the defense mechanisms, at three levels (tokenizer, gateway, real model). |
| Distributed/multi-node network service behaviour | §10 Cross-Architecture and Asynchronous Validation | Real evidence (§2 above), not invented for this conversion. |

---

## 4. What was changed, and why (summary — full list in `CN_VERSION_CHANGELOG.md`)

1. `\journal{}` → Computer Networks.
2. **Keywords 7 → 6.** CN's cap is 6, not 7. Dropped `streaming inference` (the content
   survives in the body, §10.3, in more detail than the keyword conveyed); replaced
   `model checking` with `protocol verification`, which names the identical TLA+/TLC work
   in the vocabulary CN's own scope statement uses ("Communication Network Protocols").
3. **Introduction, opening sentence** and **one new sentence before the contributions
   list**: both now name the system explicitly as a network-accessible LLM serving system
   reached over a metered API. No claim changed; this states plainly what was already true
   of the deployment being studied.
4. **Security-boundary paragraph (end of §5, Architectural Taxonomy)**: reframed from "AI
   serving system" language (written for a security-application journal) to
   "network-accessible LLM serving system" language, with an explicit sentence tying the
   integrity property to the pricing/quota/system-management surface CN's own scope names.
   The closing disclaimer — that the paper does not study the model's behaviour, robustness
   or output safety — is preserved verbatim in substance.

None of these changes touch a table, figure, equation, numerical result, or citation.

---

## 5. Genuine scope risks — stated, not hidden

- **CN is a networking-systems journal first; this is a security/accounting paper whose
  subject happens to be a network-accessible service.** A CN reviewer may reasonably ask
  why this isn't a security-venue paper. The honest answer, given in the cover letter, is
  that the two nearer security venues (Computers & Security, JISA) did not accept it —
  C&S on a stated AI/ML scope exclusion, JISA for reasons this repository does not have a
  verified record of (see the note below). CN's own "network pricing" and "data integrity"
  scope lines are the basis for trying here next, not a rationalization after the fact.
- **No wide-area or multi-host network experiment exists.** All topology variation in
  §10.1 is single-host Docker Compose. If a CN reviewer expects genuine network-layer
  experimentation (latency over a real WAN, packet loss, jitter), this manuscript does not
  provide it, and the cover letter says so rather than letting the reviewer discover it.
- **The formal model is a request-lifecycle state machine, not a network protocol in the
  IETF sense.** It does not specify wire format, framing, or a transport-layer protocol.
  It models the *authorization/accounting* states a request passes through, which is a
  narrower claim than "protocol verification" might suggest to a networking-protocols
  specialist. The keyword and framing changes above try to signal this accurately rather
  than oversell it.
- **Reference style.** The manuscript currently uses `elsarticle` with `authoryear`
  (natbib) citations, unchanged from the JISA version. Elsevier's "Your Paper Your Way"
  permits any consistent style at initial submission, so this is not a blocker, but CN's
  house style at production may differ; this is a post-acceptance formatting matter, not a
  pre-submission blocker.

## 6. Unverified item — flagged rather than invented

The task briefing that produced this package states that the manuscript was "subsequently
rejected by Journal of Information Security and Applications." **This repository holds no
record of a JISA decision** — no manuscript number, no decision date, no decision-maker,
no stated reason. `paper/FINAL_SUBMISSION_STATUS.md` (last updated before this pass) still
records JISA as "prepared, not submitted." The cover letter therefore states only that the
manuscript "is no longer under consideration" at JISA — true under the reported outcome
either way — and does **not** assert a rejection reason, a peer-review outcome, or any
other specific about that decision, because none has been verified. If you can supply the
same level of detail you gave for the C&S decision (manuscript number, date, decision-maker,
exact stated reason, whether peer review occurred), I will fold it into the cover letter
and this document with the same accuracy standard applied to C&S.
