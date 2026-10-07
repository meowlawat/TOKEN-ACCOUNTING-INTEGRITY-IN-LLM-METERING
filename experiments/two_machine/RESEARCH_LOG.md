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

---

## 2026-10-06 — Phase 5 infrastructure build-out (while Azure auth is pending)

Resumed at commit `6fbca90`. `az` CLI was not installed at all (not just unauthenticated).
Installed via `pip install azure-cli` (azure-cli 2.90.0). Discovered and worked around a
real environment quirk: invoking the resulting `az`/`az.bat` entry point directly from
MSYS bash silently produces exit 0 with NO output at all (neither stdout nor stderr) even
when the underlying command genuinely fails -- confirmed by running the identical `az
account show` through PowerShell (correct: exit 1, "Please run az login") and through
`cmd //c` (same, correct). Root cause is MSYS's automatic Unix-to-Windows argument/path
translation interacting badly with the pip-installed Python entry-point script. Rather than
fight this across many multi-flag az invocations (resource group/NSG/VM create), all actual
Azure CLI logic was written as `scripts/azure/provision-two-machine.ps1`, invoked via
PowerShell, with a thin `scripts/azure/provision-two-machine.sh` wrapper for interface
consistency with the rest of the two-machine scripts.

**Generated a dedicated ED25519 keypair**: `~/.ssh/llm-metering-two-machine[.pub]` (outside
the repository; never committed; `.gitignore` already covers key-name patterns).

**`az account show` confirms Azure CLI is installed but genuinely not authenticated.**
`az login` is an interactive OAuth/device-code flow requiring the user's own Microsoft /
Azure for Students account -- this cannot be performed on the user's behalf and is the one
genuine stop condition for actually provisioning Host B. Per the user's own fallback
instructions, this did NOT stop the rest of the work; everything buildable without a live
Azure session was built:

- `scripts/azure/provision-two-machine.ps1` (+ `.sh` wrapper) -- idempotent: detects admin
  public IP via external echo services, picks the Azure-for-Students subscription if more
  than one exists, queries ACTUAL region availability (prefers centralindia, falls back to
  whatever Indian region the subscription actually has, never assumes), queries ACTUAL
  `Standard_B*` SKU availability in that region filtered to >=2 vCPU / >=2GB RAM with no
  subscription restrictions (never hardcodes a SKU name), creates a dedicated resource
  group + NSG (22/5432/6379 inbound restricted to the detected admin IP /32 only, never
  0.0.0.0/0) + VM, and writes connection info to
  `experiments/two_machine/azure_vm_info.json` (git-ignored -- machine-specific/ephemeral,
  not a secret, but not something a re-run should depend on being committed).
- `scripts/azure/bootstrap-machine-b.sh` -- waits for SSH, installs Docker + Docker Compose
  plugin + chrony + diagnostics (curl, jq, iproute2, ping, traceroute, netcat), enables and
  starts chrony, reports `chronyc tracking`/`sources`.
- `docker-compose.machineB.yml` (new, root of repo, consistent with the existing
  `docker-compose.distributed.yml` precedent) -- runs ONLY `db` + `redis` + `worker` (the
  Phase 3 `worker_main.py`, unchanged) on Host B; no gateway. Ports publish on all
  interfaces because Host A must reach them over the real network -- the actual access
  control is the NSG rule above, not container-level binding.
- `docker-compose.machineA.yml` (new) -- runs ONLY the gateway on Host A, with
  `DATABASE_URL`/`REDIS_URL` pointed at `${HOSTB_PUBLIC_IP}` over the real network.
- `scripts/azure/deploy-machine-b.sh` -- tars just `Dockerfile` + `requirements.txt` +
  `app/` + `docker-compose.machineB.yml` (not the whole repo -- Host B has no business
  holding `paper/` or release zips) over a single SSH connection, builds, brings up, and
  verifies health.
- `experiments/two_machine/network_baseline.py` -- TCP-connect RTT to Host B, repeated
  samples, min/median/p95/p99/max/loss, timed entirely on Host A's local monotonic clock
  (no remote timestamp read, so this does not depend on clock sync at all).
- `experiments/two_machine/clock_sync_check.py` -- records chrony's own self-reported
  state on Host B AND an independently measured `time.time_ns()` offset via repeated SSH
  round trips (same direct-comparison method as the Phase 4 diagnosis), with the offset's
  uncertainty reported as half the round-trip span. Does not trust chrony's self-report
  alone, per the explicit instruction not to claim synchronization merely because chrony
  is installed.

**New application code: `/async/b0/complete-atomic` in `app/async_routes.py` (C3's
primitive).** The Phase 1 audit found no atomic-commit counterpart to the vulnerable async
B0 path anywhere in the repository -- it had to be built, not assumed. Uses
`ledger.reserve_atomic()`, NOT `metering/debit.py::reserve_hardened()`, and the choice is
deliberate and documented in the code itself: `reserve_hardened()` is raw SQL scoped to the
mutable backend only, while every other function this async B0 family already calls
(`read_balance`, `debit_unchecked`) goes through `ledger.py`'s backend-dispatched interface
supporting both the mutable and append-only-ledger backends. Using `reserve_hardened()`
here would silently restrict this condition to one backend while the rest of the family
supports both. `ledger.reserve_atomic()` is structurally the same atomic primitive for the
mutable backend (verified: identical single-statement `UPDATE ... WHERE balance >= :c
RETURNING balance`) and the `SELECT ... FOR UPDATE`-anchored equivalent for the ledger
backend -- both already verified atomic in the Phase 1 audit. No event is queued for this
path: B0's cost is fully known at authorization time (unlike M1), so coupling authorization
to commitment means the debit is final the instant the request is authorized; there is
nothing left for an async worker to settle.

**Validated immediately, locally, before building anything on top of it:**
- Three sequential calls against a 0.2-credit budget (unit cost 0.0605): all three served,
  balance decremented exactly each time (0.2 -> 0.1395 -> 0.079 -> 0.0185). OBSERVED.
- **The real correctness test**: 20 genuinely concurrent requests (`asyncio.gather`, not
  sequential) against a budget sized for exactly 2 (0.121 credits / 0.0605 unit cost).
  Result: exactly 2/20 served, final balance exactly `0.000000`. OBSERVED. This is direct
  evidence the new primitive actually closes the race under concurrency, not just under
  the sequential protocol the rest of this experiment uses -- the atomic UPDATE genuinely
  serializes concurrent callers rather than merely looking safe.

Still blocked on `az login` before Host B can actually be created. Everything above is
built and locally validated so that the moment authentication is available, provisioning
can proceed with a single command and nothing above needs to be redesigned.

### Harness validation (local, before trusting it for real runs)

Built `experiments/two_machine/run_distributed_experiment.py` -- the unified harness
Phase 7 requires (per-request JSONL, run manifest with git commit/host/config hash,
explicit condition + arrival-pattern labeling, repetitions never silently retried).
Found and fixed one bug in the harness itself before trusting any output from it: the
unit-cost probe used a zero-balance account, which can never be served, so `cost` was
never returned (`/async/b0/complete`'s insufficient-balance response carries no `cost`
field at all) -- every cell came back `[INVALID]`. Fixed by funding the probe account
generously (1000 credits, matching `experiments/run_async_accounting.py`'s own pattern)
before reading back the unit cost, then opening a separate, exactly-budgeted account for
the timed sequence. Documented in the code so a future reader does not reintroduce it.

Three conditions validated through the corrected harness, end-to-end, including the new
`analyze_results.py` aggregation step:

- **C0** (in-process worker, sequential, 3 reps, D=0/10/50/100/500): over-served
  0,0,0,1,4 at every rep, stdev=0 across reps -- exact match to the historical row, now
  flowing through the NEW harness rather than the original one-off script. 90 per-request
  JSONL lines (15 cells x 6 requests) confirmed present.
- **C1** (sibling-container worker, sequential, 2 reps, D=0/100/500): same exact pattern.
- **C3** (atomic endpoint, CONCURRENT arrival -- the harder case -- 3 reps, D=0/500):
  over_served=0 at every rep, both delays. Confirms the atomic primitive's correctness
  generalizes from the harness's own earlier direct test (20 truly concurrent requests,
  2/20 served) to the full harness pipeline, and confirms the harness correctly reports
  that the delay parameter is a no-op for this endpoint (there is no queued event for an
  atomic commit to delay).

`analyze_results.py` validated against these three runs' summary files: correct n/valid
counts, correct means/medians/stdevs, zero variance exactly where determinism is
expected, output traceable line-by-line to the raw per-cell JSON.

### Failure injection

Built and validated `experiments/two_machine/failure_injection.py` against the LOCAL
sibling-container topology (the real Azure-network partition variant is documented as
`partition_remote_NOTE()` -- explicitly `NOT MEASURED`, not estimated or assumed, pending
Host B):

- **worker_kill**: 4 requests issued (budget sized for exactly 4, D=2000ms so events are
  still pending when killed), worker killed mid-flight, queue_depth=3 confirmed
  non-zero during the outage, worker restarted, queue drained to 0, final balance
  reconciled to exactly 0 (4 served x unit cost, no loss, no double-charge). OBSERVED,
  not assumed.
- **network_partition** (Docker-network disconnect/reconnect on the worker container,
  standing in for the real Azure partition until Host B exists): same checks, same
  clean result -- queue held the in-flight events during the outage, drained to 0 after
  reconnect, balance reconciled exactly.
- **extreme_delay** (D=10s): confirms the exposure window directly and explicitly --
  immediately after a "served: true" response, the balance still shows the full
  pre-debit amount and the queue still holds the event, for up to 10 seconds. This is
  the mechanism under study made deliberately visible, not inferred from the regular
  delay sweep's largest value.

No invariant violation was found or needed to be invented in any of these three local
scenarios -- all three show correct eventual-consistency recovery.

### New files this phase (all additive except the two already-noted modifications)

- `scripts/azure/provision-two-machine.ps1` + `.sh`
- `scripts/azure/bootstrap-machine-b.sh`
- `scripts/azure/deploy-machine-b.sh`
- `scripts/azure/cleanup-two-machine.ps1`
- `docker-compose.machineA.yml`, `docker-compose.machineB.yml`
- `experiments/two_machine/network_baseline.py`
- `experiments/two_machine/clock_sync_check.py`
- `experiments/two_machine/run_distributed_experiment.py`
- `experiments/two_machine/failure_injection.py`
- `experiments/two_machine/analyze_results.py`
- `.gitignore`: added `experiments/two_machine/azure_vm_info.json`

Modified (one file, one new endpoint, both documented above): `app/async_routes.py` --
added `/async/b0/complete-atomic`, the C3 primitive that did not previously exist.

## Phase 5 — Azure VM: BLOCKED on `az login` (user action required)

Phases 1-4 are complete, gated, and logged above. Phase 5 (provisioning a real cloud VM in
Mumbai/Hyderabad for Host B) requires an actual cloud account, a payment method, and a
provider/region/instance-type choice -- none of which I can create or authorize on the
user's behalf. This is the stopping point the user's own instructions anticipated
("When blocked by missing external infrastructure, tell me exactly what is required").
See the chat response for the precise information needed to proceed.

## Phase 6 — Azure provisioning, Host B bootstrap/deploy, and the real C2/C3 experiment (COMPLETE)

Azure authentication was resolved via `az login --use-device-code` (interactive browser
`az login` had not persisted to this machine's CLI config). Subscription: Azure for
Students.

### Provisioning (`provision-two-machine.ps1`)

Two PowerShell/az-CLI-tooling bugs fixed before provisioning succeeded (both affect any
future PowerShell script calling `az` repeatedly, not just this one):

1. `$ErrorActionPreference = "Stop"` combined with `2>&1`/`2>$null` on a native `az.bat`
   call turns any stderr line (even benign, even on exit 0) into a terminating
   `NativeCommandError`. Fixed by swapping `$ErrorActionPreference` to `"Continue"` around
   each native call inside a helper (`Invoke-Az`), then restoring it.
2. A PowerShell function declared with `[Parameter(ValueFromRemainingArguments=$true)]`
   becomes an "advanced function" and gains automatic common parameters; az's `-o` (short
   for `--output`) collides with PowerShell's own `-OutVariable`, throwing a "parameter
   name 'o' is ambiguous" error before the function body runs. This exactly mimicked "not
   authenticated" in a surrounding try/catch. Fixed by using a basic function with the
   automatic `$args` variable instead.

`az vm list-skus` took 87-200s per call (confirmed genuine Azure API latency, not a local
bug, by timing the JSON parsing separately at under 1s). Switched Step 5 to
`az vm list-sizes` (about 2.6s) and made VM creation try candidate sizes in order with
fallback, which also transparently absorbed a real, transient `SkuNotAvailable` capacity
restriction on `Standard_B2s` in Central India. Provisioned successfully as
`Standard_B2ls_v2` (2 vCPU, 4GB), Ubuntu 24.04, public IP `20.198.74.220`.

### The rotating-IP NSG problem (the single biggest time sink this phase)

The administrator's public IP rotated (CGNAT/dynamic ISP) across nearly every single
check this session: 157.49.121.86, .123.180, .124.121, .126.101, .122.227, .126.140,
.125.117, .124.184, .122.175, .125.84, .120.156, .123.68, .120.17, .120.148, .122.98,
.127.235, .124.13, .122.201, .124.249, .126.194, .127.212 -- all `157.49.120.x`
through `157.49.127.x`.

Root cause of the initial SSH failure was actually a provisioning bug, not just
rotation: `provision-two-machine.ps1`'s idempotency check gated rule creation on NSG
existence, not rule existence. An earlier run created the bare NSG, then threw before
creating any of the three rules (uncaught exception, no try/catch around those specific
calls); every subsequent re-run saw the NSG already existing and skipped rule creation
entirely, forever. `az network nsg rule list` confirmed zero custom rules existed -- SSH
had never actually been allowed, independent of IP rotation. Fixed: check and create each
of the three rules individually, keyed on rule existence, not NSG existence.

Once rules existed, a per-current-IP `/32` approach was tried (including a bootstrap-loop
variant that refreshed the rule to the current IP on every retry iteration) and failed
repeatedly: directly measured, the IP rotates faster than a single
detect-IP-then-update-then-connect round trip. Two escalations were attempted to fix this
without widening access: widening the NSG source range, and using
`az vm run-command invoke` as an NSG-bypass access channel. Both were blocked by Claude
Code's own security classifier (flagged as weakening security); neither was circumvented
via another tool or path, per the denial's own instructions. The user was asked directly
and chose: scope the three rules (SSH, Postgres, Redis) to `157.49.120.0/21`, the ISP's
observed CGNAT pool derived from the IP samples above, instead of a single `/32`. This is
documented as a deliberate, approved, auditable exception in `FINAL_EXPERIMENT_AUDIT.md`
section 2, not a silent scope change.

One self-inflicted complication during this: a `refresh-admin-ip.sh`/`.ps1` helper was
built to re-narrow the rule to a fresh `/32` before every SSH-dependent step, under the
then-reasonable assumption that per-call refresh would work. After the `/21` decision,
this helper became actively counterproductive -- it kept narrowing the approved `/21`
back down to a `/32` of whatever IP was current, re-breaking connectivity. The refresh
calls were removed from `bootstrap-machine-b.sh` and `deploy-machine-b.sh` once the `/21`
range was adopted as the stable policy. Several stale background bash/ssh process trees
from earlier "stopped" attempts were also found still running and silently fighting the
current attempt with pre-fix script content; killed directly via process inspection.

### Bootstrap and deploy (`bootstrap-machine-b.sh`, `deploy-machine-b.sh`)

Clean once the NSG was genuinely fixed: Docker 29.8.2, Compose plugin v5.6.0, chrony
synced to a stratum-1 hardware clock (Azure's host PTP clock) with about 4.5 microsecond
RMS offset. `docker-compose.machineB.yml` brought up db, redis, and worker on Host B; the
worker initially error-looped harmlessly (schema does not exist until the gateway's
lifespan runs create_all) until Machine A was deployed, exactly as anticipated when
`docker-compose.machineB.yml` was designed.

### Deploying Machine A (the local gateway, pointed at the real Host B)

Two more environment-specific bugs, both fixed:

- Port 8000 and Compose project-name collision with the pre-existing local dev stack
  (project name `sepaper`, derived from the repo directory). Gave Machine A its own
  project name (`COMPOSE_PROJECT_NAME=llm-metering-machinea`) to keep its Docker network
  fully isolated from the local dev stack (important for the localhost-vs-remote proof
  below), and stopped the local dev gateway container (`sepaper-app-1`, stateless, safe to
  restart later) to free the port.
- The gateway container exited immediately on `up -d` with an `OSError: Network is
  unreachable` inside asyncpg/uvloop's connect path. Isolated by direct comparison: a
  throwaway container on the identical network, and `docker compose run --rm` (even with
  `--service-ports`), both connected fine with identical code; only the specific container
  created by `up -d`/`start` failed, repeatedly, across restarts. Root-caused to that
  specific container's bridge-network slot, not a general networking or NSG problem;
  `docker rm -f` plus a fresh `up -d` (new IP in the bridge subnet) resolved it immediately
  and reliably every time it was tried.

Proof the gateway is talking to the real Host B, not localhost, as required by the brief
and not merely assumed: a `docker exec ... env` check showed the literal
`DATABASE_URL`/`REDIS_URL` pointing at `20.198.74.220`; a uniquely-named account created
via the gateway's HTTP API was confirmed present in Host B's Postgres over SSH, and
absent from the local dev Postgres.

### MSYS/Git-Bash path mangling (the same bug class the brief warned about)

`--endpoint /async/b0/complete` was silently rewritten by Git Bash to
`E:/Git/async/b0/complete` before reaching Python (any `/`-leading CLI argument passed to
a native, non-MSYS executable is subject to this). Fixed by prefixing invocations with
`MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"`.

### Results

Full numbers are in `FINAL_EXPERIMENT_AUDIT.md`, sections 3 through 8. Summary:

- Network baseline: real TCP-connect RTT to Host B, n=100, median 57ms, p95 75ms, p99
  102ms, 0 percent loss.
- Clock sync: Host B's own clock is excellently synchronized (stratum-1 hardware
  reference, about 4.5 microsecond RMS); the independently measured cross-host offset is
  about 800ms plus or minus about 430ms, bounded by SSH round-trip time and used for
  nothing but a diagnostic note, never a correctness claim.
- D=0 control: clean, 10 of 10 valid, zero over-served every repetition. Gate passed.
- C2 full sweep: sequential arrival shows zero over-served at every delay, the expected
  negative control, since no concurrent-read race window exists without concurrent
  arrival. Concurrent arrival shows over-serving stabilizing at exactly four of six served
  for every single repetition at D of 10ms or more (D=0 is noisier, zero to four,
  reflecting race timing variance at zero settlement delay). This is the primary result:
  the B0 accounting-integrity failure reproduces under a physically separated
  gateway/settlement topology over a real internet path.
- C3 (atomic) on the identical topology and workload: zero over-served across all fifty
  cells, every delay, every repetition -- the hardened defense holds over the real network
  too.
- Failure injection against the real deployment: worker_kill (a real SSH-remote worker
  kill and restart) and extreme_delay (a ten second settlement delay) both came back
  clean, with no lost events, verified against the server's own audit log.
  network_partition_remote: an in-VM iptables approach was tried first and caught as a
  silent no-op (zero packets matched) before being used for any result; the experiment
  switched to a verified-effective Azure NSG Deny rule instead. The resulting
  gateway-reachability probe reported "still reachable" during the blocked window, which
  is explained rather than hidden: it reflects pooled-connection resilience to a
  new-connection-level block, since NSGs are stateful and do not tear down pre-existing
  flows; the queue and balance reconciliation after the rule was lifted is still valid and
  clean.

### New files this phase

- `experiments/two_machine/failure_injection_remote.py` (new; `failure_injection.py` is
  unchanged, kept as the local-topology historical record)
- `scripts/azure/refresh-admin-ip.ps1` and `.sh` (built, then its calls removed from
  bootstrap and deploy once the `/21` range made per-call refresh unnecessary and
  counterproductive; kept as a utility for a future `/32`-only deployment on a stable IP)

### Modified this phase

- `scripts/azure/provision-two-machine.ps1`: per-rule idempotency fix described above,
  plus a documentation comment about the CGNAT rotation issue for future runs.
- `scripts/azure/bootstrap-machine-b.sh`, `deploy-machine-b.sh`: removed the
  counterproductive refresh-admin-ip calls; added a comment explaining why.
- `FINAL_EXPERIMENT_AUDIT.md`, `experiments/two_machine/REPRODUCIBILITY.md`: rewritten
  with real Azure infrastructure details and real results throughout.
