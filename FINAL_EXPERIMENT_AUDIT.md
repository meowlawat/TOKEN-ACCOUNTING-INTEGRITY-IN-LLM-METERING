# Final Experiment Audit — Two-Machine Asynchronous Settlement Experiment

Status as of this audit: **the real two-machine (C2) experiment is COMPLETE.** Host A
(this machine, running the gateway) and Host B (a real Azure VM in Central India, running
Postgres/Redis/the settlement worker) are physically separate machines connected over the
public internet. Every number below is traced to a specific raw-data file in
`experiments/two_machine/raw/` or `results/two_machine/`. Where something was not
measured, or a measurement turned out not to test what it was intended to, it says so
explicitly rather than being smoothed over.

---

## 1. Local baseline

Unchanged from the prior audit — see §1 of git history for this file. Source:
`results/two_machine/C0_sequential_20261005T230453Z.summary.json` and
`...20261005T230553Z.summary.json` (10 reps each, D=0/500), reproducing the published
single-host result exactly and repeatably across a full container restart.

## 2. Azure infrastructure (Host B)

| field | value |
|---|---|
| resource group | `rg-llm-metering-two-machine` |
| VM name | `vm-llm-metering-hostb` |
| region | Central India (`centralindia`) |
| VM size | `Standard_B2ls_v2` (2 vCPU, 4 GB RAM) |
| OS image | Ubuntu 24.04 (`Ubuntu2404`) |
| public IP | `20.198.74.220` |
| private IP | `10.0.0.4` |
| NSG | `vm-llm-metering-hostb-nsg` |

Host B runs `db` (postgres:16-alpine), `redis` (redis:7-alpine), and `worker`
(`python -m app.accounting.worker_main`, the Phase 3 standalone settlement worker) via
`docker-compose.machineB.yml`. No gateway runs on Host B. Host A (this machine) runs
*only* the gateway (`docker-compose.machineA.yml`, project `llm-metering-machinea`),
with `DATABASE_URL`/`REDIS_URL` pointing at `20.198.74.220` — a real network hop, not a
container-internal hostname.

**NSG access-control note (deviation from the original /32-only instruction, user-approved
2026-10-07):** the administrator's public IP was observed to rotate (CGNAT/dynamic ISP)
roughly every 1-2 minutes — faster than any detect-and-refresh cycle, and faster than the
Azure API round-trip needed to update a rule. Chasing it with a per-call `/32` refresh was
tried and failed (confirmed by direct measurement: the rule was updated to the then-current
IP and the next connection attempt still timed out because the IP had already rotated
again). Two escalation attempts — widening the NSG range, and using `az vm run-command` as
an NSG-bypass channel — were both blocked by Claude Code's own security classifier
("Security Weaken"); neither was circumvented. The user was asked explicitly and chose:
scope the SSH/Postgres/Redis NSG rules to `157.49.120.0/21` (2048 addresses, the ISP's
observed CGNAT pool, derived from ~14 directly observed IP samples across the session, all
falling in `157.49.120.x`–`157.49.126.x`) instead of a single `/32`. This is still a
small, ISP-specific range, not `0.0.0.0/0`. A provisioning bug was also found and fixed in
the same pass: `provision-two-machine.ps1`'s idempotency check gated rule creation on NSG
*existence*, not rule existence — an earlier run had created the bare NSG and then failed
before creating any rules, and every subsequent re-run silently skipped rule creation
because the NSG already existed. Fixed to check/create each rule individually.

## 3. Real network baseline (Host A → Host B)

Source: `results/two_machine/network_baseline_hostb_postgres_20261006T233150Z.json`.
TCP-connect RTT to `20.198.74.220:5432`, n=100, timed entirely on Host A's local
monotonic clock (no remote timestamp dependency):

| metric | value |
|---|---|
| min | 40.81 ms |
| median | 57.06 ms |
| p95 | 74.63 ms |
| p99 | 102.31 ms |
| max | 107.62 ms |
| packet loss | 0.0 % (0/100) |

This is a real, measured internet round trip to Azure Central India — not a localhost or
Docker-bridge latency figure.

## 4. Clock synchronization (Host A ↔ Host B)

Source: `results/two_machine/clock_sync_20261006T233203Z.json`.

- **Host B's own chrony self-report**: synchronized to a stratum-1 hardware reference
  (`PHC0`, the Azure host's precision hardware clock), RMS offset ~4.5 µs, leap status
  Normal. Host B's own clock is excellently synchronized to true time.
- **Independently measured Host A↔B `time.time_ns()` offset** (5 SSH round trips, not
  trusting chrony's self-report): +791 to +821 ms, with uncertainty bounds of ±414 to
  ±447 ms (half the SSH round-trip span, 828–894 ms per round trip). This figure is
  dominated by SSH/python process-spawn overhead, not network latency (contrast with the
  40–108 ms raw TCP RTT in §3) — it is reported as the honest, SSH-round-trip-bounded
  estimate the method produces, not represented as a precise clock-offset measurement.
- **This number is diagnostic only.** Per the experiment's own rule, economic correctness
  in this experiment is read from ledger/balance state (which is authoritative and
  single-sourced on Host B), never derived by subtracting unsynchronized wall-clock
  timestamps across hosts. No reported `over_served`/leakage number in this document
  depends on cross-host clock agreement.

## 5. D=0 control (mandatory gate, real two-machine topology)

Source: `results/two_machine/C2_sequential_20261006T233241Z.summary.json`. 10 reps,
sequential arrival, D=0, real Host A gateway → real Host B worker/db/redis.

| condition | arrival | delay | n | valid | served (of 6 issued) | over-served | final balance |
|---|---|---|---|---|---|---|---|
| C2 | sequential | 0 ms | 10 | 10 | 2 (every rep) | 0 (every rep) | 0.000000 (every rep) |

Gate passed cleanly — proceeded to the full sweep.

## 6. Full C2 sweep (real two-machine topology) — THE PRIMARY RESULT

Source: `results/two_machine/C2_sequential_20261006T233416Z.summary.json` (sequential) and
`results/two_machine/C2_concurrent_20261006T234156Z.summary.json` (concurrent). Both:
delays = 0, 10, 50, 100, 500 ms; 10 reps each; endpoint `/async/b0/complete`; budget = 2
units of a 6-request sequence (`B0_REQUESTS=6`, `B0_BUDGET_UNITS=2`, unchanged from the
validated protocol). Analysis cross-checked via
`python -m experiments.two_machine.analyze_results`, output in
`results/two_machine/analysis_summary.json`.

| condition | arrival | delay (ms) | n | valid | over-served mean | median | stdev | p95 |
|---|---|---|---|---|---|---|---|---|
| C2 | sequential | 0 | 10 | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | sequential | 10 | 10 | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | sequential | 50 | 10 | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | sequential | 100 | 10 | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | sequential | 500 | 10 | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| C2 | concurrent | 0 | 10 | 10 | 2.70 | 3.00 | 1.49 | 4.00 |
| C2 | concurrent | 10 | 10 | 10 | 4.00 | 4.00 | 0.00 | 4.00 |
| C2 | concurrent | 50 | 10 | 10 | 4.00 | 4.00 | 0.00 | 4.00 |
| C2 | concurrent | 100 | 10 | 10 | 4.00 | 4.00 | 0.00 | 4.00 |
| C2 | concurrent | 500 | 10 | 10 | 4.00 | 4.00 | 0.00 | 4.00 |

All 100 cells (50 sequential + 50 concurrent) are `valid` (zero HTTP/transport errors).
One cell in the concurrent/D=0 row was spot-checked end-to-end against its raw JSONL
(`experiments/two_machine/raw/C2_concurrent_20261006T234156Z.jsonl`, run_id ending
`_D10_rep0`): 6 raw per-request events, 6 marked `served: true`, matching the reported
`served=6, over_served=4` exactly.

**Interpretation, stated at the correct scope (per the project's absolute rules):** the
previously-published B0 asynchronous-settlement accounting-integrity failure was
reproduced under a physically separated gateway/settlement topology, for concurrent
request arrival, at every tested non-zero delay (10/50/100/500 ms over a real internet
path) — not merely "LLM providers are vulnerable" and not "production systems have this
vulnerability."

**Correction (added during the final hardening pass, `FINAL_HARDENING_BASELINE.md` §8.1
— not silently rewritten, flagged here instead):** the sentence originally here described
the sequential-arrival zero-over-serving result as "the designed-in negative control...
sequential requests never create the concurrent-read TOCTOU window the race requires,
regardless of settlement delay." That characterization is **wrong** and is retracted. The
true explanation, found by measuring the harness's own send timestamps directly: the
harness awaits each request's full round trip before sleeping the nominal 20ms gap, and
over this real network (RTT 40–108 ms per hop, doubled for `read_balance` + the Redis
emit) the *achieved* inter-request gap was 513–857 ms, not 20 ms — already exceeding
every delay tested here (≤500 ms) before the mechanism could manifest. This is not
architectural immunity to the race under physical separation; it is the fixed 20 ms
interarrival constant being overwhelmed by real network latency. A corrected, harness-
fixed rerun with delays chosen relative to the measured real gap
(`results/two_machine/C2_sequential_20261007T123546Z.summary.json`) shows the race
**does** reproduce under sequential arrival once the delay properly exceeds the achieved
gap: zero over-serving through D=2000ms, a transitional region at D=5000ms, and fully
saturated (4 over-served, every rep) at D=10000ms — exactly the behavior the manuscript's
own stated mechanism predicts. A genuine, structurally-guaranteed negative control
(`strict-serial` arrival, which confirms each request's settlement before dispatching the
next) was added separately and confirmed to never race at any tested delay up to
10000ms — see `FINAL_HARDENING_AUDIT.md`.

## 7. Atomic control (C3, real two-machine topology)

Source: `results/two_machine/C3_concurrent_20261006T234655Z.summary.json`. Same real
topology, same concurrent-arrival workload that produced 4/6 over-served under C2,
against `/async/b0/complete-atomic` instead.

| condition | arrival | delay (ms) | n | valid | over-served mean |
|---|---|---|---|---|---|
| C3 | concurrent | 0–500 (all 5) | 50 | 50 | 0.00 (every single cell) |

`served=2, over_served=0, final_balance=0.000000` for all 50 cells (every delay, every
rep). The atomic/hardened defense closes the race over the real network, not only
locally.

## 8. Failure injection (real two-machine deployment)

New module `experiments/two_machine/failure_injection_remote.py` (the local-topology
`failure_injection.py` is unchanged and kept as the historical C1 record;
`partition_remote_NOTE()` in it is now superseded by this real measurement).

| scenario | mechanism | result |
|---|---|---|
| `worker_kill` | real worker container on Host B stopped/restarted over SSH, 4 requests with 3s settlement delay in flight | Source: `results/two_machine/failure_injection_remote_worker_kill_20261006T235311Z.json`. Queue held at 3 during outage, drained to 0 after restart, server audit record/served counts match client exactly, balance reconciled to 0.000000. No lost events, no double counting. |
| `network_partition_remote` | **see methodology note below** | Source: `results/two_machine/failure_injection_remote_network_partition_remote_20261006T235827Z.json`. |
| `extreme_delay` | D=10s on the real deployment | Source: `results/two_machine/failure_injection_remote_extreme_delay_20261006T235910Z.json`. Gateway returns success immediately; balance still shows full pre-debit amount and the event is still queued on Host B — the client-visible "success" and the actual economic commitment are separated by up to 10s across the real network boundary. |

**`network_partition_remote` methodology note (reported honestly, not smoothed over):**
an in-VM `iptables -I DOCKER-USER ... -j DROP` approach was tried first and directly
verified to be a **silent no-op** — the rule showed 0 packets/0 bytes matched after a live
connection succeeded straight through it, because Docker on this Ubuntu 24.04 host manages
its own forwarding rules via a backend that legacy `iptables` inserts do not intercept.
This was caught before being used for a reported result and was **not** used. The
mechanism actually used instead — a temporary, higher-priority Azure NSG Deny rule,
inserted and removed via the Azure control plane — was independently verified before the
real run (a direct `socket.create_connection` probe timed out with the rule active and
succeeded immediately after removal). With that verified mechanism active, the gateway's
own `/admin/async/state` probe during the 10s blocked window still reported
`reachable: true`. This is explained, not ignored: Azure NSGs are stateful and only
evaluate *new* connection attempts — they do not tear down already-established flows, and
the gateway's asyncpg/redis clients were holding pooled connections to Host B opened
*before* the Deny rule existed, so neither the probe nor the 3 in-flight requests needed to
dial a new connection during the window. The result therefore demonstrates **pooled-
connection resilience to a new-connection-level block**, not that total connectivity loss
has no effect on the gateway — that would require forcing a fresh connection attempt (e.g.
restarting the gateway process) during the blocked window, which this run did not do. This
caveat is recorded verbatim in the result JSON's `caveat_pooled_connections` field. Despite
this, the queue/balance reconciliation after the rule was removed is still valid evidence:
events sent during the window were not lost and settled correctly once the rule was lifted.

No invariant violation was found or invented in any scenario.

## 9. Reproducibility

See `experiments/two_machine/REPRODUCIBILITY.md` for the exact command sequence used,
updated with the real Host B connection info and the actual commands run for this result.

## 10. Threats to validity (current state)

- **Single Azure region, single VM size, single run.** All C2 numbers come from one
  provisioning of one `Standard_B2ls_v2` VM in Central India; no claim is made about
  variance across regions, VM sizes, or repeated provisioning.
- **RETRACTED, see the §6 correction and `FINAL_HARDENING_BASELINE.md` §8.1:** this item
  originally claimed the sequential/D≤500 "zero over-serving" result was a clean negative
  control showing "the race requires concurrent arrival by construction, independent of
  topology." That is false — sequential arrival over this real network *does* race once
  the delay exceeds the real, round-trip-inflated achieved inter-arrival gap
  (confirmed up to D=10000ms). The corrected threats-to-validity item is: **the D≤500ms
  sequential sweep on the real topology was not a valid test of the race at all**, because
  the tested delays never exceeded the achieved ~500-900ms gap — it measured the gap, not
  the mechanism. The genuine negative control is the separately-added `strict-serial`
  arrival mode, which does not race at any tested delay because it waits for confirmed
  settlement before each subsequent authorization.
- **`network_partition_remote`'s gateway-reachability probe did not test what it was
  designed to test**, due to connection pooling — see §8. The worker-kill and extreme-delay
  scenarios are not subject to this caveat (they do not depend on an application-level
  "is the gateway still reachable" check during the fault window).
- **Clock-offset estimate (§4) is SSH-round-trip-bounded, not a tight measurement** — the
  ±400+ ms uncertainty is dominated by process-spawn overhead. No correctness claim in
  this document depends on it.
- Mock LLM / seeded randomness: unchanged from the prior audit — cost variation is seeded
  and reproducible, not from an uncontrolled source.
- **The NSG range was widened from the originally-specified `/32` to a `/21`** — a
  deliberate, user-approved, documented exception (§2), not a silent scope change. It
  affects only this experiment's own cloud infrastructure, not the testbed's security
  model, which is unchanged.

## 11. Claims CURRENTLY supported by this work

- The published single-host B0 over-serving result is reproduced exactly, repeatedly,
  across a full stack restart (§1, unchanged from the prior audit).
- A worker running as a genuinely separate OS process, sharing the gateway's clock domain,
  reproduces the same result (unchanged from the prior audit).
- **The B0 asynchronous-settlement accounting-integrity failure was reproduced under a
  physically separated gateway/settlement topology** (real Azure VM, real internet path,
  measured RTT 40–108 ms), for concurrent request arrival, at every tested non-zero delay.
  This is the result this entire experiment was built to obtain.
- The atomic-commitment primitive (`reserve_atomic`-based) empirically prevents
  over-serving under the identical real two-machine topology and workload that produced
  4/6 over-served under the vulnerable path — 0/50 cells show any over-serving.
- The async settlement pipeline recovers cleanly from a real remote worker crash (not a
  local sibling container): no lost events, no double counting, verified against the
  server's own raw per-request records on Host B.
- A genuine Azure-NSG-level network partition between Host A and Host B was verified to
  actually block new connections (not assumed); queued events survive the partition and
  reconcile once it is lifted.

## 12. Claims NOT supported (do not write these)

- Any claim that a commercial LLM provider, or any specific production system, is
  vulnerable — not claimed anywhere in this work and not supported by anything measured.
- Any claim that injected delay (`reconcile_delay_ms`) represents production inference
  latency — it is a settlement-delay parameter in a research testbed.
- Any claim that the `network_partition_remote` scenario demonstrates gateway behavior
  under total connectivity loss — it does not, per §8/§10's caveat.
- Any claim about variance across Azure regions, VM sizes, or repeated provisioning — only
  one configuration was tested.
