"""Network baseline measurement: Host A <-> Host B, before any accounting experiment runs.

Measures real round-trip time via repeated TCP connect timing (not ICMP -- cloud NSGs
commonly block ICMP, and a TCP SYN/SYN-ACK/ACK round trip to a port the experiment
actually uses, e.g. 5432, is a more honest proxy for "can the application reach this
service and how long does that take" than a ping that may be filtered independently of
the actual data path).

This does NOT measure or depend on clock synchronization between the two hosts -- RTT via
TCP connect timing is measured entirely on the LOCAL (Host A) monotonic clock: start a
timer, open a socket, wait for connect() to complete, stop the timer. No remote timestamp
is read or compared.

Usage:
    python -m experiments.two_machine.network_baseline --host <IP> --port 5432 --n 100
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "two_machine"


def tcp_connect_rtt_ms(host: str, port: int, timeout_s: float = 5.0) -> float | None:
    """One TCP connect round trip, timed on the LOCAL monotonic clock. None on failure."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout_s) as s:
            s.close()
        return (time.monotonic() - start) * 1000.0
    except OSError:
        return None


def percentile(data: list[float], p: float) -> float:
    if not data:
        return float("nan")
    data = sorted(data)
    k = (len(data) - 1) * p
    f, c = int(k), min(int(k) + 1, len(data) - 1)
    if f == c:
        return data[f]
    return data[f] + (data[c] - data[f]) * (k - f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="Host B public (or private) IP")
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--interval-s", type=float, default=0.1)
    ap.add_argument("--label", default="hostb")
    args = ap.parse_args()

    print(f"Measuring TCP-connect RTT to {args.host}:{args.port}, n={args.n} ...")
    samples: list[float] = []
    failures = 0
    for i in range(args.n):
        rtt = tcp_connect_rtt_ms(args.host, args.port)
        if rtt is None:
            failures += 1
        else:
            samples.append(rtt)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{args.n} ({failures} failed so far)")
        time.sleep(args.interval_s)

    result = {
        "target_host": args.host,
        "target_port": args.port,
        "label": args.label,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "clock_note": "RTT measured entirely on Host A's local monotonic clock "
                      "(time.monotonic start/stop around a TCP connect); no remote "
                      "timestamp read or compared -- does not depend on clock sync.",
        "requested_samples": args.n,
        "successful_samples": len(samples),
        "failed_samples": failures,
        "packet_loss_rate": failures / args.n if args.n else None,
    }
    if samples:
        result.update({
            "rtt_ms_min": min(samples),
            "rtt_ms_max": max(samples),
            "rtt_ms_mean": statistics.mean(samples),
            "rtt_ms_median": statistics.median(samples),
            "rtt_ms_stdev": statistics.stdev(samples) if len(samples) > 1 else 0.0,
            "rtt_ms_p95": percentile(samples, 0.95),
            "rtt_ms_p99": percentile(samples, 0.99),
            "raw_samples_ms": samples,
        })
        print(f"\nmin={result['rtt_ms_min']:.2f}ms  median={result['rtt_ms_median']:.2f}ms  "
              f"p95={result['rtt_ms_p95']:.2f}ms  p99={result['rtt_ms_p99']:.2f}ms  "
              f"max={result['rtt_ms_max']:.2f}ms  loss={result['packet_loss_rate']:.1%}")
    else:
        print("\nALL SAMPLES FAILED. Target unreachable on this port -- check NSG rules, "
              "VM state, and that the service is actually listening.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"network_baseline_{args.label}_{stamp}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
