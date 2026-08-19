"""One-shot patch: add MODEL-CHECKED evidence class and the journal-upgrade claims.

Kept as a file rather than an inline heredoc because the claim text contains quotes and
arrows that shells mangle. Idempotent.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "experiments" / "build_claim_matrix.py"
s = p.read_text(encoding="utf-8")
before = s

s = s.replace(
    "# kind: DIRECTLY MEASURED | ANALYTICALLY DERIVED | INFERRED | LITERATURE-SUPPORTED\n"
    "#       | HYPOTHESIS | WITHDRAWN | UNSUPPORTED",
    "# kind: MODEL-CHECKED | DIRECTLY MEASURED | ANALYTICALLY DERIVED | INFERRED\n"
    "#       | LITERATURE-SUPPORTED | HYPOTHESIS | WITHDRAWN | UNSUPPORTED\n"
    "#\n"
    "# MODEL-CHECKED: TLC exhaustively explored the reachable state space of\n"
    "# formal/TokenAccounting.tla under a stated configuration. Machine-checked, and\n"
    "# bounded by the model -- see paper/scope_of_formal_claims.md. Never write 'proved'\n"
    "# for anything weaker.", 1)

s = s.replace('    "DIRECTLY MEASURED": "high",\n    "ANALYTICALLY DERIVED"',
              '    "MODEL-CHECKED": "high (exhaustive within the model)",\n'
              '    "DIRECTLY MEASURED": "high",\n    "ANALYTICALLY DERIVED"', 1)

s = s.replace('    "DIRECTLY MEASURED": "single-host testbed; mock generator unless stated",\n'
              '    "ANALYTICALLY DERIVED"',
              '    "MODEL-CHECKED": "bounded model (2-3 requests, unit pricing, strong '
              'consistency); no refinement proof to the implementation",\n'
              '    "DIRECTLY MEASURED": "single-host testbed; mock generator unless stated",\n'
              '    "ANALYTICALLY DERIVED"', 1)

NEW_CLAIMS = '''    # ---- formal verification ----------------------------------------------
    dict(id="C40", section="Formal",
         claim="An atomic guarded decrement preserves ledger conservation on every "
               "reachable state; the non-atomic read/check/blind-write path violates it "
               "(21-step counterexample) while every individual record stays consistent.",
         kind="MODEL-CHECKED", metric="TLC exhaustive state-space exploration",
         source="formal/TokenAccounting.tla + formal/check.py",
         result_file="results/formal/model_check_results.json"),
    dict(id="C41", section="Formal",
         claim="Reservation and abort-safe finalization are orthogonal: reservation alone "
               "gives solvency but violates accounting integrity; abort-safe finalization "
               "alone gives integrity but violates solvency; only the conjunction gives both.",
         kind="MODEL-CHECKED", metric="4 M1 configurations x 4 invariants",
         source="formal/check.py", result_file="results/tables/table_formal_matrix.md",
         verify=("file_contains", ("results/tables/table_formal_matrix.md",
                                   "m1 no reserve settle"))),
    dict(id="C42", section="Formal",
         claim="Server-authoritative billing preserves all four invariants against the same "
               "lying client that breaks the client-authoritative architecture; under-billing "
               "with a reservation also violates the refund bound.",
         kind="MODEL-CHECKED", metric="m2_client vs m2_server_recount",
         source="formal/check.py", result_file="results/formal/model_check_results.json"),
    dict(id="C43", section="Formal",
         claim="All 40 model-checking outcomes (10 configurations x 4 invariants, 28,363 "
               "distinct states) matched expectations declared before the run; 0 disagreements.",
         kind="MODEL-CHECKED", metric="pre-declared expectation matrix",
         source="formal/check.py", result_file="results/formal/model_check_results.json"),
    # ---- real serving stack ------------------------------------------------
    dict(id="C44", section="External validity",
         claim="Against a third-party serving stack (llama.cpp llama-server, "
               "SmolLM2-135M-Instruct) the architectural conclusions are unchanged: 12 M1 and "
               "48 M2 cells produced 0 safety disagreements. Vulnerable architectures still "
               "leak on abort; every server-authoritative architecture still leaks exactly "
               "zero across all 8 manipulations.",
         kind="DIRECTLY MEASURED", metric="leak sign per cell vs mock corpus",
         source="experiments/run_real_stack.py",
         result_file="results/processed/real_stack.summary.json"),
    dict(id="C45", section="External validity",
         claim="Attack EFFECTIVENESS is generator-dependent even though the architectural "
               "conclusion is not: 5 of 48 M2 cells flipped, because SmolLM2 emits no "
               "reasoning tokens (drop_reasoning becomes inert) and flat-total pricing "
               "over-charges on this token mix.",
         kind="DIRECTLY MEASURED", metric="mock vs real leakage efficiency per cell",
         source="experiments/summarize_real_stack.py",
         result_file="results/tables/table_real_stack_m2.md"),
    dict(id="C46", section="External validity",
         claim="On a real serving stack the authoritative cost of a byte-identical request is "
               "not reproducible: the reported prefix-cache split changes with server cache "
               "state, moving the honest charge by 22-32 percent (3/3 prompts). The client "
               "cannot verify its own bill even in principle.",
         kind="DIRECTLY MEASURED", metric="honest cost across repeated identical calls",
         source="experiments/cached_split_probe.py",
         result_file="results/tables/table_cached_split.md"),
    # ---- asynchronous accounting -------------------------------------------
    dict(id="C47", section="Async accounting",
         claim="With an honest event pipeline, asynchronous accounting is late rather than "
               "lossy: the mean exposure window tracks the configured reconciliation delay "
               "and the leak reconciles to exactly zero.",
         kind="DIRECTLY MEASURED", metric="exposure window + post-reconciliation leak",
         source="experiments/run_async_accounting.py",
         result_file="results/tables/table_async_m1.md"),
    dict(id="C48", section="Async accounting",
         claim="Decoupling settlement converts B0's concurrency race into an architectural "
               "window: with strictly sequential arrivals 20 ms apart, over-serving appears "
               "once the reconciliation delay reaches 100 ms and reaches 4 requests over a "
               "2-request budget at 500 ms, driving the balance negative. An atomic decrement "
               "does not help when it lands after the next authorization.",
         kind="DIRECTLY MEASURED", metric="over-served count vs reconciliation delay",
         source="experiments/run_async_accounting.py",
         result_file="results/tables/table_async_b0.md"),
    dict(id="C49", section="Async accounting",
         claim="A lost usage event leaks permanently while a duplicated one is suppressed "
               "idempotently; whether a straggler looks lost or merely late is a property of "
               "the observation horizon, not of the architecture.",
         kind="DIRECTLY MEASURED", metric="leak by injected pipeline fault",
         source="experiments/run_async_accounting.py",
         result_file="results/tables/table_async_m1.md"),
    dict(id="C50", section="Async accounting",
         claim="M2 leakage efficiency is identical at every reconciliation delay, confirming "
               "the analytically predicted independence of usage authority from settlement "
               "timing.",
         kind="ANALYTICALLY DERIVED", metric="leakage efficiency vs delay (confirmatory)",
         source="experiments/run_async_accounting.py",
         result_file="results/processed/async_accounting.summary.json"),
    # ---- explicitly scoped non-claims -------------------------------------
'''

anchor = "    # ---- explicitly scoped non-claims -------------------------------------\n"
if "C40" not in s:
    s = s.replace(anchor, NEW_CLAIMS, 1)

s = s.replace('"**ANALYTICALLY DERIVED** / **HYPOTHESIS** / **WITHDRAWN** / **UNSUPPORTED**.',
              '"**MODEL-CHECKED** / **ANALYTICALLY DERIVED** / **HYPOTHESIS** / '
              '**WITHDRAWN** / **UNSUPPORTED**.', 1)

p.write_text(s, encoding="utf-8")
print("patched" if s != before else "no change (already applied)")
