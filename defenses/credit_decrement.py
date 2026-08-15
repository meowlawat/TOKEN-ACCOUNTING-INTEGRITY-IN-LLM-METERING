"""Reference defense for flaw class 6: atomic compare-and-decrement.

The enforcement primitive is a single SQL statement that both checks and debits
under a row lock, executed and committed *before* the metered work begins::

    UPDATE credits SET balance = balance - :cost
    WHERE account_id = :id AND balance >= :cost
    RETURNING balance

Because the compare and the decrement are one atomic, serialized operation, no two
concurrent handlers can both pass the check on the same funds. Exactly the
affordable number of requests succeed; the remainder receive HTTP 402.

Implementation: ``app.metering.debit.reserve_hardened`` (reserve), with
``adjust_hardened`` reconciling the estimate against the recounted actual cost and
``refund_hardened`` returning funds if a reserved response fails to complete.

Safety property enforced
------------------------
    No completed response without a committed, non-refunded debit.

Equivalently: for every served completion there exists exactly one committed,
non-refunded ``usage_records`` row, and the sum of live-balance decrements equals
the sum of those recorded costs (no lost updates, no over-serving).

Overhead
--------
The primitive adds no extra round trips versus the vulnerable path (it replaces a
SELECT + UPDATE with one UPDATE...RETURNING). Its cost is contention on the credit
row's lock, which is measured directly by ``experiments/run_class6.py`` (latency
p50/p95/p99 and served-throughput) under the hardened posture.
"""
