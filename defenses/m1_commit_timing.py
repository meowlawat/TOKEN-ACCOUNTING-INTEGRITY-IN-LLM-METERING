"""Reference defenses for M1 (metering-commit timing).

The vulnerable architectures commit the charge *after* — or refund it *on* — a
client-controllable event (stream completion / disconnect), opening an abort window.
Two enforcement primitives close it; both are implemented in
``app/architectures/commit_timing.py`` and measured by ``experiments/run_m1.py`` and
``experiments/run_overhead.py``.

Primitive A — pre-authorization (`pre_debit`)
    Atomically debit the full estimate before any token is generated. A mid-stream
    abort cannot reduce the charge. Cost: may overcharge when the actual output is
    shorter than the estimate (needs a separate refund policy to be fair to honest
    users), so it trades integrity for potential over-billing.

Primitive B — reserve-then-reconcile (`reserve_reconcile`)  [RECOMMENDED]
    Atomically reserve the full estimate before streaming; on completion OR on
    disconnect, settle to the tokens actually delivered and refund the unused
    remainder. The settlement runs in a cancellation-shielded path so it executes
    even when the client disconnects. This bills exactly for delivered value and
    satisfies the safety invariant at every abort point.

Safety property enforced
    served(r) => committed_debit(r) - refund(r) >= authoritative_cost(delivered(r))

i.e. no delivered inference without a committed, non-refunded debit covering it.

Anti-pattern (do NOT do this) — `reserve_refund_on_abort`
    Reserving and then refunding the *entire* reserve when the final usage block is
    missing after a disconnect (the deployed new-api #5235 behaviour) is equivalent
    to no charge at all under abort — the worst case. Reconcile to delivered instead.

Measured overhead (testbed, medium tier, full-completion latency): reserve_reconcile
adds ~+9.8 ms mean over post_completion (two extra atomic DB writes: the reserve and
the reconcile refund), i.e. a few percent on top of streaming latency. See
``results/raw/overhead_*.json``.
"""
