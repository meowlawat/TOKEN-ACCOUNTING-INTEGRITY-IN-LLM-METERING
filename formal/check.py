"""Run the TLC model checker over every architecture configuration.

This is real explicit-state model checking, not a hand argument: TLC exhaustively
explores the reachable state space of `TokenAccounting.tla` under each configuration and
either proves an invariant holds on every reachable state, or returns a shortest
counterexample trace.

Each invariant is checked in a SEPARATE TLC run. TLC stops at the first invariant it
finds violated, so checking them together would hide the fact that (for example) an M2
architecture breaks both accounting integrity and the refund bound. The result is a full
configuration x invariant matrix rather than one verdict per configuration.

Expected outcomes are declared here *in advance* (see EXPECTED) and compared against what
TLC actually reports. A configuration whose real outcome differs from its expectation is
a FAILURE of this script and exits non-zero -- it is not quietly re-labelled. That is the
same discipline the empirical side uses, and it is what stops the formal model from being
written to agree with the paper. It has already earned its keep: the first version of the
model treated a reservation as a hold rather than a committed debit, and TLC rejected the
safe configurations until the settlement semantics were corrected.

Java: no system JRE is required. `jdk4py` ships one as a wheel; TLC itself is
`formal/tools/tla2tools.jar` (see formal/README.md).

Usage:
    python formal/check.py            # check every configuration
    python formal/check.py b0_        # only configurations matching a prefix
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

FORMAL = Path(__file__).resolve().parent
ROOT = FORMAL.parent
CFG = FORMAL / "cfg"
RUN = FORMAL / ".run"
JAR = FORMAL / "tools" / "tla2tools.jar"
OUT = ROOT / "results" / "formal"

INVARIANTS = ["AccountingIntegrity", "Solvency", "LedgerConservation", "RefundBounded"]

HOLDS, VIOLATED = "HOLDS", "VIOLATED"

# The expected matrix, declared before running. `VIOLATED` means the unsafe architecture
# must be caught; `HOLDS` means the invariant must survive exhaustive exploration.
EXPECTED = {
    # B0 -- state synchronization. The lost update keeps every individual record
    # self-consistent; what breaks is conservation of the shared balance.
    "b0_vulnerable": {"AccountingIntegrity": HOLDS, "Solvency": HOLDS,
                      "LedgerConservation": VIOLATED, "RefundBounded": HOLDS},
    "b0_hardened":   {i: HOLDS for i in INVARIANTS},

    # M1 -- commitment timing, as a 2x2 over (reserves, abort-safe).
    "m1_post_completion":         {"AccountingIntegrity": VIOLATED, "Solvency": HOLDS,
                                   "LedgerConservation": HOLDS, "RefundBounded": HOLDS},
    "m1_reserve_refund_on_abort": {"AccountingIntegrity": VIOLATED, "Solvency": HOLDS,
                                   "LedgerConservation": HOLDS, "RefundBounded": VIOLATED},
    "m1_no_reserve_settle":       {"AccountingIntegrity": HOLDS, "Solvency": VIOLATED,
                                   "LedgerConservation": HOLDS, "RefundBounded": HOLDS},
    "m1_reserve_reconcile":       {i: HOLDS for i in INVARIANTS},

    # M2 -- usage authority.
    "m2_client":         {"AccountingIntegrity": VIOLATED, "Solvency": HOLDS,
                          "LedgerConservation": HOLDS, "RefundBounded": VIOLATED},
    "m2_server_recount": {i: HOLDS for i in INVARIANTS},

    # The conjunction of all three defenses, under contention + abort + a lying client.
    "all_defenses":      {i: HOLDS for i in INVARIANTS},
    "all_defenses_3req": {i: HOLDS for i in INVARIANTS},
}

MECHANISM = {
    "b0_vulnerable": "B0", "b0_hardened": "B0",
    "m1_post_completion": "M1", "m1_reserve_refund_on_abort": "M1",
    "m1_no_reserve_settle": "M1", "m1_reserve_reconcile": "M1",
    "m2_client": "M2", "m2_server_recount": "M2",
    "all_defenses": "ALL", "all_defenses_3req": "ALL",
}


def java_exe() -> str:
    try:
        import jdk4py
        return str(jdk4py.JAVA)
    except ImportError:
        return "java"


def single_invariant_cfg(name: str, inv: str) -> Path:
    """Derive a one-invariant .cfg from the canonical multi-invariant one."""
    src = (CFG / f"{name}.cfg").read_text(encoding="utf-8")
    head = src.split("INVARIANTS")[0].rstrip()
    RUN.mkdir(exist_ok=True)
    dst = RUN / f"{name}__{inv}.cfg"
    dst.write_text(f"{head}\n\nINVARIANTS\n    TypeOK\n    {inv}\n", encoding="utf-8")
    return dst


def parse_states(text: str) -> dict:
    m = re.search(r"(\d+) states generated, (\d+) distinct states found", text)
    return {"states_generated": int(m.group(1)), "distinct_states": int(m.group(2))} if m else {}


def parse_trace(text: str) -> list[dict]:
    """Extract the counterexample trace TLC prints as `State n: <Action ...>`."""
    states, blocks = [], re.split(r"^State (\d+): (.*)$", text, flags=re.M)
    for i in range(1, len(blocks) - 2, 3):
        num, label, body = blocks[i], blocks[i + 1].strip(), blocks[i + 2]
        action = label.split(" line ")[0].strip("<>") or label
        vals = {}
        for line in body.split("\nState ")[0].splitlines():
            line = line.strip()
            if line.startswith("/\\ "):
                kv = line[3:].split(" = ", 1)
                if len(kv) == 2:
                    vals[kv[0].strip()] = kv[1].strip()
        states.append({"step": int(num), "action": action, "vars": vals})
    return states


def run_one(name: str, inv: str) -> dict:
    cfg = single_invariant_cfg(name, inv)
    # -deadlock disables TLC's deadlock check. Terminal states are the POINT of this
    # model (every request ends DONE or REJECTED and has no successor), so a "deadlock"
    # here is successful termination, not a defect.
    # -workers 1, deliberately. With parallel workers a run that HALTS at a
    # counterexample explores a nondeterministic number of states, so the reported totals
    # drift between runs and the artifact stops being reproducible. Single-worker BFS is
    # deterministic; the whole matrix still takes well under two minutes.
    cmd = [java_exe(), "-XX:+UseParallelGC", "-cp", str(JAR), "tlc2.TLC",
           "-config", str(cfg), "-workers", "1", "-cleanup", "-deadlock",
           str(FORMAL / "TokenAccounting.tla")]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(FORMAL))
    text = p.stdout + p.stderr

    violated = bool(re.search(rf"Invariant {inv} is violated", text))
    errored = (p.returncode != 0 and not violated) or               "Parsing or semantic analysis failed" in text
    observed = VIOLATED if violated else HOLDS
    expected = EXPECTED[name][inv]

    res = {"config": name, "mechanism": MECHANISM[name], "invariant": inv,
           "expected": expected, "observed": observed,
           "agrees": (observed == expected) and not errored,
           "seconds": round(time.perf_counter() - t0, 2), **parse_states(text)}
    if violated:
        tr = parse_trace(text)
        res["counterexample"] = tr
        res["trace_length"] = len(tr)
    if not res["agrees"]:
        res["raw_tail"] = text[-2500:]
    return res


def fmt_trace(states: list[dict]) -> str:
    out = []
    for s in states:
        v = s["vars"]
        out.append(f"       {s['step']:>2}. {s['action']:<16} "
                   f"bal={v.get('balance',''):<3} "
                   f"deliv={v.get('delivered','')}  "
                   f"debit={v.get('debit','')}  refund={v.get('refund','')}")
    return "\n".join(out)


def main() -> None:
    if not JAR.exists():
        sys.exit(f"missing {JAR} -- see formal/README.md for how to fetch TLC")
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    names = [n for n in EXPECTED if n.startswith(prefix)]

    OUT.mkdir(parents=True, exist_ok=True)
    results, matrix = [], {}
    print("=" * 92)
    print("TLC MODEL CHECKING -- formal/TokenAccounting.tla")
    print("=" * 92)
    print(f"{'configuration':<28}{'mech':<6}" + "".join(f"{i[:14]:<16}" for i in INVARIANTS))
    print("-" * 92)
    for n in names:
        row = {}
        for inv in INVARIANTS:
            r = run_one(n, inv)
            results.append(r)
            row[inv] = r
        matrix[n] = {i: row[i]["observed"] for i in INVARIANTS}
        cells = "".join(
            ("  " if row[i]["agrees"] else "!!") +
            f"{('viol' if row[i]['observed'] == VIOLATED else 'holds'):<5}"
            f"({row[i].get('distinct_states','?')})".ljust(9)
            for i in INVARIANTS)
        print(f"{n:<28}{MECHANISM[n]:<6}{cells}")
        for inv in INVARIANTS:
            if row[inv].get("counterexample") and row[inv]["agrees"]:
                print(f"     counterexample for {inv} "
                      f"({row[inv]['trace_length']} steps):")
                print(fmt_trace(row[inv]["counterexample"]))
        for inv in INVARIANTS:
            if not row[inv]["agrees"]:
                print(f"     !!! {inv}: expected {row[inv]['expected']}, "
                      f"observed {row[inv]['observed']}")
                print("     " + row[inv].get("raw_tail", "")[:1200].replace("\n", "\n     "))

    bad = [r for r in results if not r["agrees"]]
    payload = {"tool": "TLC (tla2tools 2.19)", "spec": "formal/TokenAccounting.tla",
               "invariants": INVARIANTS, "configurations": len(names),
               "checks": len(results), "disagreements": len(bad),
               "matrix": matrix, "results": results}
    (OUT / "model_check_results.json").write_text(json.dumps(payload, indent=2),
                                                  encoding="utf-8")
    shutil.rmtree(RUN, ignore_errors=True)

    total_states = sum(r.get("distinct_states", 0) for r in results)
    print("-" * 92)
    print(f"configurations : {len(names)}   checks (config x invariant): {len(results)}")
    print(f"distinct states explored (total): {total_states:,}")
    print(f"matched expectation : {len(results) - len(bad)}/{len(results)}")
    print(f"DISAGREEMENTS       : {len(bad)}")
    print(f"-> {OUT / 'model_check_results.json'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
