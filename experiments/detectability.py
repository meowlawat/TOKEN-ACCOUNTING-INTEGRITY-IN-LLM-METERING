"""Evidence-based detectability classifier (audit fix F1).

The previous implementation assigned a detectability level from static architecture
metadata (`arch.detection`, and for M1 literally `"D3" if arch.safe else "D0"`). That is
circular: it restates a label the experimenter set, and the independent audit showed the
resulting D0/D1 distinction is **contradicted by the data** -- the `client` architecture
(labelled D0 "invisible") retains exactly the same usage evidence as `client_logged`
(labelled D1 "reconcilable").

This module classifies detectability **only from observable evidence in the ledger row**.
It never reads:
    * the architecture name
    * the posture / `safe` flag
    * any stored `detection_level`
    * any expected outcome

Levels (evidence definitions, not labels):

    D0  no detectable evidence
        A leak occurred, but nothing retained in the record lets a detector notice:
        no independent usage reference, and the balance movement is consistent with
        the billed amount.

    D1  post-hoc detectable / reconcilable
        A leak occurred and the retained evidence contains an independent reference
        (e.g. a server-observed usage vector, or a delivered-token count) that
        disagrees with what was billed. An offline reconciliation pass comparing
        retained fields would surface it.

    D2  application-visible discrepancy
        The gateway itself recorded a discrepancy signal (e.g. a correction flag) that
        an operational monitor could alert on, but the leak still stands.

    D3  prevented / corrected in real time
        No leak remains: either it never occurred, or the system corrected it before
        settlement.

Usage:
    python -m experiments.detectability            # classify latest M1 + M2 raw data
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"

USAGE_CATS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def classify_record(rec: dict) -> tuple[str, str]:
    """Return (level, reason) from observable evidence only.

    Deliberately blind to architecture, posture, and any stored detection level.
    """
    served = bool(rec.get("served"))
    auth = D(rec.get("authoritative_cost"))
    net = D(rec.get("net_debit"))
    leak = auth - net if served else -net

    # ---- D3: nothing to detect -----------------------------------------------
    if leak <= 0:
        return "D3", "no residual leak (prevented, corrected, or never occurred)"

    extra = rec.get("extra") or {}

    # ---- D2: the application itself flagged a discrepancy ---------------------
    if extra.get("corrected") is True:
        return "D2", "gateway recorded a correction/discrepancy signal"

    # ---- D1: retained evidence contains an independent usage reference that
    #          disagrees with what was billed -------------------------------
    true_u = extra.get("true")
    decl_u = extra.get("declared")
    if isinstance(true_u, dict) and isinstance(decl_u, dict):
        if any(int(true_u.get(c, 0)) != int(decl_u.get(c, 0)) for c in USAGE_CATS) or \
           true_u.get("total") != decl_u.get("total"):
            return "D1", ("record retains a server-observed usage vector that disagrees "
                          "with the declared vector; offline reconciliation would surface it")

    # M1-style evidence: a delivered-token count is retained and is inconsistent
    # with a zero/short debit.
    delivered = rec.get("tokens_delivered")
    if delivered is not None and int(delivered) > 0 and net < auth:
        return "D1", ("record retains a delivered-token count inconsistent with the "
                      "committed debit; offline reconciliation would surface it")

    # ---- D0: leak with no retained contradiction -----------------------------
    return "D0", "leak occurred and no retained evidence contradicts the billed amount"


def analyze(path: Path, mechanism: str) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    # group by architecture ONLY for reporting; the classifier never sees it
    by_arch: dict[str, Counter] = defaultdict(Counter)
    reasons: dict[str, Counter] = defaultdict(Counter)
    label_vs_evidence = Counter()
    evidence_fingerprint: dict[str, set] = defaultdict(set)

    for t in d["trials"]:
        arch = t["architecture"]
        for r in t["records"]:
            level, reason = classify_record(r)
            by_arch[arch][level] += 1
            reasons[arch][reason] += 1
            stored = r.get("detection_level")
            label_vs_evidence[(stored, level)] += 1
            # what evidence fields does this architecture actually retain?
            ex = r.get("extra") or {}
            fields = tuple(sorted(k for k in ("true", "declared", "corrected") if k in ex))
            evidence_fingerprint[arch].add(fields)

    return {
        "mechanism": mechanism, "file": path.name,
        "by_architecture": {a: dict(c) for a, c in by_arch.items()},
        "reasons": {a: dict(c) for a, c in reasons.items()},
        "stored_vs_evidence": {f"stored={k[0]}|evidence={k[1]}": v
                               for k, v in label_vs_evidence.items()},
        "retained_evidence_fields": {a: sorted(list(s)) for a, s in evidence_fingerprint.items()},
    }


def latest(pattern: str, folder: Path):
    c = [p for p in glob.glob(str(folder / pattern)) if ".summary." not in os.path.basename(p)]
    return Path(max(c, key=os.path.getmtime)) if c else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PROC / "detectability.json"))
    args = ap.parse_args()

    out = {}
    for mech, pat in (("m2", "m2_2*.json"), ("m1", "m1_2*.json")):
        p = latest(pat, RAW)
        if p:
            out[mech] = analyze(p, mech)

    PROC.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=" * 78)
    print("EVIDENCE-BASED DETECTABILITY (classifier is blind to architecture labels)")
    print("=" * 78)
    for mech, res in out.items():
        print(f"\n{mech.upper()}  <- {res['file']}")
        for arch, counts in sorted(res["by_architecture"].items()):
            fields = res["retained_evidence_fields"][arch]
            print(f"  {arch:<18} {dict(counts)}   retained evidence: {fields}")
        print("  stored-label vs evidence-derived:")
        for k, v in sorted(res["stored_vs_evidence"].items()):
            agree = k.split("|")[0].split("=")[1] == k.split("|")[1].split("=")[1]
            print(f"    {k:<40} n={v:<6} {'agree' if agree else 'DISAGREE'}")

    # The decisive question for F1.
    m2 = out.get("m2")
    if m2:
        c = set(m2["by_architecture"].get("client", {}))
        cl = set(m2["by_architecture"].get("client_logged", {}))
        same_ev = (m2["retained_evidence_fields"].get("client")
                   == m2["retained_evidence_fields"].get("client_logged"))
        print("\n" + "-" * 78)
        print("F1 DECISIVE TEST: do `client` and `client_logged` differ in EVIDENCE?")
        print(f"  client       levels={sorted(c)}  evidence={m2['retained_evidence_fields'].get('client')}")
        print(f"  client_logged levels={sorted(cl)}  evidence={m2['retained_evidence_fields'].get('client_logged')}")
        print(f"  identical retained evidence: {same_ev}")
        print(f"  identical evidence-derived levels: {c == cl}")
        if same_ev and c == cl:
            print("  => The claimed D0 vs D1 distinction is NOT supported by the evidence.")
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
