"""M2 — usage-record-authority architectures and client manipulation strategies.

The question: who authoritatively determines the billed usage quantity? Five
architectures span client-authoritative → server-authoritative, giving a
detectability spectrum (D0..D3). The attacker controls only the *client-declared*
usage; the mock provider is honest (our threat model), and the server may or may
not recount.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..accounting.usage import Usage


@dataclass(frozen=True)
class AuthorityArch:
    name: str
    basis: str            # which usage the bill is computed from
    recounts: bool        # does the server compute an authoritative recount?
    corrects: bool        # does it bill the recount when they disagree?
    detection: str        # D0 | D1 | D2 | D3 (best case for a client under-report)
    safe: bool
    description: str


ARCHES: dict[str, AuthorityArch] = {
    "client": AuthorityArch(
        "client", basis="client", recounts=False, corrects=False, detection="D0", safe=False,
        description="Bill the client-declared usage; server never recounts (blind trust) — VULNERABLE, hidden.",
    ),
    "client_logged": AuthorityArch(
        "client_logged", basis="client", recounts=True, corrects=False, detection="D1", safe=False,
        description="Bill client-declared usage but log a server recount for later reconciliation — VULNERABLE live, reconcilable.",
    ),
    "client_total": AuthorityArch(
        "client_total", basis="client", recounts=False, corrects=False, detection="D0", safe=False,
        description="Bill the client-declared TOTAL at a flat rate (collapses categories) — VULNERABLE, and exposed to total/subtotal mismatch.",
    ),
    "upstream": AuthorityArch(
        "upstream", basis="upstream", recounts=False, corrects=False, detection="D3", safe=True,
        description="Bill the honest provider's usage metadata; not client-controllable in this threat model.",
    ),
    "server_recount": AuthorityArch(
        "server_recount", basis="recount", recounts=True, corrects=True, detection="D3", safe=True,
        description="Server independently recounts tokens and bills that (authoritative) — SAFE.",
    ),
    "hybrid_reconcile": AuthorityArch(
        "hybrid_reconcile", basis="client", recounts=True, corrects=True, detection="D3", safe=True,
        description="Accept client usage but reconcile against a server recount at request time and correct — SAFE, with recount cost.",
    ),
}


# --- Client manipulation strategies (true usage -> declared usage) ----------- #
def honest(u: Usage) -> Usage:
    return u.copy()


def under_report_output(u: Usage, frac: float = 0.5) -> Usage:
    m = u.copy()
    m.output_tokens = int(u.output_tokens * frac)
    return m


def under_report_input(u: Usage, frac: float = 0.5) -> Usage:
    m = u.copy()
    m.input_tokens = int(u.input_tokens * frac)
    return m


def drop_reasoning(u: Usage) -> Usage:
    m = u.copy()
    m.reasoning_tokens = 0
    return m


def inflate_cached(u: Usage) -> Usage:
    """Reclassify billed output as (discounted) cached-input to pay less."""
    m = u.copy()
    shift = u.output_tokens // 2
    m.output_tokens = u.output_tokens - shift
    m.cached_input_tokens = u.cached_input_tokens + shift
    return m


def total_mismatch(u: Usage) -> Usage:
    """Declare a low total while subtotals stay high (exploits total-based pricing)."""
    m = u.copy()
    m.declared_total = max(1, u.subtotal_total // 4)
    return m


def rounding_shave(u: Usage) -> Usage:
    """Shave a few tokens off each category (below a naive rounding tolerance)."""
    m = u.copy()
    m.output_tokens = max(0, u.output_tokens - 3)
    m.input_tokens = max(0, u.input_tokens - 1)
    return m


STRATEGIES = {
    "honest": honest,
    "under_report_output_50": lambda u: under_report_output(u, 0.5),
    "under_report_output_90": lambda u: under_report_output(u, 0.1),
    "under_report_input_50": lambda u: under_report_input(u, 0.5),
    "drop_reasoning": drop_reasoning,
    "inflate_cached": inflate_cached,
    "total_mismatch": total_mismatch,
    "rounding_shave": rounding_shave,
}
