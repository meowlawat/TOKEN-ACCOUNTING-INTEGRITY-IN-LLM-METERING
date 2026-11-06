# Independent formal-model review

Executed 2026-11-06 from commit `6114e20` plus the preregistered runner. TLC 2.19
(`formal/tools/tla2tools.jar`) ran with one worker through the JDK bundled by `jdk4py`.
Specification, configuration, JAR, command, exit, and state-count evidence is retained in
`formal_runs/`.

## Primary model rerun

Command: `python formal/check.py`

Result: 10 configurations x 4 separately checked invariants = 40 outcomes; 40/40
matched the expectations declared before execution; 0 disagreements; 27,526 summed
distinct states. Unsafe configurations produced the expected counterexamples. The run
rewrote the repository's generated result only in wall-clock seconds, so that historical
file was restored byte-for-byte and the fresh result was preserved as
`formal_runs/primary_model_check_results.json` instead.

This independently reproduces `C-TLC-PRIMARY`. It does not prove the FastAPI/PostgreSQL
implementation, arbitrary request counts, arbitrary prices, weak-consistency behavior, or
the asynchronous family.

## Async model and preregistered extension

Command: `python audit/taisap_upgrade/scripts/run_async_formal_extension.py --repo .
--output audit/taisap_upgrade/formal_runs`

The first attempt was an execution failure: all cells exited 255 because TLC's config
resolver could not open a config outside the spec directory when the spec itself was
passed as an absolute path. A minimal reproduction showed the same config worked when the
module was named relative to the `formal/` working directory. The runner now passes
`AsyncSettlementTOCTOU.tla` relative to that directory, clears stale generated logs, and
records failed runs rather than interpreting them as safe states.

The corrected run checked 12 configurations x 3 invariants = 36 outcomes at `(N,k)` =
`(3,1), (4,1), (4,2), (5,2), (6,2), (6,3)` in vulnerable and atomic modes. Result:

- 36/36 matched preregistered expectations; 0 errors and 0 unexpected cells;
- all atomic cells held AccountingIntegrity, Solvency, and LedgerConservation;
- all vulnerable cells held per-request AccountingIntegrity and LedgerConservation but
  violated Solvency;
- aggregate exploration across the 36 independent runs generated 480,565 states and
  found 116,920 distinct states (sums include repeated state spaces because each invariant
  is intentionally run separately);
- the vulnerable `(6,2)` isolated holding runs each reproduced 91,921 generated and
  22,521 distinct states, exactly matching the manuscript; its Solvency run produced the
  expected counterexample.

This reproduces `C-TLC-ASYNC` and extends it to four additional `(N,k)` points. It supports
the generalized coupling condition only within this finite untimed causal model. It is not
an unbounded theorem, a timed threshold result, a database/network model, or an
implementation refinement proof.

## Necessary, sufficient, and conditional wording

- **Model-sufficient:** In `TokenAccounting.tla`, the modeled conjunction of reservation,
  abort-safe finalization, and server authority is sufficient for the four checked
  invariants at the bounded configurations.
- **Model-sufficient:** In `AsyncSettlementTOCTOU.tla`, atomic admission/commitment is
  sufficient for the three checked invariants at the six preregistered points.
- **Counterexample-supported necessity within the modeled architecture:** Removing the
  relevant primitive exposes a trace violating the named invariant. This is not logical
  necessity across every possible implementation or defense.
- **Conditional empirical prediction:** Deferred settlement can over-serve when multiple
  admissions observe funds before their commitments land. Millisecond thresholds depend
  on achieved arrival/settlement timing and are outside the TLA+ state model.

No specification source or historical formal evidence was changed.

