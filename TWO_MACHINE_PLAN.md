# Two-Machine Physical Distribution Experiment — Plan

Status: **PLAN ONLY. Nothing has been modified, no experiment has been run, and no
manuscript file has been touched.** Written from a read of the actual code at commit
`b60c37e`.

Research question: does the B0 accounting-integrity failure persist when the
authorization/gateway service and the accounting/settlement service run on physically
separate machines connected by a real network?

---

## 1. Current architecture, as implemented

### 1.1 How the existing asynchronous B0 experiment works

Driver: `experiments/run_async_accounting.py`, function `run_b0()`.

```
BASE                 = http://localhost:8000     (client -> gateway, same host)
DELAYS_MS            = [0, 10, 50, 100, 500]
B0_INTERARRIVAL_MS   = 20.0
B0_REQUESTS          = 6
budget               = 2 requests' worth of credit
WORKER_POLL_MS       = 2.0
over_served          = max(0, served - 2)
```

Per delay condition: reset the queue, start the worker, create an account funded for
exactly two requests, then issue 6 requests strictly sequentially with
`asyncio.sleep(20 ms)` between them, wait `max(0.4 s, 4 x delay)` for convergence, stop
the worker, read the final balance. Published result: over-served = 0, 0, 0, 1, 4 at
D = 0, 10, 50, 100, 500 ms.

### 1.2 The request path (`app/async_routes.py`, `POST /async/b0/complete`)

1. Authenticate, load trial, compute `cost`.
2. `balance = ledger.read_balance(session, account.id)` — a synchronous, committed read.
3. If `balance < cost`, refuse. **Otherwise serve.**
4. `ev = aw.new_event(..., delay_ms=req.reconcile_delay_ms)`; `_emit(...)` pushes JSON onto
   the Redis list `accounting:queue`.
5. Write an `MRecord` with `net_debit = 0`, `leak = authoritative`, `invariant_ok = False`.
   No debit exists yet at response time; that is the architecture, not a defect.

The authorization read and the economic commitment are therefore separated by the queue.
That separation is the whole mechanism under study.

### 1.3 The settlement worker — **runs inside the gateway process**

`app/async_routes.py::_worker_loop` is started by `POST /admin/async/worker/start` as
`asyncio.create_task(...)` on `app.state.async_worker_task`. It calls
`aw.drain(app.state.redis, apply_debit)`, and `apply_debit` opens `SessionLocal()` — the
gateway's own SQLAlchemy engine — and calls `ledger.debit_unchecked`.

**There is no standalone worker entrypoint anywhere in the repository.** Verified by
grep: `async_worker` / `_worker_loop` appear only in `app/async_routes.py`.

### 1.4 Component ownership today

| Component | Owner | Endpoint config |
|---|---|---|
| Client / driver | host process (`experiments/run_async_accounting.py`) | `BASE`, hardcoded `http://localhost:8000` |
| Gateway (FastAPI/uvicorn) | Docker container | — |
| Settlement worker | **same process as gateway** (asyncio task) | — |
| Redis (event queue) | Docker container | `REDIS_URL` env var |
| PostgreSQL (ledger) | Docker container | `DATABASE_URL` env var |

`DATABASE_URL` and `REDIS_URL` are read through `app/config.py` (pydantic settings,
`.env` + environment), so **repointing storage at another host is configuration, not
code**. `docker-compose.distributed.yml` already demonstrates two gateway containers
sharing one DB and one Redis.

### 1.5 Event transfer and correlation

`UsageEvent` (dataclass, JSON) carries `event_id` (uuid4), `request_id`, `trial_id`,
`account_id`, `delivered_tokens`, `amount`, `authoritative`, `created_ns`,
`deliver_after_ns`, `attempt`, `meta`. Transfer is `RPUSH` / `LPOP` on
`accounting:queue`. Idempotency is a Redis set `accounting:applied` keyed on `event_id`,
checked with `SISMEMBER` before applying. `request_id` is generated gateway-side and
written into both the event and the `MRecord`, so authorization, delivery and settlement
correlate on it.

### 1.6 How leakage is computed

Gateway writes `MRecord.net_debit = 0` and `leak = authoritative` at response time. The
debit lands later via `ledger.debit_unchecked`. For B0 the harness does not use `leak` at
all: it counts `served` and reports `over_served = max(0, served - 2)` plus the final
balance read from `/admin/async/balance/{id}`. Integrity is judged by over-serving against
a known budget, which is why the sequential design is sound — with a two-request budget,
any third served request is architectural over-serving.

---

## 2. Blocking findings — read before planning any run

### B-1. The worker cannot move hosts without a code change (**hard blocker**)

The worker is an asyncio task in the gateway process. Physically separating gateway from
settlement requires extracting `_worker_loop` + `apply_debit` into a standalone module
with its own `__main__`, its own engine and its own Redis client.

### B-2. `perf_counter_ns` is not comparable across processes or machines (**hard blocker, silent corruption risk**)

`async_worker.new_event()` sets both `created_ns` and `deliver_after_ns` from
`time.perf_counter_ns()`, and `drain()` gates on
`time.perf_counter_ns() < ev.deliver_after_ns`.

`perf_counter` is a monotonic clock with an **arbitrary, process-and-boot-local origin**
(QPC on Windows, `CLOCK_MONOTONIC` on Linux). Across two machines these values are
unrelated numbers. If the worker is moved as-is, the comparison becomes meaningless: the
worker will either apply every event immediately or never apply any, depending on which
host's counter happens to be larger.

This would not crash. It would silently produce a clean-looking table, and it could be
mistaken for "B0 disappeared under physical separation" (outcome B) or "B0 got much
worse". **This must be fixed before a single number is collected.** Fix: carry an epoch
timestamp (`time.time_ns()`) plus the delay, or have the worker compute its own due time
as `receive_time + delay_ms` and record the transport leg separately.

### B-3. Docker daemon is not running

`docker --version` reports 29.8.0, but the daemon is down (`dockerDesktopLinuxEngine`
pipe missing) and the `docker-desktop` WSL distro is `Stopped`. The entire testbed
(Postgres 16, Redis 7, gateway) is Docker Compose. Nothing can run until Docker Desktop is
started, which needs the interactive desktop session.

### B-4. There is no second machine currently available

Checked: no `gcloud`/`aws`/`az`/`doctl`/`multipass`/`vagrant`. VirtualBox 7.1.8 is
installed with exactly one VM, `kali-linux-2025.3-virtualbox-amd64`, currently **powered
off**, provisioning state unknown (Python version, Postgres, Redis, Docker, repo
checkout, network adapter mode all unverified). Bridged candidates seen: a Samsung USB
RNDIS tether (Up), Realtek GbE (Down), Hyper-V vEthernet (Up).

**A VirtualBox guest satisfies the brief's fallback clause** ("two genuine networked
hosts/VMs with separate network identities"): separate kernel, separate network stack,
separate IP, real TCP sockets, real serialization. It is **not** two physical machines and
**not** a real LAN path, so its transport latency will be sub-millisecond and must never be
described as LAN or cloud latency.

---

## 3. Proposed architecture

```
  Machine A (Windows host)                    Machine B (Kali VM, bridged adapter)
  ------------------------                    ------------------------------------
  experiments/run_two_machine.py   --HTTP-->   (none)
  FastAPI gateway (uvicorn)        --TCP--->   PostgreSQL 16   (ledger)
    authorization read             --TCP--->   Redis 7         (event queue)
    value delivery                              settlement worker  (standalone process)
    event emit                                    LPOP -> wait -> debit -> SADD applied
```

Machine A owns: client driver, gateway, authorization path, value delivery, event
emission. Machine B owns: Redis queue, PostgreSQL ledger, settlement worker. The worker
sits next to the store it writes, which is the realistic deployment and also keeps the
debit commit off Machine A entirely.

Control for B-4's honesty problem: the same experiment is also run **single-host** at the
same commit, so any difference is attributable to the split rather than to code changes
made for it.

---

## 4. Files requiring modification

| File | Change | Risk |
|---|---|---|
| `app/accounting/async_worker.py` | Replace `perf_counter_ns` with `time.time_ns()` in `new_event`; add `emitted_epoch_ns`; in `drain()`, gate on epoch time and record `received_epoch_ns`. Keep the existing single-host semantics identical. | **Touches a published artifact path.** Must be behind a flag or verified to reproduce the existing single-host numbers exactly. |
| `app/accounting/worker_main.py` | **New.** Standalone `python -m app.accounting.worker_main` running the drain loop against `REDIS_URL`/`DATABASE_URL`. | New file, additive. |
| `app/async_routes.py` | Leave `_worker_loop` intact for the existing experiment; no behaviour change. | None if untouched. |
| `experiments/run_two_machine.py` | **New.** Driver with configurable `BASE`, same constants (20 ms, 6 requests, budget 2), per-request JSONL logging of all timestamps. | New file, additive. |
| `docker-compose.machineA.yml`, `docker-compose.machineB.yml` | **New.** Split deployment. | New files, additive. |
| `experiments/summarize_two_machine.py` | **New.** Builds `two_machine_results.csv` + analysis tables. | New file, additive. |

Nothing in `paper/` is touched by this plan.

---

## 5. Exact measurement points

Recorded per request, raw, unrounded, in JSONL:

| Field | Clock | Where |
|---|---|---|
| `authorization_time` | A, epoch ns | gateway, immediately after `read_balance` returns |
| `settlement_send_time` | A, epoch ns | gateway, immediately before `RPUSH` |
| `accounting_receive_time` | B, epoch ns | worker, immediately after `LPOP` |
| `debit_commit_time` | B, epoch ns | worker, after `COMMIT` of `debit_unchecked` |
| `client_send_time`, `client_recv_time` | A, monotonic | driver, around the HTTP call |
| `value_delivered`, `net_committed_debit`, `leakage`, `final_integrity_status` | — | driver + `/admin/async/balance` |

Derived, and kept separate as the brief requires:

- **transport leg** = `accounting_receive_time − settlement_send_time` (cross-machine;
  reported with clock-offset uncertainty, never as a precise figure).
- **end-to-end settlement latency** = `debit_commit_time − authorization_time`.
- **configured delay** `D` — always reported as a separate column from both of the above.

**Clock discipline (brief §12).** Cross-machine differences are reported only with the
measured offset and its uncertainty. The primary, defensible latency number is measured
**entirely on Machine A**: a round-trip probe (`RPUSH` a sentinel, worker echoes, A reads
it back) giving transport RTT on one clock. Cross-machine event ordering is never claimed
from raw timestamps alone.

---

## 6. Experiment matrix

Primary, sequential (concurrency = 1, inter-arrival 20 ms, 6 requests, budget 2):
D ∈ {0, 5, 10, 20, 50, 100} ms, ≥30 repetitions per condition.

The brief's delay list differs from the published one ({0, 10, 50, 100, 500}). Both are
run: the brief's grid resolves the threshold near the 20 ms inter-arrival, and the
published grid keeps continuity with Table 7. Actual realized delays are recorded, not
assumed.

Optional secondary, only if the primary is stable: concurrency ∈ {1, 2, 5, 10}.

**Control condition (mandatory, brief §9):** D = 0 on the two-machine deployment. Must
show no over-serving, no duplicate settlement, no lost events, correct `request_id`
correlation, queue drained to zero. **If the control fails, stop and diagnose; do not
interpret any delayed condition.**

Failure taxonomy, kept separate in the logs and never folded into B0: transport failure
(connection reset, timeout), infrastructure failure (DB/Redis down, VM pause), clock
anomaly (offset drift beyond tolerance), implementation bug.

---

## 7. Rollback plan

1. All new code lands in **new files**; the only edit to an existing file is
   `async_worker.py`'s clock change.
2. Before touching it: `git stash`-clean tree, then a branch
   `two-machine-experiment`. `main` stays at `b60c37e`.
3. Regression gate: after the clock change, re-run `experiments/run_async_accounting.py`
   single-host and verify the published B0 row is reproduced exactly
   (over-served 0, 0, 0, 1, 4 at D = 0, 10, 50, 100, 500). **If it is not reproduced, the
   change is wrong — revert it, do not renumber the paper.**
4. If the experiment is abandoned: `git checkout main`, delete the branch. Manuscript and
   artifact are untouched, and the existing FGCS limitation paragraph stands as written.

---

## 8. Feasibility verdict

**Cannot proceed today without two decisions that are the author's, not mine.**

1. **Hardware.** Is there a real second machine on a LAN (preferred, and the only option
   that supports the phrase "real network")? If not, do you authorize the Kali VM with a
   bridged adapter, accepting that the result can only be described as separation across
   two OS instances and a real TCP/IP stack, never as LAN or cloud latency?
2. **Artifact change.** The clock fix (B-2) modifies a file in the released, DOI-archived
   artifact. That is a real change to published code and needs your approval, plus the
   regression gate in §7.3 before any result is believed.

Also required before any run: start Docker Desktop, and confirm the VM's provisioning
state and credentials if the VM route is chosen.

Until both decisions are made, the honest position is the one already in the manuscript:
separation is temporal, not physical, and a two-machine replication is the obvious next
experiment that has not been performed.
