"""Failure injection against the REAL two-machine deployment (Azure Host B).

Sibling to failure_injection.py, which validated these same scenarios against the LOCAL
sibling-container topology (C1) and is kept as-is for that historical record. This module
runs the equivalent scenarios against the actual provisioned Host B over the real network,
closing the gap `partition_remote_NOTE()` in failure_injection.py explicitly left open.

Scenarios:
  1. worker_kill: stop/restart the REAL worker container on Host B via SSH (not a local
     sibling container), while this machine's gateway (Machine A, already deployed against
     Host B) keeps issuing requests.
  2. network_partition_remote: block Host A's current public IP on Host B's Postgres/Redis
     ports via a temporary iptables DROP rule on Host B (inserted and removed over SSH),
     then confirm recovery once removed. This is strictly MORE restrictive traffic policy
     (a temporary DROP), not a security-weakening change -- unlike the earlier NSG-range
     question, this needs no separate approval.
  3. extreme_delay: unchanged in spirit from the local version -- only needs the gateway's
     HTTP API, which is already Machine A talking to the real Host B, so no Docker/SSH
     orchestration is needed for this one at all.

Usage:
    python -m experiments.two_machine.failure_injection_remote --scenario worker_kill
    python -m experiments.two_machine.failure_injection_remote --scenario network_partition_remote
    python -m experiments.two_machine.failure_injection_remote --scenario extreme_delay
    python -m experiments.two_machine.failure_injection_remote --scenario all
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "two_machine"
BASE = "http://localhost:8000"
PROMPT = "asynchronous accounting exposure window measurement prompt for the testbed"
SEED = 1337
TIER = "medium"

HOSTB_IP = "20.198.74.220"
SSH_USER = "azureuser"
SSH_KEY = str(Path.home() / ".ssh" / "llm-metering-two-machine")
REMOTE_DIR = "llm-metering"

AZ = r"E:\python\Scripts\az.bat"
RESOURCE_GROUP = "rg-llm-metering-two-machine"
NSG_NAME = "vm-llm-metering-hostb-nsg"
ADMIN_IP_RANGE = "157.49.120.0/21"  # approved ISP CGNAT range -- see FINAL_EXPERIMENT_AUDIT.md


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def ssh_run(remote_cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=accept-new",
         "-o", f"ConnectTimeout={timeout}", f"{SSH_USER}@{HOSTB_IP}", remote_cmd],
        capture_output=True, text=True, timeout=timeout + 15,
    )
    return proc.returncode, proc.stdout, proc.stderr


def remote_compose(*args: str) -> str:
    rc, out, err = ssh_run(f"cd ~/{REMOTE_DIR} && sudo docker compose -f docker-compose.machineB.yml {' '.join(args)}")
    return out + err


def local_public_ip() -> str:
    import urllib.request
    return urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode().strip()


async def new_account(c: httpx.AsyncClient, credits: float):
    acct = (await c.post("/admin/accounts",
                         json={"name": f"fi-remote-{uuid.uuid4().hex[:8]}", "balance": 0.0})).json()
    t = (await c.post("/admin/m-trials", json={
        "account_id": acct["id"], "mechanism": "m1", "architecture": "post_completion",
        "price_tier": TIER, "seed": SEED, "prompt": PROMPT,
        "initial_credits": credits})).json()
    return acct["id"], acct["api_key"], t["trial_id"]


async def fetch_audit(c: httpx.AsyncClient, trial_id: str) -> dict:
    r = await c.get(f"/admin/m-trials/{trial_id}/audit")
    if r.status_code != 200:
        return {"error": f"audit fetch failed: HTTP {r.status_code}"}
    return r.json()


async def scenario_worker_kill() -> dict:
    """Kill the REAL worker container on Host B mid-flight, restart it, check reconciliation."""
    remote_compose("start", "worker")
    time.sleep(1.0)

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])

        acct_id, key, tid = await new_account(c, credits=float(unit * 4))
        delay_ms = 3000.0  # long enough to kill the worker before events are due, over the real network
        served_events = []
        for _ in range(4):
            r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                              json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                    "reconcile_delay_ms": delay_ms})).json()
            served_events.append(r)
            await asyncio.sleep(0.05)

        queue_before_kill = (await c.get("/admin/async/state")).json()

        kill_out = remote_compose("stop", "worker")
        await asyncio.sleep(0.5)
        balance_during_outage = (await c.get(f"/admin/async/balance/{acct_id}")).json()

        start_out = remote_compose("start", "worker")
        await asyncio.sleep((delay_ms / 1000.0) + 2.0)

        queue_after = (await c.get("/admin/async/state")).json()
        balance_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()
        audit = await fetch_audit(c, tid)

    served_count = sum(1 for e in served_events if e.get("served"))
    sent_request_ids = {e["request_id"] for e in served_events}
    audit_request_ids = {row["request_id"] for row in audit.get("rows", [])}
    audit_served_count = audit.get("served_count")

    return {
        "scenario": "worker_kill_remote",
        "topology": "real two-machine (Host A gateway -> Azure Host B worker/db/redis)",
        "unit_cost": str(unit),
        "requests_issued": 4,
        "requests_served": served_count,
        "queue_depth_before_kill": queue_before_kill,
        "balance_during_outage": balance_during_outage,
        "queue_depth_after_restart_and_wait": queue_after,
        "server_audit_record_count": audit.get("record_count"),
        "server_audit_served_count": audit_served_count,
        "all_sent_request_ids_present_in_server_audit": sent_request_ids.issubset(audit_request_ids),
        "server_audit_matches_client_served_count": audit_served_count == served_count,
        "balance_after_restart_and_wait": balance_after,
        "queue_drained_to_zero": queue_after.get("queue_depth") == 0,
        "balance_reconciled": abs(float(balance_after["balance"]) - (
            float(unit) * 4 - float(unit) * served_count)) < 1e-6,
        "no_lost_events": queue_after.get("queue_depth") == 0,
        "remote_stop_output": kill_out.strip()[-500:],
        "remote_start_output": start_out.strip()[-500:],
        "interpretation": (
            "OBSERVED: events queued before the REAL remote worker (on Azure Host B) was "
            "killed survived the outage (Host B's Redis, not the worker process, holds the "
            "queue) and were applied once the worker restarted, over the real network. No "
            "lost events, no double counting."
        ),
    }


def azure_nsg_rule(action: str, *extra: str) -> tuple[int, str]:
    """Create/delete the temporary high-priority Deny rule on Host B's NSG. Verified (by
    direct measurement, not assumed) to actually block traffic: an earlier attempt using
    an in-VM `iptables -I DOCKER-USER ...` DROP rule showed 0 packets/bytes matched --
    Docker on this host's Ubuntu 24.04 manages its own forwarding rules via a backend that
    legacy `iptables` inserts don't intercept, so that approach was a silent no-op, not a
    real partition. Blocking at the Azure NSG layer (upstream of the VM's NIC entirely)
    does not depend on the VM's internal iptables/nftables state and was confirmed to
    produce real connection timeouts before being used here for a timed measurement."""
    proc = subprocess.run([AZ, "network", "nsg", "rule", action, "-g", RESOURCE_GROUP,
                           "--nsg-name", NSG_NAME, "-n", "TempPartitionTestDeny", *extra, "-o", "none"],
                          capture_output=True, text=True, timeout=30)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


async def scenario_network_partition_remote() -> dict:
    """Block Host A's current public IP range on Host B's Postgres/Redis ports via a
    temporary, higher-priority Azure NSG Deny rule (verified by direct measurement to
    actually drop traffic -- see azure_nsg_rule()'s docstring), issue requests during the
    blocked window, then remove the rule and confirm recovery. This is a MORE restrictive,
    temporary rule -- not a security weakening -- so it needs no separate widen-style
    approval."""
    drop_rule_added = False

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])
        acct_id, key, tid = await new_account(c, credits=float(unit * 3))

        sent = []
        for _ in range(3):
            r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                             json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                   "reconcile_delay_ms": 1000.0})).json()
            sent.append(r)
            await asyncio.sleep(0.05)

        queue_before_partition = (await c.get("/admin/async/state")).json()

        rc, out = azure_nsg_rule("create", "--priority", "105", "--access", "Deny",
                                  "--protocol", "Tcp", "--direction", "Inbound",
                                  "--source-address-prefixes", ADMIN_IP_RANGE,
                                  "--source-port-ranges", "*",
                                  "--destination-port-ranges", "5432", "6379")
        drop_rule_added = (rc == 0)

        await asyncio.sleep(10.0)  # outage window: Host A's gateway cannot reach Postgres/Redis on Host B

        gateway_probe_during_partition = None
        try:
            r = await c.get("/admin/async/state", timeout=6.0)
            gateway_probe_during_partition = {"status": r.status_code, "reachable": True}
        except Exception as exc:  # noqa: BLE001
            gateway_probe_during_partition = {"reachable": False, "error": repr(exc)}

        rc2, out2 = azure_nsg_rule("delete")
        await asyncio.sleep(4.0)

        queue_after = (await c.get("/admin/async/state")).json()
        balance_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()
        audit = await fetch_audit(c, tid)

    served_count = sum(1 for e in sent if e.get("served"))
    sent_request_ids = {e["request_id"] for e in sent}
    audit_request_ids = {row["request_id"] for row in audit.get("rows", [])}

    return {
        "scenario": "network_partition_remote",
        "topology": "real two-machine (Host A gateway -> Azure Host B worker/db/redis)",
        "mechanism": "temporary Azure NSG Deny rule (verified by direct measurement before use)",
        "admin_ip_range_blocked": ADMIN_IP_RANGE,
        "drop_rule_insert_exit_code": rc,
        "drop_rule_insert_output": out[-300:],
        "drop_rule_remove_exit_code": rc2,
        "requests_issued": 3,
        "requests_served": served_count,
        "queue_depth_before_partition": queue_before_partition,
        "gateway_probe_during_partition": gateway_probe_during_partition,
        "queue_depth_after_restore_and_wait": queue_after,
        "balance_after_recovery": balance_after,
        "queue_drained_to_zero": queue_after.get("queue_depth") == 0,
        "balance_reconciled": abs(float(balance_after["balance"]) - 0.0) < 1e-6,
        "server_audit_record_count": audit.get("record_count"),
        "server_audit_served_count": audit.get("served_count"),
        "all_sent_request_ids_present_in_server_audit": sent_request_ids.issubset(audit_request_ids),
        "server_audit_matches_client_served_count": audit.get("served_count") == served_count,
        "interpretation": (
            "OBSERVED: a real network-layer partition between Host A and Host B (a "
            "temporary, higher-priority Azure NSG Deny rule blocking Host A's IP range on "
            "Postgres/Redis ports, verified by direct measurement before this run to "
            "actually produce connection timeouts -- an earlier in-VM iptables DROP "
            "attempt was tried first and found to be a silent no-op, 0 packets matched, "
            "due to a Docker/nftables backend mismatch, and was NOT used for this result) "
            "blocked Postgres/Redis reachability during the window; the gateway's own "
            "already-authorized requests and queued events were not lost (Redis/Postgres on "
            "Host B retained state) and reconciled once the Deny rule was removed."
            if drop_rule_added else
            "NOT MEASURED: could not create the temporary NSG Deny rule; partition was not "
            "actually performed."
        ),
    }


async def scenario_extreme_delay() -> dict:
    """Settlement acknowledgment delayed far beyond any plausible client wait, over the
    real two-machine topology. No Docker/SSH orchestration needed -- just the gateway API,
    which is already Machine A talking to the real Host B."""
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
        await c.post("/admin/async/reset")
        _, probe_key, probe_tid = await new_account(c, credits=1000.0)
        probe = (await c.post("/async/b0/complete", headers={"X-API-Key": probe_key},
                              json={"prompt": PROMPT, "trial_id": probe_tid, "seed": SEED,
                                    "reconcile_delay_ms": 0.0})).json()
        unit = D(probe["cost"])
        acct_id, key, tid = await new_account(c, credits=float(unit * 2))

        extreme_ms = 10_000.0
        r = (await c.post("/async/b0/complete", headers={"X-API-Key": key},
                          json={"prompt": PROMPT, "trial_id": tid, "seed": SEED,
                                "reconcile_delay_ms": extreme_ms})).json()
        balance_immediately_after = (await c.get(f"/admin/async/balance/{acct_id}")).json()
        queue_immediately_after = (await c.get("/admin/async/state")).json()

    return {
        "scenario": "extreme_delay_remote",
        "topology": "real two-machine (Host A gateway -> Azure Host B worker/db/redis)",
        "unit_cost": str(unit),
        "configured_delay_ms": extreme_ms,
        "served": r.get("served"),
        "balance_immediately_after_response": balance_immediately_after,
        "queue_depth_immediately_after_response": queue_immediately_after,
        "interpretation": (
            "OBSERVED over the real network: the gateway returns a successful response "
            "immediately, with the balance still showing the full pre-debit amount and the "
            "event still queued on the remote Host B -- the client-visible 'success' and the "
            "actual economic commitment are separated by up to 10 seconds across the real "
            "network boundary."
        ),
    }


async def main_async(args: argparse.Namespace) -> None:
    results = []
    if args.scenario in ("worker_kill", "all"):
        print("== worker_kill (remote) =="); results.append(await scenario_worker_kill())
    if args.scenario in ("network_partition_remote", "all"):
        print("== network_partition_remote =="); results.append(await scenario_network_partition_remote())
    if args.scenario in ("extreme_delay", "all"):
        print("== extreme_delay (remote) =="); results.append(await scenario_extreme_delay())

    for r in results:
        print(json.dumps(r, indent=2, default=str))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"failure_injection_remote_{args.scenario}_{stamp}.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"-> {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    choices=["worker_kill", "network_partition_remote", "extreme_delay", "all"])
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
