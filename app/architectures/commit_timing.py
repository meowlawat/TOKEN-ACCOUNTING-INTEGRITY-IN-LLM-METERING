"""M1 — metering-commit-timing architectures.

The question: what happens when streamed inference is delivered before billing is
irrevocably committed? Four architectures span the design space; two are safe, two
leak under a client that aborts mid-stream.

Each architecture is a small descriptor consumed by the `/m1/stream` handler:

  reserve_before : take an atomic reserve of the full estimate before streaming
  on_complete    : how to settle when the stream finishes normally
  on_disconnect  : how to settle when the client disconnects mid-stream
  safe           : whether it satisfies the safety invariant under abort
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommitArch:
    name: str
    reserve_before: bool
    on_complete: str      # "keep_reserve" | "reconcile" | "debit_actual"
    on_disconnect: str    # "keep_reserve" | "reconcile_delivered" | "no_debit" | "refund_all"
    safe: bool
    description: str


ARCHES: dict[str, CommitArch] = {
    # A. Debit the full estimate up front. Aborting cannot reduce the charge.
    "pre_debit": CommitArch(
        "pre_debit", reserve_before=True, on_complete="keep_reserve",
        on_disconnect="keep_reserve", safe=True,
        description="Debit full estimate before inference; abort keeps the charge (may overcharge).",
    ),
    # C. Reserve, stream, then reconcile to what was actually delivered/generated.
    "reserve_reconcile": CommitArch(
        "reserve_reconcile", reserve_before=True, on_complete="reconcile",
        on_disconnect="reconcile_delivered", safe=True,
        description="Reserve estimate; on completion or abort, settle to delivered tokens and refund the rest.",
    ),
    # B. No reserve; only debit after the stream completes. Abort => no debit.
    "post_completion": CommitArch(
        "post_completion", reserve_before=False, on_complete="debit_actual",
        on_disconnect="no_debit", safe=False,
        description="Debit only after full completion; a mid-stream abort is never billed (VULNERABLE).",
    ),
    # D. Reserve, but refund the whole reserve if the final usage block is missing
    #    after disconnect (the new-api #5235 pattern).
    "reserve_refund_on_abort": CommitArch(
        "reserve_refund_on_abort", reserve_before=True, on_complete="reconcile",
        on_disconnect="refund_all", safe=False,
        description="Reserve estimate; on abort with missing final usage, refund the entire reserve (VULNERABLE; new-api #5235).",
    ),
    # ABLATION CELL: abort-inclusive finalization WITHOUT a reservation. Isolates
    # which primitive actually closes M1. Accounting-safe (delivered value is always
    # billed) but provides NO funds guarantee: the balance can go negative because
    # nothing was held before serving.
    "no_reserve_settle": CommitArch(
        "no_reserve_settle", reserve_before=False, on_complete="debit_actual",
        on_disconnect="debit_delivered", safe=True,
        description="No reservation; settle to delivered tokens on BOTH completion and abort "
                    "(ablation: finalization without reservation -- integrity holds, funds "
                    "guarantee does not).",
    ),
}

VULNERABLE = [a for a, v in ARCHES.items() if not v.safe]
SAFE = [a for a, v in ARCHES.items() if v.safe]
