"""Compare regenerated results against a previously captured headline baseline.

Produces paper/reproduction_consistency.md.

Classification of every differing metric:
  EXACT                    identical to the last digit
  EXPECTED-NONDETERMINISM  deterministic quantity that legitimately varies (e.g. a
                           timing-derived value), within a stated tolerance
  MEASUREMENT-NOISE        wall-clock/throughput quantity; report an interval, not a
                           frozen number
  METHODOLOGY-CHANGE       the experiment definition changed between runs
  BUG                      a difference that indicates incorrect behaviour
  STALE-DOCUMENTATION      documentation still quotes a superseded value

Usage:
    python -m experiments.reproduction_consistency --baseline <prev_headline.json>
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PAPER = ROOT / "paper"

# The M1 probe prompt tokenizes to 6 tokens under the mock server-side tokenizer;
# used to verify the accounting identity leak == (p_tok*p_in + delivered*p_out)/1000.
M1_PROMPT_TOKENS = 6
VULNERABLE_M1 = {"post_completion", "reserve_refund_on_abort"}

# Metric families and how differences should be judged.
# tol = absolute tolerance below which a difference is not worth flagging.
FAMILIES = {
    "B0_dollar_leak_mean":        dict(kind="deterministic", tol=1e-9, unit="$/trial"),
    # M1 leakage is deterministic *conditional on the number of tokens the client
    # received before its disconnect took effect*. Under load the disconnect can be
    # detected a token earlier/later (within-cell std of tokens_delivered is exactly 0
    # at concurrency <= 20 and ~0.01 at 50/100), so the value legitimately moves by
    # whole-token increments. We therefore verify the ACCOUNTING IDENTITY rather than
    # the raw number: any change must be exactly explained by delivered tokens.
    "M1_leak_per_request":        dict(kind="conditional_deterministic", tol=1e-9,
                                       unit="$/request"),
    "M2_leak_eff":                dict(kind="deterministic", tol=1e-9, unit="efficiency"),
    "realmodel_recount_frac":     dict(kind="timing", tol=5e-5, unit="fraction of e2e"),
    "tokenizer_p50_16384_natural": dict(kind="timing", tol=1e9, unit="ms"),
    "gateway_ratio":              dict(kind="timing", tol=1e9, unit="ratio"),
}


def latest(pat: str, folder: Path):
    c = sorted(glob.glob(str(folder / pat)))
    return max(c, key=os.path.getmtime) if c else None


def collect_current() -> dict:
    out: dict[str, dict] = {}
    f = latest("class6_*.summary.json", RESULTS)
    if f:
        d = json.load(open(f, encoding="utf-8"))
        out["B0_dollar_leak_mean"] = {
            c["posture"] + "_c" + str(c["concurrency"]): round(c["dollar_leak"]["mean"], 6)
            for c in d["cells"]}
    f = latest("m1_*.summary.json", RESULTS / "processed")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        sel = [c for c in d["cells"]
               if c["price_tier"] == "medium" and c["client_type"] == "attacker"]
        out["M1_leak_per_request"] = {
            f'{c["architecture"]}_c{c["concurrency"]}_a{int(c["abort_bin"])}':
                round(c["leak_per_request"], 6) for c in sel}
        # Context for the conditional-determinism test: does the accounting identity
        #   leak_per_request == (prompt_tokens*p_in + delivered*p_out)/1000
        # hold exactly for the observed delivered-token mean? (medium tier: 0.5/1.5)
        ctx: dict[str, dict] = {}
        for c in sel:
            delivered = c["tokens_delivered"]["mean"]
            predicted = (M1_PROMPT_TOKENS * 0.5 + delivered * 1.5) / 1000.0
            leaky = c["architecture"] in VULNERABLE_M1
            ctx[f'{c["architecture"]}_c{c["concurrency"]}_a{int(c["abort_bin"])}'] = {
                "delivered": delivered,
                "identity_holds": (abs(predicted - c["leak_per_request"]) < 1e-9) if leaky
                                  else (c["leak_per_request"] == 0.0),
            }
        out["_ctx_M1_leak_per_request"] = ctx
    f = latest("m2_*.summary.json", RESULTS / "processed")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        out["M2_leak_eff"] = {
            f'{c["architecture"]}_{c["manipulation"]}': round(c["leakage_efficiency"]["mean"], 6)
            for c in d["cells"] if c["price_tier"] == "medium" and c["concurrency"] == 1}
    f = latest("real_model_recount_*.json", RESULTS / "raw")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        out["realmodel_recount_frac"] = {
            f'{s["workload"]}_{s["posture"]}': round(s["recount_frac_of_e2e_p50"], 8)
            for s in d["summary"]}
    f = latest("tokenizer_overhead_*.json", RESULTS / "raw")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        out["tokenizer_p50_16384_natural"] = {
            r["engine"]: round(r["p50_ms"], 3) for r in d["results"]
            if r["status"] == "ok" and r["target_tokens"] == 16384 and r["workload"] == "natural"}
    f = latest("gateway_recount_*.json", RESULTS / "raw")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        out["gateway_ratio"] = {
            f'{c["engine"]}_s{c["size_tokens_cl100k"]}_c{c["concurrency"]}':
                round(c.get("throughput_ratio_vs_none") or 0, 4)
            for c in d["cells"] if c["concurrency"] in (1, 10) and c["engine"] != "none"}
    return out


def classify(family: str, prev: float, cur: float, ctx: dict | None = None) -> tuple[str, str]:
    meta = FAMILIES.get(family, dict(kind="timing", tol=1e-9))
    if prev == cur:
        return "EXACT", ""
    diff = abs(cur - prev)
    rel = diff / abs(prev) if prev else float("inf")

    if meta["kind"] == "deterministic":
        if diff <= meta["tol"]:
            return "EXACT", "within decimal tolerance"
        return "BUG", (f"deterministic metric changed by {diff:.6g} ({rel:.2%}) — "
                       "investigate; deterministic quantities must not move")

    if meta["kind"] == "conditional_deterministic":
        # The value may move only if the ACCOUNTING IDENTITY still holds exactly for
        # the observed delivered-token count. If the identity holds, the change is
        # caused by disconnect-timing jitter, not by an accounting error.
        if ctx and ctx.get("identity_holds") is True:
            d = ctx.get("delivered")
            return "EXPECTED-NONDETERMINISM", (
                f"accounting identity exact for delivered={d}; change is "
                f"disconnect-timing jitter ({diff:.6g})")
        if ctx and ctx.get("identity_holds") is False:
            return "BUG", ("accounting identity does NOT hold for the observed delivered "
                           "token count — this is an accounting error, not jitter")
        return "MEASUREMENT-NOISE", f"abs {diff:.6g}, rel {rel:.2%} (identity not checkable)"

    return "MEASUREMENT-NOISE", f"timing-derived; abs {diff:.6g}, rel {rel:.2%}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    args = ap.parse_args()
    prev = json.load(open(args.baseline, encoding="utf-8"))
    cur = collect_current()

    rows, bugs = [], []
    for family in FAMILIES:
        p_fam, c_fam = prev.get(family, {}), cur.get(family, {})
        keys = sorted(set(p_fam) | set(c_fam))
        for k in keys:
            pv, cv = p_fam.get(k), c_fam.get(k)
            if pv is None:
                rows.append((family, k, "—", f"{cv}", "—", "—", "METHODOLOGY-CHANGE",
                             "metric absent from the previous run"))
                continue
            if cv is None:
                rows.append((family, k, f"{pv}", "—", "—", "—", "METHODOLOGY-CHANGE",
                             "metric absent from the regenerated run"))
                continue
            cls, note = classify(family, pv, cv, (cur.get(f"_ctx_{family}") or {}).get(k))
            diff = cv - pv
            rel = (diff / pv) if pv else float("nan")
            rows.append((family, k, f"{pv:g}", f"{cv:g}", f"{diff:+.6g}",
                         ("n/a" if pv == 0 else f"{rel:+.2%}"), cls, note))
            if cls == "BUG":
                bugs.append((family, k, pv, cv))

    counts: dict[str, int] = {}
    for r in rows:
        counts[r[6]] = counts.get(r[6], 0) + 1

    lines = ["# Reproduction Consistency Audit\n",
             "Compares the headline metrics regenerated by the final clean reproduction "
             "against the values captured before it. Deterministic quantities must match "
             "exactly; timing-derived quantities are expected to move and are reported as "
             "intervals rather than frozen numbers.\n",
             "## Summary\n"]
    for k in sorted(counts):
        lines.append(f"- **{k}**: {counts[k]}")
    lines.append(f"\n**Total metrics compared: {len(rows)}**")
    lines.append(f"\n**BUG-classified discrepancies: {len(bugs)}**"
                 + (" — none; no corrective rerun required." if not bugs else
                    " — each must be investigated and the affected experiment rerun."))

    lines += ["\n## Investigation note: M1 leak-per-request\n",
              "The first pass of this audit flagged six M1 cells as potential BUGs because a",
              "quantity assumed deterministic had moved (e.g. 0.028725 → 0.028500). Investigation",
              "showed the accounting is deterministic but the *input* to it is not:",
              "",
              "- In every affected cell the accounting identity",
              "  `leak_per_request == (prompt_tokens x p_in + delivered x p_out) / 1000`",
              "  holds **exactly** (to 1e-9), i.e. the meter charged precisely for the tokens",
              "  the client actually received.",
              "- What changed is `tokens_delivered` (e.g. 17.15 → 17.00), because the number of",
              "  tokens the client reads before its disconnect takes effect depends on scheduling.",
              "- The within-cell standard deviation of `tokens_delivered` is **exactly 0** at",
              "  concurrency 1, 5 and 20, and ~0.011 at 50 and 100 — precisely where the flagged",
              "  cells are.",
              "",
              "The metric is therefore reclassified as **conditional-deterministic**: it may move",
              "only in whole-token increments, and only if the accounting identity still holds.",
              "The audit now verifies that identity instead of the raw value, so a genuine",
              "accounting error would still be reported as a BUG. No conclusion in the paper",
              "depends on the affected digits; the c=1 and c=5 columns are exactly reproducible."]

    # Timing families: report the observed interval instead of a single number.
    lines.append("\n## Timing families — observed intervals (not frozen values)\n")
    for family, meta in FAMILIES.items():
        if meta["kind"] != "timing":
            continue
        pf, cf = prev.get(family, {}), cur.get(family, {})
        common = sorted(set(pf) & set(cf))
        if not common:
            continue
        rels = [abs(cf[k] - pf[k]) / abs(pf[k]) for k in common if pf[k]]
        if rels:
            lines.append(f"- `{family}` ({meta['unit']}): {len(common)} metrics, "
                         f"median |Δ| = {sorted(rels)[len(rels)//2]:.1%}, "
                         f"max |Δ| = {max(rels):.1%} — treat as run-to-run variation.")

    lines += ["\n## Full comparison\n",
              "| family | metric | previous | regenerated | abs Δ | rel Δ | class | note |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")

    PAPER.mkdir(exist_ok=True)
    (PAPER / "reproduction_consistency.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"compared {len(rows)} metrics: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"-> {PAPER/'reproduction_consistency.md'}")
    if bugs:
        print("BUG-classified discrepancies:")
        for b in bugs[:10]:
            print("  ", b)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
