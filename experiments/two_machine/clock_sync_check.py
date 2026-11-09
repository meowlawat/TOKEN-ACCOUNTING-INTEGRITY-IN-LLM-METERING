"""Clock synchronization characterization: Host A <-> Host B.

Records TWO independent things, and does not conflate them:

1. chrony's own self-reported state on Host B (chronyc tracking / sources) -- what the
   NTP daemon believes about its own synchronization.
2. An INDEPENDENTLY measured host-vs-host time.time_ns() offset, via SSH, using the same
   direct-comparison method already used in Phase 4 to diagnose the perf_counter_ns()
   clock-domain mismatch (see RESEARCH_LOG.md). This does not trust chrony's self-report;
   it measures the actual observable difference, bounded by the SSH round-trip delay
   (recorded alongside the offset as its uncertainty bound).

Per the experiment's own rule: cross-host economic correctness must NOT depend on this
number. This script exists so that if any LATENCY figure is ever reported, its uncertainty
is stated rather than assumed away -- not to gate correctness, which is read from
ledger/balance state regardless of clock agreement.

Usage:
    python -m experiments.two_machine.clock_sync_check --host <IP> --user azureuser \
        --key ~/.ssh/llm-metering-two-machine
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "two_machine"


def ssh_run(host: str, user: str, key: str, remote_cmd: str, timeout: int = 20) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["ssh", "-i", key, "-o", "StrictHostKeyChecking=accept-new",
         "-o", f"ConnectTimeout={timeout}", f"{user}@{host}", remote_cmd],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    return proc.returncode, proc.stdout, proc.stderr


def measure_offset_ns(host: str, user: str, key: str, rounds: int = 5) -> dict:
    """Bound the Host A <-> Host B time.time_ns() offset using repeated SSH round trips.

    Method: record t0 (local, before SSH), ssh out to read Host B's time.time_ns() (t_b),
    record t1 (local, after SSH returns). The true local time when Host B sampled its
    clock is somewhere in [t0, t1]; the offset estimate uses the midpoint, and the
    uncertainty is reported as half the round-trip span (t1 - t0) / 2, which is the
    honest bound given no further clock-sync protocol (NTP-style) is being run here.
    """
    samples = []
    for _ in range(rounds):
        t0 = time.time_ns()
        rc, out, err = ssh_run(host, user, key, "python3 -c 'import time; print(time.time_ns())'")
        t1 = time.time_ns()
        if rc != 0:
            continue
        try:
            t_b = int(out.strip())
        except ValueError:
            continue
        rtt = t1 - t0
        local_mid = (t0 + t1) // 2
        offset = t_b - local_mid  # positive => Host B's clock is ahead of Host A's
        samples.append({"offset_ns": offset, "round_trip_ns": rtt,
                        "uncertainty_ns": rtt // 2})
    return {"rounds_attempted": rounds, "rounds_succeeded": len(samples), "samples": samples}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", default="azureuser")
    ap.add_argument("--key", default=str(Path.home() / ".ssh" / "llm-metering-two-machine"))
    ap.add_argument("--rounds", type=int, default=5)
    args = ap.parse_args()

    print(f"== chrony self-report on {args.host} ==")
    rc1, tracking_out, tracking_err = ssh_run(args.host, args.user, args.key, "chronyc tracking")
    rc2, sources_out, sources_err = ssh_run(args.host, args.user, args.key, "chronyc sources -v")
    print(tracking_out or tracking_err)
    print(sources_out or sources_err)

    print(f"\n== Independently measured time.time_ns() offset (A vs B), {args.rounds} rounds ==")
    offset_result = measure_offset_ns(args.host, args.user, args.key, args.rounds)
    for s in offset_result["samples"]:
        print(f"  offset={s['offset_ns']/1e6:+.3f}ms  "
              f"uncertainty=+/-{s['uncertainty_ns']/1e6:.3f}ms  "
              f"(round-trip={s['round_trip_ns']/1e6:.3f}ms)")

    result = {
        "host_b": args.host,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "chronyc_tracking_exit_code": rc1,
        "chronyc_tracking_raw": tracking_out if rc1 == 0 else f"FAILED: {tracking_err}",
        "chronyc_sources_exit_code": rc2,
        "chronyc_sources_raw": sources_out if rc2 == 0 else f"FAILED: {sources_err}",
        "independent_offset_measurement": offset_result,
        "note": "This offset measurement is diagnostic only. Economic correctness in "
                "this experiment is read from ledger/balance state, never derived by "
                "subtracting unsynchronized wall-clock timestamps across hosts.",
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"clock_sync_{stamp}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n-> {out_path}")

    if rc1 != 0:
        print("\nWARNING: could not read chrony state from Host B. Do NOT claim clocks "
              "are synchronized. Treat any cross-host latency figure as unverified.")


if __name__ == "__main__":
    main()
