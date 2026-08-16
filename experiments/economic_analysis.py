"""Formal M2 analysis + economic sensitivity (Phases K and L).

PHASE K — formalize M2 as a transformation on the usage vector:

    U            true usage vector (input, output, cached, reasoning)
    P(.)         pricing function (category-wise, or flat-total)
    T(.)         attacker transformation of the declared usage
    billed       P(T(U))          true cost   C = P(U)
    Leak         C - P(T(U))      efficiency  Leak / C

For every (pricing basis, manipulation) we compute the transformed vector, the true
and billed costs, and explain WHY the manipulation succeeds or fails under that basis.
The explanation is derived from which categories T actually changes and which
categories the pricing basis reads -- not asserted.

PHASE L — economic sensitivity. Absolute dollars depend on arbitrary mock prices, so
we report normalized measures that do not:
    leaked tokens, leakage efficiency, leakage per 1K tokens, per 1M tokens,
    fraction of true inference value unpaid.
Dollar figures are retained but labelled SCENARIO values.

Writes results/tables/table_m2_formal.{md,tex},
       results/tables/table_economic_sensitivity.{md,tex},
       results/processed/economic_analysis.json
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"

CATEGORIES = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


def _esc(s):
    return (str(s).replace("\\", "").replace("_", r"\_").replace("%", r"\%")
            .replace("&", r"\&").replace("$", r"\$").replace("#", r"\#"))


def write_table(name, header, rows, caption, label):
    TAB.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    cols = "ll" + "r" * (len(header) - 2)
    widest = max([sum(len(str(c)) for c in r) for r in rows] + [sum(len(h) for h in header)])
    wide = len(header) >= 6 or widest > 70
    tex = [r"\begin{table}[t]", r"\centering", r"\small",
           f"\\caption{{{_esc(caption)}}}", f"\\label{{{label}}}"]
    if wide:
        tex.append(r"\resizebox{\linewidth}{!}{%")
    tex += [f"\\begin{{tabular}}{{{cols}}}", r"\toprule",
            " & ".join(_esc(h) for h in header) + r" \\", r"\midrule"]
    tex += [" & ".join(_esc(c) for c in r) + r" \\" for r in rows]
    tex += [r"\bottomrule", r"\end{tabular}"]
    if wide:
        tex.append(r"}")
    tex.append(r"\end{table}")
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def _delta_description(true_u: dict, decl_u: dict) -> str:
    """Which categories did T actually change? (derived, not asserted)"""
    parts = []
    for c in CATEGORIES:
        t, d = int(true_u.get(c, 0)), int(decl_u.get(c, 0))
        if t != d:
            parts.append(f"{c.replace('_tokens','')}:{t}->{d}")
    tt, dt = true_u.get("total"), decl_u.get("total")
    if tt is not None and dt is not None and tt != dt:
        parts.append(f"total:{tt}->{dt}")
    return ", ".join(parts) if parts else "unchanged"


def analyze(raw: dict) -> dict:
    trials = raw["trials"]
    formal_rows, econ_rows, records = [], [], []

    for t in trials:
        arch = t["architecture"]
        tier = t["price_tier"]
        manip = t["manipulation"]
        prices = t["prices"]
        rows = t["records"]
        if not rows:
            continue
        r0 = rows[0]
        extra = r0.get("extra") or {}
        true_u = extra.get("true") or {}
        decl_u = extra.get("declared") or {}

        n = len(rows)
        true_cost = sum(D(r["authoritative_cost"]) for r in rows)
        billed = sum(D(r["net_debit"]) for r in rows)
        leak = (true_cost - billed)
        eff = float(leak / true_cost) if true_cost > 0 else 0.0

        # token-normalized quantities (independent of the arbitrary price vector)
        true_tokens = sum(int(r["tokens_generated"]) for r in rows)
        # leaked tokens = the token-equivalent of unpaid value, at the true blended rate
        blended_per_token = (true_cost / true_tokens) if true_tokens else Decimal(0)
        leaked_tokens = float(leak / blended_per_token) if blended_per_token > 0 else 0.0

        rec = {
            "architecture": arch, "price_tier": tier, "manipulation": manip,
            "requests": n,
            "true_cost_scenario_usd": str(true_cost),
            "billed_scenario_usd": str(billed),
            "leak_scenario_usd": str(leak),
            "leakage_efficiency": eff,
            "true_tokens": true_tokens,
            "leaked_tokens": leaked_tokens,
            "leak_per_1k_tokens_scenario_usd": float(leak / true_tokens * 1000) if true_tokens else 0.0,
            "leak_per_1M_tokens_scenario_usd": float(leak / true_tokens * 1_000_000) if true_tokens else 0.0,
            "fraction_of_value_unpaid": eff,
            "true_usage": true_u, "declared_usage": decl_u,
            "transformation": _delta_description(true_u, decl_u),
        }
        records.append(rec)

    # ---- Phase K table: formal transformation view (medium tier only) ------- #
    basis = {"client": "category", "client_logged": "category", "client_total": "flat-total",
             "server_recount": "server (category)", "hybrid_reconcile": "server (category)",
             "upstream": "upstream (category)"}
    for r in [x for x in records if x["price_tier"] == "medium"
              and x["architecture"] in ("client", "client_total")]:
        b = basis[r["architecture"]]
        eff = r["leakage_efficiency"]
        if eff > 0.001:
            why = "T lowers a category the basis prices" if b == "category" else \
                  "T lowers the declared total the basis prices"
        elif r["transformation"] == "unchanged":
            why = "T is identity (honest)"
        elif b == "flat-total" and "total:" not in r["transformation"]:
            why = "T changes only subtotals; flat-total basis never reads them"
        elif b == "category" and r["transformation"].startswith("total:"):
            why = "T changes only the declared total; category basis never reads it"
        else:
            why = "T's change is priced at (near) the same rate"
        formal_rows.append([
            r["architecture"], b, r["manipulation"], r["transformation"][:44],
            f"{eff:+.3f}", why,
        ])

    # ---- Phase L table: economic sensitivity across tiers ------------------- #
    tiers = raw["parameters"]["tiers"]
    for manip in raw["parameters"]["manipulations"]:
        for arch in ("client", "client_total"):
            row = [arch, manip]
            effs = []
            for tier in tiers:
                m = [x for x in records if x["architecture"] == arch
                     and x["price_tier"] == tier and x["manipulation"] == manip]
                if m:
                    row.append(f"{float(D(m[0]['leak_scenario_usd'])):+.4f}")
                    effs.append(m[0]["leakage_efficiency"])
                else:
                    row.append("--")
            def _eff(tier):
                m = [x for x in records if x["architecture"] == arch
                     and x["price_tier"] == tier and x["manipulation"] == manip]
                return m[0]["leakage_efficiency"] if m else None
            e_lo, e_med, e_hi = _eff("low"), _eff("medium"), _eff("high")
            m_med = [x for x in records if x["architecture"] == arch
                     and x["price_tier"] == "medium" and x["manipulation"] == manip]
            if m_med:
                row.append(f"{m_med[0]['leaked_tokens']:.0f}")
                row.append(f"{m_med[0]['leakage_efficiency']:+.3f}")
                # Invariance under UNIFORM price scaling (low -> medium is exactly x10).
                row.append("yes" if (e_lo is not None and e_med is not None
                                     and abs(e_lo - e_med) < 1e-9) else "no")
                # Structure change (medium -> high alters output/input ratio 3 -> 5):
                # efficiency is NOT expected to be invariant here.
                row.append("--" if (e_med is None or e_hi is None) else f"{e_hi - e_med:+.3f}")
            econ_rows.append(row)

    write_table("table_m2_formal",
                ["architecture", "pricing basis", "manipulation T", "vector change T(U)",
                 "leak eff.", "why it succeeds / fails"],
                formal_rows,
                "M2 as a transformation on the usage vector. Whether a manipulation pays off is "
                "determined by whether the pricing basis reads the field T changes.",
                "tab:m2formal")

    write_table("table_economic_sensitivity",
                ["architecture", "manipulation"] + [f"{t} ($)" for t in tiers]
                + ["leaked tokens", "leak eff.", "inv. under x10 scale?", "d(eff) med->high"],
                econ_rows,
                "Economic sensitivity. Dollar columns are SCENARIO values under synthetic price "
                "tiers; leakage efficiency and leaked tokens are the price-independent measures. "
                "Efficiency is invariant under uniform price scaling (low->medium) but not under a "
                "price-structure change (medium->high alters the output/input ratio).",
                "tab:econ")

    return {"records": records, "formal_rows": formal_rows, "econ_rows": econ_rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(RAW / "m2_tiers.json"))
    args = ap.parse_args()
    p = Path(args.input)
    if not p.exists():
        cands = sorted(RAW.glob("m2_*.json"))
        if not cands:
            raise SystemExit("no m2 raw data")
        p = max(cands, key=lambda x: x.stat().st_mtime)
    raw = json.loads(p.read_text(encoding="utf-8"))
    out = analyze(raw)
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "economic_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"input: {p.name}")
    print(f"records: {len(out['records'])}")
    print("tables -> table_m2_formal, table_economic_sensitivity")


if __name__ == "__main__":
    main()
