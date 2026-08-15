"""Server-side enforcement primitives, one per flaw class.

The class-6 reference defense (atomic compare-and-decrement) lives with the
metering code it replaces, in ``app.metering.debit.reserve_hardened``. See
``defenses.credit_decrement`` for the write-up of the primitive and the safety
property it enforces.
"""
