# Two-Machine Distributed Experiment — Research Engineering Log

This log records major decisions, unexpected behavior, failed approaches, and why a
particular solution was chosen. It is part of the artifact, not scratch notes.

Branch: TBD (to be created before any existing file is touched — see Phase 3 entry).
Base commit at log start: `785bf80` (clean working tree).

---

## Provenance correction (binding on all future entries in this log)

The "single-host testbed... nothing here transfers" framing originates from
`paper/journal_reviewer_attack_v2.md`, a **self-authored adversarial red-team exercise**,
not an external reviewer's decision letter. No actual journal decision for this
manuscript has raised this specific objection. This log, and any later commit message,
report, or manuscript text produced from this work, must say "an anticipated concern" or
"a self-identified limitation," never "the reviewers said."

---

## 2026-10-04/05 — Phase 1: Code audit (reserve_atomic, B0, async B0)

**Finding 1 — `ledger.reserve_atomic()` is NOT used by B0 at all.**
Grep confirms `reserve_atomic` has exactly one caller in the entire repo:
`app/m_routes.py:212`, part of the M1/M2 mechanism routes. B0 (synchronous and async) has
its own, separate, independently-implemented atomic primitive. My own first-pass summary
(delivered to the user before this audit) assumed B0-hardened reused
`ledger.reserve_atomic()` — that assumption was **wrong** and is corrected here rather than
carried forward silently.

**Finding 2 — exact atomicity provided by each primitive, read from source:**

- `ledger.reserve_atomic()` (`app/accounting/ledger.py:69-71` → `app/accounting/backends.py`):
  - `mutable` backend: single statement `UPDATE credits SET balance = balance - :c WHERE
    account_id = :a AND balance >= :c RETURNING balance`. Atomic because it is one
    row-locked statement; Postgres serializes concurrent UPDATEs on the same row.
  - `ledger` backend: `SELECT account_id FROM credits WHERE account_id = :a FOR UPDATE`
    (anchor-row lock) → read derived balance → conditional `INSERT INTO ledger_entries`.
    Atomic because the FOR UPDATE lock on the anchor row serializes all reservers against
    that account; the balance read in between is safe only because no other reserver can
    acquire the same lock until this transaction commits or rolls back.
  - Used only by M1/M2 (`m_routes.py`), both backends. Not used by B0.

- B0's real atomic primitive is `app/metering/debit.py::reserve_hardened()`:
  single statement `UPDATE credits SET balance = balance - :c WHERE account_id = :a AND
  balance >= :c RETURNING balance` — same SQL shape as the mutable `reserve_atomic`, but
  implemented independently and scoped to the mutable backend only (raw SQL against
  `credits`, no backend dispatch). Caller (`app/main.py::_complete_hardened`, line 636)
  commits **immediately** after the reserve, before streaming — verified by reading the
  caller, not assumed from the docstring's claim ("Commit the reserve immediately so the
  row lock is not held during streaming" — confirmed true).
  `refund_hardened()` is called on any exception during streaming (main.py:642), so a
  failed/aborted response is refunded. B0-vulnerable (`debit_stale_absolute`) does a
  lock-free read, streams, then writes a stale absolute value under a `FOR UPDATE` lock
  taken only at write time — the lock observes the true pre-image but the written value
  still derives from the stale pre-stream read, which is the lost-update bug by
  construction (confirmed by reading `app/metering/debit.py` and its caller
  `_complete_vulnerable`, main.py:565-619).

**Finding 3 — async B0 (`/async/b0/complete`, `app/async_routes.py:186-240`) uses neither
primitive.** It calls `ledger.read_balance()` (lock-free, backend-dispatched) to authorize,
serves unconditionally if sufficient, then queues a `UsageEvent` whose debit is applied
later by the worker via `ledger.debit_unchecked()` (also lock-free, backend-dispatched,
no WHERE-balance-check at all). This is, by design, the architecture under study: the
exposure window exists because authorization and commitment are not coupled, regardless of
backend. There is currently no "atomic async B0" path in the repository.

**Implication for C3 design (not yet implemented):** the natural, minimal C3 is NOT
"reserve provisionally, finalize later" (that is M1's pattern, needed because M1's final
cost is completion-dependent). B0's cost is fully known at authorization time, so coupling
authorization to commitment for B0 means calling a `reserve_hardened`-equivalent atomic
UPDATE synchronously at authorization time — the debit is already final the moment the
request is authorized, on whichever host runs the gateway. Any event still emitted to the
async queue in C3 would carry no further balance mutation (audit/observability only, or
omitted entirely). This needs to be built as a genuinely new code path, not a reuse of an
existing unused primitive — correcting the over-optimistic framing in the pre-audit report.

**Finding 4 — idempotency has no DB-level backstop.** `UsageRecord.request_id` and the
async pipeline's `event_id` are indexed, not unique-constrained, at the database level.
Duplicate-delivery safety for the async path currently rests entirely on the Redis
`accounting:applied` SET (`SISMEMBER` check in `async_worker.py::drain`). If that set were
ever lost or reset while an event could still be redelivered, nothing at the SQL layer
would prevent a double debit. Relevant to Phase 8 (failure injection) design, and to be
treated as a known property of the current architecture, not fixed silently as part of
this work unless failure-injection results show it matters for H1-H3.

**Finding 5 — isolation level confirmed live**, not assumed: `GET /admin/db-info` on the
running stack returns `"transaction_isolation":"read committed"`, matching
`app/db.py`'s default (no isolation-level override in `create_async_engine`). Each request
handler gets its own `AsyncSession`/pooled connection (`app/db.py:33-36`), which is what
makes B0-vulnerable's race observable across concurrent handlers in the first place.

---

## 2026-10-05 — Phase 2: Published baseline regression

Docker Desktop was not running at session start (confirmed: no process, no
`com.docker.service`; found the actual install under
`C:\Users\hardi\AppData\Local\Programs\DockerDesktop`, not the default `Program Files`
path). Started it, waited for the daemon, confirmed with `docker ps`.

`git log` confirms `app/accounting/async_worker.py`, `app/async_routes.py`, and
`experiments/run_async_accounting.py` have had exactly **one** commit each since they were
introduced (`7bc1993`), and zero commits since. The working tree was clean (no
modifications) at the time of this run. This is the strongest possible precondition for a
reproduction: the code is byte-identical to whatever produced the originally published
numbers.

Ran, verbatim, no flags changed:
```
python -m experiments.run_async_accounting --reps 5
```
Output written to `results/raw/async_accounting_20261004T214010Z.json`.

**B0 result (the row that matters):**

| D (ms) | issued | served | over-served | final balance |
|---|---|---|---|---|
| 0   | 6 | 2 | 0 | 0.000000  |
| 10  | 6 | 2 | 0 | 0.000000  |
| 50  | 6 | 2 | 0 | 0.000000  |
| 100 | 6 | 3 | 1 | -0.081000 |
| 500 | 6 | 6 | 4 | -0.324000 |

**Exact match** to the published row (0, 0, 0, 1, 4) and to the published final balances.
No nondeterminism observed on this run; reproducibility envelope not yet characterized
across multiple repeated runs (only one baseline run performed so far — sufficient to
clear the Phase 2 gate per the stated instruction, but a multi-run reproducibility
envelope should still be established before the full experiment, not assumed from one
pass).

**Corroborating evidence the pipeline is otherwise unchanged:** M2 leakage efficiency
measured as `+0.5823` identically at D = 0, 100, 500 ms — exactly matching the prediction
that asynchrony does not change M2 (billed amount is a pure function of one request's
declared usage, computed independent of when the balance is read).

**Verdict: Phase 2 gate PASSED.** Proceeding to Phase 3 (worker extraction, same host).

---

## 2026-10-05 — Phase 3: Worker extraction

**Branch created:** `two-machine-experiment`, off `785bf80` (clean tree at branch point).

**New file:** `app/accounting/worker_main.py` -- standalone entrypoint running the same
`aw.drain(redis, apply_debit)` loop as `_worker_loop` in `async_routes.py`, verified
line-by-line against it. One behavioral addition beyond what `_worker_loop` does:
explicitly calls `ledger.configure(redis_client)`, because a standalone process has no
shared `app.state` with the gateway and would otherwise silently default to the
"mutable" backend regardless of which backend the gateway actually has selected
(`_worker_loop` gets this for free since it shares the gateway's already-configured
Redis client). `async_routes.py` itself was not touched.

**New file:** `experiments/two_machine/pilot_same_host_external_worker.py` -- copies the
B0 sequential-arrival protocol from `run_async_accounting.py::run_b0()` as closely as
possible, but starts/stops the standalone `worker_main.py` as a subprocess instead of
calling the gateway's `/admin/async/worker/start`/`stop`. Includes a guard that refuses
to run if the gateway's own worker task is already active, so the control can't
accidentally be drained by both workers at once.

**Bug found and fixed in my own pilot script, not in the system under test:** first draft
called `new_account(..., mechanism="b0", architecture="async_b0")`. `/admin/m-trials`
validates `mechanism` against `^(m1|m2)$` and returned HTTP 422 for `"b0"`. The published
driver (`run_async_accounting.py::run_b0`) actually calls `new_account(c, credits=...)`
with **no override**, so B0 trials are labeled `m1`/`post_completion` in `MTrial` -- the
trial's `mechanism` field is bookkeeping metadata only; which endpoint is called
(`/async/b0/complete` vs `/async/m1/stream`) is what actually selects B0 vs. M1 behavior.
I had "improved" this to look more semantically correct and broke it. Fixed by matching
the published driver's call exactly, with a comment explaining why the apparent mismatch
is intentional. Recorded here per the instruction to document failed approaches, not just
successes.

### Attempt 1 — FAILED (dependency missing)

Ran the fixed pilot. Worker subprocess crashed immediately: `ModuleNotFoundError: No
module named 'redis'`. Cause: `subprocess.Popen([sys.executable, ...])` used the host
Windows Python, which has none of the app's dependencies -- only the Docker image does.
Fixed by installing the minimal runtime dependency subset (`sqlalchemy[asyncio]`,
`asyncpg`, `redis`, `pydantic`, `pydantic-settings`, `python-dotenv`) into the host
Python. This is itself informative: it is the simplest possible model of what "Machine B"
will need later -- just those packages, not the full FastAPI/tokenizer stack.

### Attempt 2 — FAILED (host/container port collision)

Worker started cleanly but every `drain()` pass failed: `password authentication failed
for user "postgres"`. Checked `Get-NetTCPConnection -LocalPort 5432` and found **two**
listeners on this machine: Docker's backend (expected) and a **native PostgreSQL service
already installed on this machine** (`postgres.exe`), both bound to port 5432 on
different address families (`::` vs `0.0.0.0`). A host-side process connecting to
"localhost:5432" can resolve to either, and in this case hit the native instance, which
naturally doesn't have this project's credentials/database. Port 6379 has the same
problem with a second listener (`wslrelay.exe`). The gateway container itself was never
affected, because it reaches Postgres/Redis via the Docker-internal hostnames `db`/`redis`,
not `localhost`.

**Fix:** `docker-compose.override.yml` (git-ignored, local-only, does not touch the
tracked `docker-compose.yml`) remaps only the HOST side of the port mappings to
15432/16379. Container-internal addressing (`db:5432`, `redis:6379`) is untouched, so the
already-reproduced Phase 2 baseline is unaffected. Verified both remapped ports reachable
with the project's actual credentials before re-running.

### Attempt 3 — FAILED (own-induced cold-start race, not a true result)

With correct dependencies and ports, debits finally applied -- but the over-served pattern
was incoherent (3, 3, 4, 2, 2 at D = 0, 10, 50, 100, 500 ms) and did not track delay at
all, worse at small D than the published baseline and *better* at D=500 than expected.
Root cause: the pilot restarted the worker as a **fresh cold Python subprocess for every
delay condition**, with only a fixed `time.sleep(0.3)` guess before assuming it was ready.
Process startup + import + DB/Redis connection took an uncontrolled, variable amount of
time competing directly with the 120 ms (6 x 20 ms) request window being measured --
the test was measuring "how fast does a cold-started process become ready," not the
reconciliation delay. This is a confound in my own test harness, not a property of the
system under test, and would have been a bad place to stop.

**Fix:** restructured so the worker process starts **once**, before the delay sweep, and
the harness waits for an explicit readiness signal (the worker's own "worker starting"
log line, read from its stdout on a background-thread pump) with a timeout, rather than a
fixed sleep. The worker then stays up across all five delay conditions and is stopped
once at the end -- which also matches how a real deployed worker would actually run.
Also switched from buffering all subprocess output until the end to continuously draining
stdout on a background thread, because a long-running process logging every pass
(`--stats-every 1`) can fill the OS pipe buffer and block if nothing reads it.

### Attempt 4 — FAILED, and this failure is itself a real, reportable finding

With a persistent, readiness-confirmed worker: D=0,10,50 correctly showed 0 over-served
(matching published), but D=100 and D=500 **also** showed 0 over-served (published: 1 and
4). The worker was settling every request instantly regardless of the requested
`reconcile_delay_ms`.

**Diagnosed, not patched around.** Compared `time.perf_counter_ns()` read directly in the
host Windows process against the same call read inside the gateway's own Linux container
(`docker compose exec app python -c "import time; print(time.perf_counter_ns())"`):

```
host (Windows, native python):               80,933,361,348,800 ns  (~22.5 h uptime)
gateway container (Linux, Docker Desktop VM):     779,459,102,694 ns  (~13 min uptime)
```

The host's counter is ~104x larger than the container's, because Docker Desktop on
Windows runs containers inside its own Linux VM (WSL2) with an independent boot time --
not the same clock domain as the Windows host at all. `new_event()` computes
`deliver_after_ns` from the **container's** `perf_counter_ns()` (it runs inside the
gateway); the worker's `drain()`, running as a **host** process, compared that value
against the **host's** `perf_counter_ns()`. Since the host counter is always far larger
than any container-origin `deliver_after_ns`, `time.perf_counter_ns() < ev.deliver_after_ns`
evaluates `False` immediately for every event, regardless of the configured delay -- so
the external worker always treated every event as instantly due.

**This is exactly the B-2 risk the plan anticipated for genuine physical separation, but
it surfaced one step earlier than expected: even "same machine" is not one clock domain
once the worker leaves the gateway's container**, because of how Docker Desktop on
Windows is architected. This is a real, useful result in its own right (not something to
bury): it is direct empirical proof that B-2 is not a theoretical risk -- it reproduces on
demand, deterministically, the moment the worker and gateway are not the same OS process.

**Fix for Phase 3 specifically (old clock, same host, per the phase's own constraint):**
run the standalone worker inside a sibling container that shares the gateway's Docker
network and therefore its Linux VM's clock domain, instead of as a bare Windows host
process. This is still "old clock, unmodified `async_worker.py`" -- it changes *where the
worker's OS process lives*, not the clock source -- so it still respects the Phase 3/Phase
4 ordering the brief requires. The actual clock fix (Phase 4) remains necessary before any
*real* cross-machine deployment (Phase 5), where this exact failure mode will recur in its
intended, serious form.

New service added to `docker-compose.override.yml`: `worker` (same image as `app`,
command overridden to `python -m app.accounting.worker_main`, internal `db`/`redis`
hostnames, gated behind `profiles: ["two-machine-pilot"]` so a plain `docker compose up`
-- what anyone reproducing the published baseline would run -- never starts it).
`experiments/two_machine/pilot_same_host_external_worker.py` rewritten to control this
container via `docker compose up/stop/logs` instead of a bare `subprocess.Popen`.

### Attempt 5 — PASSED

```
    delay  issued  served  affordable  over-served   final bal
       0ms       6       2           2            0    0.000000
      10ms       6       2           2            0    0.000000
      50ms       6       2           2            0    0.000000
     100ms       6       3           2            1   -0.081000
     500ms       6       6           2            4   -0.324000
```

Exact match to the published row, both `over_served` and `final_balance`. Output:
`results/two_machine/pilot_same_host_external_worker_20261004T215152Z.json`.

**Verdict: Phase 3 gate PASSED.** The worker extraction itself, run in a clock-domain-
compatible environment, is behavior-preserving. "We changed the worker" and "physical
distribution changed the behavior" are now cleanly separated, as the phase requires.
Proceeding to Phase 4 (clock change), which does not require external infrastructure the
user must provide -- Phase 5 (actual cloud VM) is where this work will pause for the
user's hardware/account decision.

---

## 2026-10-05 — Phase 4: Clock change

**Minimum safe change, as prescribed:** in `app/accounting/async_worker.py`, replaced
`time.perf_counter_ns()` with `time.time_ns()` in exactly three places --
`new_event()`'s `now` (origin for both `created_ns` and `deliver_after_ns`), `drain()`'s
due-check (`time.time_ns() < ev.deliver_after_ns`), and `drain()`'s exposure-window
calculation. Field names (`created_ns`, `deliver_after_ns`) are unchanged; only the clock
source changed, to keep the diff minimal and the public shape of `UsageEvent` stable.
Added a long docstring comment explaining why, with the concrete numbers from the Phase 3
attempt-4 diagnosis, so a future reader does not "fix" this back to perf_counter without
re-deriving why it was wrong. `app/async_routes.py` was not touched -- its own
`perf_counter_ns()` uses (`stream_start_ns`, `emitted_ns` in the M1 state dict) are set and
read within the same gateway process only, never compared across a process boundary, so
they are unaffected by and irrelevant to this fix.

Rebuilt both images that share this code (`sepaper-app` and `sepaper-worker` are, it turns
out, two *separate* images despite both being `build: .` with no explicit `image:` key --
confirmed via `docker images`, both needed an explicit rebuild).

**Regression, run twice:**
1. Plain `python -m experiments.run_async_accounting --reps 5` (gateway's own in-process
   worker, unmodified `_worker_loop`): over_served = [0, 0, 0, 1, 4], balances unchanged.
   Exact match.
2. `pilot_same_host_external_worker` (sibling-container worker): over_served =
   [0, 0, 0, 1, 4], balances unchanged. Exact match.

**Verdict: Phase 4 gate PASSED.** The clock change is behavior-preserving on every
same-host configuration tested so far.

**Additional finding, directly relevant to Phase 5's chrony requirement, not skipped:**
compared `time.time_ns()` directly between the host and the gateway's Linux container the
same way the perf_counter_ns() mismatch was diagnosed:

```
host (Windows):                       1,791,150,879,195,763,800 ns
gateway container (Docker Linux VM):  1,791,150,879,499,225,336 ns
difference:                           ~303,461,536 ns  (~303 ms)
```

This is vastly smaller and bounded compared to the ~104x perf_counter_ns mismatch -- the
fix genuinely works -- but 303 ms of host/VM clock drift is **larger than three of the
five configured delay conditions** (0, 10, 50 ms). This is a Docker-Desktop-on-Windows-
specific artifact (the Linux VM's clock can drift from the Windows host, particularly
after sleep/resume), not a property of the real Phase 5 deployment, but it is concrete,
quantified proof of exactly why the brief's chrony/offset-measurement requirement for
Phase 5 is not optional box-ticking: an unmeasured few-hundred-millisecond clock offset
would silently corrupt every small-delay cell of the experiment matrix. This machine's own
host-vs-container drift will not be the number that matters for the real cloud deployment
(a fresh, independent clock-offset measurement against the actual cloud VM is required
there, per Phase 5's own instructions), but it is the clearest concrete illustration found
so far of why that measurement matters.

---

## Phase 5 — NOT STARTED: requires the user

Phases 1-4 are complete, gated, and logged above. Phase 5 (provisioning a real cloud VM in
Mumbai/Hyderabad for Host B) requires an actual cloud account, a payment method, and a
provider/region/instance-type choice -- none of which I can create or authorize on the
user's behalf. This is the stopping point the user's own instructions anticipated
("When blocked by missing external infrastructure, tell me exactly what is required").
See the chat response for the precise information needed to proceed.
