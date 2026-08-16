"""Adversarial validation of the measurement harness (Phase H).

Two independent families of checks:

PART 1 — FAULT INJECTION (do the integrity gates actually fail closed?)
    Deliberately corrupt copies of real result files, one field at a time, and
    require the summarizer's gates to detect each corruption. A gate that cannot be
    made to fail is not evidence of correctness.

PART 2 — METAMORPHIC PROPERTIES (does the measured system obey relations that must
    hold by construction?) Each property is asserted ONLY where it is mathematically
    justified for this architecture; where the architecture makes a relation false we
    say so instead of asserting it.

Exits non-zero if any check fails. Writes results/processed/metamorphic_report.json.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TMP = RAW / "_metamorphic_tmp"


class Report:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, part: str, name: str, ok: bool, detail: str = ""):
        self.rows.append({"part": part, "check": name, "passed": bool(ok), "detail": detail})
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

    @property
    def ok(self) -> bool:
        return all(r["passed"] for r in self.rows)


def _latest(pattern: str) -> Path:
    c = sorted(RAW.glob(pattern))
    if not c:
        raise SystemExit(f"no {pattern} in {RAW}")
    return max(c, key=lambda p: p.stat().st_mtime)


def _run_summarizer(module: str, path: Path) -> int:
    """Return the summarizer's exit code for a given input file."""
    r = subprocess.run([sys.executable, "-m", module, "--input", str(path)],
                       cwd=str(ROOT), capture_output=True, text=True)
    return r.returncode


# --------------------------------------------------------------------------- #
# PART 1 — fault injection
# --------------------------------------------------------------------------- #
def part1_fault_injection(rep: Report) -> None:
    print("\nPART 1 — FAULT INJECTION (gates must fail closed)")
    TMP.mkdir(parents=True, exist_ok=True)

    for mech, module, pattern in (("M2", "experiments.summarize_m2", "m2_*.json"),
                                  ("M1", "experiments.summarize_m1", "m1_*.json")):
        src = _latest(pattern)
        base = json.loads(src.read_text(encoding="utf-8"))

        # sanity: the pristine file must PASS (a gate that always fails is useless)
        clean = TMP / f"{mech}_clean.json"
        clean.write_text(json.dumps(base), encoding="utf-8")
        rep.add("fault_injection", f"{mech}: pristine file passes gates",
                _run_summarizer(module, clean) == 0, "clean data must exit 0")

        mutations = {
            "leakage value changed": lambda d: d["trials"][0]["records"][0].__setitem__("leak", "9.999999"),
            "committed debit changed": lambda d: d["trials"][0]["records"][0].__setitem__("net_debit", "0.000001"),
            "served flag flipped": lambda d: d["trials"][0]["records"][0].__setitem__(
                "served", not d["trials"][0]["records"][0]["served"]),
            "final balance changed": lambda d: d["trials"][0].__setitem__(
                "final_balance", str(Decimal(d["trials"][0]["final_balance"]) + Decimal("5"))),
            "invariant result flipped": lambda d: d["trials"][0]["records"][0].__setitem__(
                "invariant_ok", not d["trials"][0]["records"][0]["invariant_ok"]),
            "ledger row deleted": lambda d: d["trials"][0]["records"].pop(0),
        }
        for name, mutate in mutations.items():
            d = copy.deepcopy(base)
            mutate(d)
            p = TMP / f"{mech}_{name.replace(' ', '_')}.json"
            p.write_text(json.dumps(d), encoding="utf-8")
            code = _run_summarizer(module, p)
            rep.add("fault_injection", f"{mech}: detects {name}", code != 0,
                    f"summarizer exited {code}, expected non-zero")


# --------------------------------------------------------------------------- #
# PART 2 — metamorphic properties (live, against the testbed)
# --------------------------------------------------------------------------- #
async def _m2_trial(client, aid, key, arch, tier, manip, n, prompt, seed=1337):
    """Run n M2 requests in one trial; return the audit."""
    from attacks.m2_usage_authority import send
    meta = (await client.post("/admin/m-trials", json={
        "account_id": aid, "mechanism": "m2", "architecture": arch, "price_tier": tier,
        "prompt": prompt, "seed": seed, "initial_credits": 1e8})).json()
    tid = meta["trial_id"]
    for _ in range(n):
        await send(client, key, prompt, seed, tid, manip)
    return (await client.post(f"/admin/m-trials/{tid}/finalize")).json()


async def part2_metamorphic(rep: Report, base_url: str) -> None:
    print("\nPART 2 — METAMORPHIC PROPERTIES (live testbed)")
    PROMPT = "metamorphic property validation prompt for accounting integrity"
    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        (await client.get("/health")).raise_for_status()
        acct = (await client.post("/admin/accounts",
                                  json={"name": "metamorphic", "balance": 0.0})).json()
        aid, key = acct["id"], acct["api_key"]

        # --- P1: request-count scaling -------------------------------------- #
        # JUSTIFIED: M2 leak is per-request and independent across requests
        # (no shared state in the billing decision), so total leak must scale
        # EXACTLY linearly with identical-request count.
        a = await _m2_trial(client, aid, key, "client", "medium", "under_report_output_90", 10, PROMPT)
        b = await _m2_trial(client, aid, key, "client", "medium", "under_report_output_90", 20, PROMPT)
        la, lb = Decimal(a["total_leak"]), Decimal(b["total_leak"])
        exact = (lb == la * 2)
        rep.add("metamorphic", "P1 doubling identical M2 requests exactly doubles total leak",
                exact, f"{la} -> {lb} (expected {la*2})")

        # --- P2: price-tier scaling ----------------------------------------- #
        # JUSTIFIED: cost is linear in per-1k prices, so dollar leak must scale by
        # the tier price ratio while leakage EFFICIENCY (a ratio) is invariant.
        lo = await _m2_trial(client, aid, key, "client", "low", "under_report_output_90", 10, PROMPT)
        med = await _m2_trial(client, aid, key, "client", "medium", "under_report_output_90", 10, PROMPT)
        hi = await _m2_trial(client, aid, key, "client", "high", "under_report_output_90", 10, PROMPT)
        l_lo, l_med, l_hi = (Decimal(x["total_leak"]) for x in (lo, med, hi))
        # medium output price 1.5 vs low 0.15 => 10x ; high 15.0 => 10x vs medium
        ok_ratio = (abs(l_med / l_lo - 10) < Decimal("0.01")) and (abs(l_hi / l_med - 10) < Decimal("0.01"))
        rep.add("metamorphic", "P2 dollar leak scales with price tier (10x steps)",
                ok_ratio, f"low={l_lo} med={l_med} hi={l_hi}")

        def eff(audit):
            tot = sum(Decimal(r["authoritative_cost"]) for r in audit["rows"])
            return (Decimal(audit["total_leak"]) / tot) if tot else Decimal(0)
        e_lo, e_med, e_hi = eff(lo), eff(med), eff(hi)

        # P3a JUSTIFIED: leakage efficiency is a RATIO of two costs computed with the
        # same price vector, so it is invariant under UNIFORM scaling of all prices.
        # `low -> medium` is exactly a uniform x10 scaling (verified in usage.Prices).
        rep.add("metamorphic", "P3a leakage efficiency invariant under UNIFORM price scaling (low->medium)",
                e_lo == e_med, f"low={e_lo} medium={e_med}")

        # P3b NOT an invariance claim: `medium -> high` changes the price STRUCTURE
        # (output/input ratio 3 -> 5), not merely the scale. Efficiency therefore may
        # legitimately differ; asserting invariance here would be mathematically wrong.
        # We record the observed difference as a finding instead of a pass/fail gate.
        print(f"  [note] P3b price-STRUCTURE change (medium->high, out/in ratio 3->5): "
              f"efficiency {e_med} -> {e_hi} (difference is expected, not a violation)")

        # --- P4: hardening never increases leakage -------------------------- #
        # JUSTIFIED: server-authoritative billing bills >= the client-declared basis
        # for any manipulation in our catalogue, so leak_hardened <= leak_vulnerable.
        worst = Decimal(0)
        bad = None
        for manip in ["under_report_output_50", "under_report_output_90", "drop_reasoning",
                      "inflate_cached", "total_mismatch", "rounding_shave", "honest"]:
            v = await _m2_trial(client, aid, key, "client", "medium", manip, 5, PROMPT)
            h = await _m2_trial(client, aid, key, "server_recount", "medium", manip, 5, PROMPT)
            lv, lh = Decimal(v["total_leak"]), Decimal(h["total_leak"])
            if lh > lv:
                bad = f"{manip}: hardened {lh} > vulnerable {lv}"
            worst = max(worst, lh)
        rep.add("metamorphic", "P4 hardened leak never exceeds vulnerable leak (per manipulation)",
                bad is None, bad or "")
        rep.add("metamorphic", "P5 hardened leak is exactly zero for every manipulation",
                worst == 0, f"max hardened leak={worst}")

        # --- P6: honest client leaks nothing even on vulnerable arch -------- #
        hon = await _m2_trial(client, aid, key, "client", "medium", "honest", 10, PROMPT)
        rep.add("metamorphic", "P6 honest client on vulnerable architecture leaks 0",
                Decimal(hon["total_leak"]) == 0, f"leak={hon['total_leak']}")

        # --- P7: ledger conservation holds in every trial above ------------- #
        alltrials = [a, b, lo, med, hi, hon]
        bad_c = [t["trial_id"][:8] for t in alltrials if t["reconciled"] is not True]
        rep.add("metamorphic", "P7 ledger conservation holds in all metamorphic trials",
                not bad_c, f"unreconciled: {bad_c}")

        # --- P8: token-volume monotonicity (M1) ----------------------------- #
        # JUSTIFIED: on a post-completion meter, leak = value delivered before the
        # (absent) commit, so leak must be NON-DECREASING in tokens delivered.
        from attacks.m1_stream_abort import stream_and_abort
        q = (await client.get("/admin/quote", params={"prompt": PROMPT, "seed": 1337})).json()
        n_out = int(q["completion_tokens"])
        leaks = []
        for pct in (10, 25, 50, 75, 90):
            meta = (await client.post("/admin/m-trials", json={
                "account_id": aid, "mechanism": "m1", "architecture": "post_completion",
                "price_tier": "medium", "prompt": PROMPT, "seed": 1337,
                "initial_credits": 1e8})).json()
            tid = meta["trial_id"]
            await stream_and_abort(client, key, PROMPT, 1337, tid, max(1, round(pct/100*n_out)))
            await asyncio.sleep(0.25)
            aud = (await client.post(f"/admin/m-trials/{tid}/finalize")).json()
            leaks.append((pct, Decimal(aud["total_leak"])))
        mono = all(leaks[i][1] <= leaks[i+1][1] for i in range(len(leaks)-1))
        rep.add("metamorphic", "P8 M1 leak is non-decreasing in tokens delivered",
                mono, ", ".join(f"{p}%={l}" for p, l in leaks))

        # --- P9: NOT asserted (documented non-property) ---------------------- #
        print("  [note] P9 NOT asserted: leak is deliberately NOT expected to scale with")
        print("         concurrency -- the measured architecture makes that relation false")
        print("         (M1/M2 are per-request defects). Asserting it would be wrong.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--skip-live", action="store_true")
    args = ap.parse_args()

    rep = Report()
    part1_fault_injection(rep)
    if not args.skip_live:
        asyncio.run(part2_metamorphic(rep, args.base_url))

    PROC.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in rep.rows if r["passed"])
    (PROC / "metamorphic_report.json").write_text(
        json.dumps({"passed": passed, "total": len(rep.rows), "ok": rep.ok,
                    "checks": rep.rows}, indent=2), encoding="utf-8")

    # Tidy ONLY the temp artifacts this script created. NOTE: globbing here is unsafe
    # on case-insensitive filesystems (Windows) -- e.g. "M1_*.summary.*" also matches
    # the real "m1_<ts>.summary.json". Delete by exact derived name instead.
    for f in list(TMP.glob("*.json")) if TMP.exists() else []:
        for suffix in (".summary.json", ".summary.csv", ".summary.md"):
            p = PROC / f"{f.stem}{suffix}"
            if p.exists():
                p.unlink()
        f.unlink()
    if TMP.exists():
        try:
            TMP.rmdir()
        except OSError:
            pass

    print(f"\n{passed}/{len(rep.rows)} checks passed -> {PROC/'metamorphic_report.json'}")
    if not rep.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
