"""Reference defenses for M2 (usage-record authority).

The vulnerable architectures bill on a client-declared (or client-influenceable)
usage record. The defense is to move billing authority to the server. Implemented in
``app/architectures/usage_authority.py``; measured by ``experiments/run_m2.py`` and
``experiments/run_overhead.py``.

Primitive A — server-side authoritative recount (`server_recount`)  [RECOMMENDED]
    The server independently tokenizes the actual input and generated output and bills
    that. The client-declared usage is ignored for billing. Neutralizes every
    manipulation (output/input under-report, category drop, cached reclassification,
    total/subtotal mismatch, rounding shave) — request-ASR 0 across all of them.

Primitive B — reconcile-and-correct (`hybrid_reconcile`)
    Accept the client/upstream usage but recount server-side at request time; if they
    disagree beyond a tolerance, bill the recount and flag the discrepancy. Same
    safety as A, with an explicit detection signal.

Primitive C — honest-upstream authority (`upstream`)
    Bill the provider's usage metadata. Safe in the honest-provider threat model
    because the client cannot alter it; NOT safe against a dishonest provider (that is
    the orthogonal CoIn / Invisible Tokens / Token Inflation problem).

Detection spectrum (why this matters)
    client            -> D0  (blind trust; the leak is invisible to the app)
    client_logged     -> D1  (leak happens live, but a logged recount enables reconciliation)
    client_total      -> D0  (flat total pricing; also exposed to total/subtotal mismatch)
    hybrid_reconcile  -> D3  (detected and corrected at request time)
    server_recount    -> D3  (prevented by construction)

Safety property enforced
    served(r) => net_debit(r) >= authoritative_cost(true_usage(r))

Anti-pattern
    Trusting a client-declared `usage` object, or a client-side tokenizer estimate,
    for billing. A dishonest client under-reports; the leakage efficiency reaches
    ~0.58 for a 90% output under-report and ~0.74 for a total/subtotal mismatch under
    flat total pricing (medium tier). Real proxies already mitigate a related
    "silent zero-debit" via encoding (lightninglabs/aperture #247).

Measured overhead (testbed): server_recount adds ~+0.1 ms mean over the client-trust
path. CAVEAT: the deterministic mock makes the recount nearly free; in production the
recount is a real tokenizer pass whose cost is model/tokenizer-dependent and is NOT
captured by this testbed (see threats-to-validity). See ``results/raw/overhead_*.json``.
"""
