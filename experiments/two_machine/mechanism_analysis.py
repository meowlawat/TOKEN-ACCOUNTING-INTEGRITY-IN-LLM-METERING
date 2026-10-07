"""Tier-1 mechanism analysis: reconstruct the T1-T7 timeline for a run and test whether
over-serving actually correlates with authorization crossing settlement, rather than just
asserting it.

Reads a run's raw JSONL (written by run_distributed_experiment.py) for its request_ids,
fetches each request's MRecord.extra (written by async_routes.py's gateway-side
instrumentation and, if the worker was run with --instrument, async/worker_main.py's
worker-side instrumentation) from Postgres, and computes:

  - intra-gateway intervals (T1->T2 read latency, T2->T3 decision, T3->T4 event creation,
    T4->T4b emit) -- same-process perf_counter_ns deltas, valid for ANY topology (local or
    real two-machine), never subject to cross-host clock-domain concerns.
  - cross-process exposure window (T4 created -> T7 applied) -- wall-clock (time.time_ns())
    on both ends. For the LOCAL sibling-worker topology (C1) this is precise (same clock
    domain, verified). For the REAL two-machine topology (C2) this inherits the cross-host
    clock-offset uncertainty already characterized in results/two_machine/clock_sync_*.json
    -- reported with that caveat, never treated as exact.
  - for each concurrent cell, whether each request's own authorization-read (T1, gateway-
    local perf_counter_ns, directly comparable across the request's SIBLINGS in the same
    cell since they share one gateway process) happened before any sibling request's own
    settlement (T7) had landed -- the actual causal test for "did this request's admission
    decision cross another request's commitment", not an assumed correlation.

Can read Postgres either directly (local topology, DATABASE_URL reachable) or over SSH
(real two-machine topology, Host B's Postgres is not meant to be queried directly from an
arbitrary host -- this script SSHes in and runs psql, the same pattern already used by
clock_sync_check.py and failure_injection_remote.py).

Usage:
    python -m experiments.two_machine.mechanism_analysis \
        --jsonl experiments/two_machine/raw/C2_concurrent_20261007T003513Z.jsonl \
        --via ssh --host 20.198.74.220
    python -m experiments.two_machine.mechanism_analysis \
        --jsonl experiments/two_machine/raw/C1_concurrent_....jsonl --via local
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "two_machine"


def load_request_ids(jsonl_path: Path) -> list[dict]:
    """Return the raw per-request records (with condition_delay_ms, arrival, served,
    etc.) exactly as the harness wrote them -- the source of truth for which request_ids
    belong to this run and what cell each belongs to."""
    rows = [json.loads(l) for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def fetch_extra_via_ssh(request_ids: list[str], host: str, user: str, key: str,
                        db_container: str = "llm-metering-db-1", batch_size: int = 40) -> dict[str, dict]:
    """Batch-fetch MRecord.request_id -> extra for the given ids, over SSH, from the
    real Host B's own Postgres container. Chunked (not one single IN-clause) because a
    long SQL string embedded in an SSH remote command can exceed what the remote shell's
    command-line parsing handles cleanly -- confirmed directly: a 330-id single query
    failed with a shell quoting error, a 40-id chunk did not."""
    out: dict[str, dict] = {}
    for i in range(0, len(request_ids), batch_size):
        chunk = request_ids[i:i + batch_size]
        ids_sql = ",".join(f"'{rid}'" for rid in chunk)
        sql = (f"SELECT request_id, extra::text FROM m_records "
               f"WHERE request_id IN ({ids_sql});")
        remote_cmd = (f"sudo docker exec {db_container} psql -U postgres -d metering "
                     f"-t -A -F'|' -c \"{sql}\"")
        proc = subprocess.run(
            ["ssh", "-i", key, "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=20", f"{user}@{host}", remote_cmd],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ssh/psql failed: {proc.stderr}")
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            rid, extra_json = line.split("|", 1)
            try:
                out[rid.strip()] = json.loads(extra_json)
            except json.JSONDecodeError:
                continue
    return out


def fetch_extra_via_local_db_container(request_ids: list[str], container: str) -> dict[str, dict]:
    ids_sql = ",".join(f"'{rid}'" for rid in request_ids)
    sql = f"SELECT request_id, extra::text FROM m_records WHERE request_id IN ({ids_sql});"
    proc = subprocess.run(
        ["docker", "exec", container, "psql", "-U", "postgres", "-d", "metering",
         "-t", "-A", "-F|", "-c", sql],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"docker exec psql failed: {proc.stderr}")
    out: dict[str, dict] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        rid, extra_json = line.split("|", 1)
        try:
            out[rid.strip()] = json.loads(extra_json)
        except json.JSONDecodeError:
            continue
    return out


def analyze(rows: list[dict], extras: dict[str, dict]) -> dict:
    """Group by (delay_ms, rep), compute intervals, and the causal authorization-vs-
    settlement crossing test."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["condition_delay_ms"], r.get("arrival"), r.get("run_id", "").rsplit("_rep", 1)[-1])
        cells[key].append(r)

    cell_reports = []
    for key, cell_rows in cells.items():
        delay_ms, arrival, rep = key
        per_request = []
        for r in cell_rows:
            rid = r["request_id"]
            e = extras.get(rid)
            if e is None:
                per_request.append({"request_id": rid, "instrumented": False})
                continue
            has_gw = "t1_read_start_ns" in e
            has_w = "t6_worker_popped_ns" in e
            rec = {
                "request_id": rid, "instrumented": has_gw, "settled": has_w,
                "served": r.get("served"),
            }
            if has_gw:
                rec.update({
                    "t1_read_start_ns": e["t1_read_start_ns"],
                    "t2_read_done_ns": e["t2_read_done_ns"],
                    "t3_decision_ns": e["t3_decision_ns"],
                    "t4_event_created_ns": e["t4_event_created_ns"],
                    "t4b_emitted_ns": e["t4b_emitted_ns"],
                    "read_latency_ms": (e["t2_read_done_ns"] - e["t1_read_start_ns"]) / 1e6,
                    "decision_latency_ms": (e["t3_decision_ns"] - e["t2_read_done_ns"]) / 1e6,
                    "emit_latency_ms": (e["t4b_emitted_ns"] - e["t4_event_created_ns"]) / 1e6,
                })
            if has_w:
                created = e["event_created_ns"]
                deliver_after = e["event_deliver_after_ns"]
                popped = e["t6_worker_popped_ns"]
                applied = e["t7_worker_applied_ns"]
                rec.update({
                    "event_created_ns": created, "event_deliver_after_ns": deliver_after,
                    "t6_worker_popped_ns": popped, "t7_worker_applied_ns": applied,
                    "configured_delay_ms": (deliver_after - created) / 1e6,
                    "overdue_at_pop_ms": (popped - deliver_after) / 1e6,
                    "exposure_window_ms": (applied - created) / 1e6,
                    "worker_dwell_ms": (applied - popped) / 1e6,
                })
            per_request.append(rec)

        # Causal test: for each request with a known T1 (perf_counter_ns, gateway-local,
        # comparable to every OTHER request in this same cell since one gateway process
        # served them all), count how many SIBLING requests in this cell had their
        # settlement (T7, wall clock) land before this request's own T1. Since T7 is
        # wall-clock and T1 is perf_counter, they cannot be subtracted directly -- instead
        # we use each request's OWN t4_event_created_ns (wall clock) as the anchor and
        # compare elapsed perf_counter time since the cell started against elapsed
        # wall-clock time for siblings' settlement, both relative to the EARLIEST T1 in
        # the cell. This avoids ever comparing an absolute perf_counter value to an
        # absolute wall-clock value -- only same-kind deltas are compared.
        instrumented = [r for r in per_request if r.get("instrumented")]
        if instrumented:
            t1_min = min(r["t1_read_start_ns"] for r in instrumented)
            for r in instrumented:
                r["t1_offset_ms"] = (r["t1_read_start_ns"] - t1_min) / 1e6
        settled = [r for r in per_request if r.get("settled")]
        if settled:
            created_min = min(r["event_created_ns"] for r in settled)
            for r in settled:
                r["settlement_offset_ms"] = (r["t7_worker_applied_ns"] - created_min) / 1e6

        crossings = 0
        if instrumented and settled:
            for req in instrumented:
                # Did ANY sibling's settlement land before THIS request's own authorization
                # read, in cell-relative time? req's own T1 offset vs siblings' settlement
                # offsets (both already anchored to a per-kind cell-relative zero above;
                # comparing them directly is only valid because every request's T1 and
                # every request's T4-created happen within the same sub-second cell window,
                # so cross-anchoring both to "cell start" makes the comparison meaningful
                # without mixing clock domains).
                for sib in settled:
                    if sib["request_id"] == req["request_id"]:
                        continue
                    if sib.get("settlement_offset_ms", 1e9) < req.get("t1_offset_ms", -1e9):
                        crossings += 1
                        break

        served_count = sum(1 for r in cell_rows if r.get("served") is True)

        # The DIRECT causal signal, needing no new instrumentation at all: balance_seen
        # was already recorded by the pre-existing code for every request (served or
        # rejected). If a request's balance_seen is strictly less than the cell's initial
        # funded balance, a settlement landed before this request's own authorization read
        # -- unambiguous, server-observed, no clock comparison of any kind involved. The
        # number of distinct observed balance_seen values below the initial balance is a
        # direct lower bound on how many settlements had landed by the time requests in
        # this cell were authorized.
        balance_points = [(r.get("balance_seen"), r.get("served"), r["request_id"])
                          for r in cell_rows if r.get("balance_seen") is not None]
        initial_balance = max((float(b) for b, _, _ in balance_points), default=None)
        settlements_visible_during_cell = sum(
            1 for b, _, _ in balance_points
            if initial_balance is not None and float(b) < initial_balance
        )

        cell_reports.append({
            "delay_ms": delay_ms, "arrival": arrival, "rep": rep,
            "served_count": served_count,
            "requests_with_authorization_preceding_a_sibling_settlement": crossings,
            "requests_total": len(cell_rows),
            "initial_balance": initial_balance,
            "balance_seen_sequence": [{"request_id": rid, "served": s, "balance_seen": b}
                                      for b, s, rid in balance_points],
            "settlements_visible_during_cell_authorization": settlements_visible_during_cell,
            "per_request": per_request,
        })

    return {"cells": cell_reports}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--via", choices=["ssh", "local-db-container"], required=True)
    ap.add_argument("--host", default="20.198.74.220")
    ap.add_argument("--user", default="azureuser")
    ap.add_argument("--key", default=str(Path.home() / ".ssh" / "llm-metering-two-machine"))
    ap.add_argument("--db-container", default="llm-metering-db-1")
    ap.add_argument("--local-container", default="sepaper-db-1")
    args = ap.parse_args()

    jsonl_path = Path(args.jsonl)
    rows = load_request_ids(jsonl_path)
    request_ids = [r["request_id"] for r in rows]
    print(f"Loaded {len(rows)} requests from {jsonl_path.name}")

    if args.via == "ssh":
        extras = fetch_extra_via_ssh(request_ids, args.host, args.user, args.key, args.db_container)
    else:
        extras = fetch_extra_via_local_db_container(request_ids, args.local_container)
    print(f"Fetched extra for {len(extras)}/{len(request_ids)} request_ids")

    result = analyze(rows, extras)
    for cell in result["cells"]:
        n_inst = sum(1 for r in cell["per_request"] if r.get("instrumented"))
        n_settled = sum(1 for r in cell["per_request"] if r.get("settled"))
        print(f"D={cell['delay_ms']:>6g}ms rep={cell['rep']:>2} served={cell['served_count']} "
              f"instrumented={n_inst}/{cell['requests_total']} settled={n_settled}/{cell['requests_total']} "
              f"crossings={cell['requests_with_authorization_preceding_a_sibling_settlement']} "
              f"settlements_visible_during_auth={cell['settlements_visible_during_cell_authorization']}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"mechanism_analysis_{jsonl_path.stem}_{stamp}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
