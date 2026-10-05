# Final Experiment Audit — Two-Machine Asynchronous Settlement Experiment

Status as of this audit: **local phases complete and validated; the actual two-machine
(C2) result is BLOCKED pending Azure authentication.** Every number below is traced to a
specific raw-data file in `experiments/two_machine/raw/` or `results/two_machine/`. Where
something was not measured, it says `NOT MEASURED`, not an estimate.

---

## 1. Local baseline

Source: `results/two_machine/C0_sequential_20261005T230453Z.summary.json` and
`...20261005T230553Z.summary.json` (10 reps each, D=0/500, run before and after a full
`docker compose restart app db redis`), plus `results/two_machine/analysis_summary.json`.

| condition | arrival | delay (ms) | n | valid | over-served mean | stdev |
|---|---|---|---|---|---|---|
| C0 | sequential | 0 | 20 | 20 | 0.00 | 0.00 |
| C0 | sequential | 500 | 20 | 20 | 4.00 | 0.00 |

Also reproduced, from `experiments/two_machine/raw/C0_sequential_20261004T215413Z.jsonl`
(the Phase 4 post-clock-fix regression) at the full historical delay set: over-served =
0, 0, 0, 1, 4 at D = 0, 10, 50, 100, 500 ms — exact match to the originally published row.

**Repeatability**: the two 10-rep runs above used identical seeds (`SEED_BASE + rep`,
rep=0..9 in both) and produced identical per-rep final balances across a full container
restart in between. This is direct evidence the result is deterministic given the seed,
not an artifact of accumulated Redis/Postgres state from a prior run.

## 2. Two-machine (C2) results

**NOT MEASURED.** `az account show` / `az account list` both confirm Azure CLI is
installed (2.90.0) but not authenticated (`ERROR: Please run 'az login' to setup
account.`); `~/.azure/azureProfile.json` contains zero subscriptions. No VM, no resource
group, no network path exists. Every script needed to run C2 the moment this is resolved
is built and locally validated (`scripts/azure/*`, `docker-compose.machine{A,B}.yml`,
`experiments/two_machine/run_distributed_experiment.py --condition C2`), but none has
been executed against real Azure infrastructure, and this document does not claim
otherwise.

## 3. Atomic control (C3)

Source: `results/two_machine/C3_concurrent_20261005T223032Z.summary.json` (3 reps,
D=0/500, concurrent arrival) plus a direct, separate stress test (not part of the
harness, run manually against `/async/b0/complete-atomic`): 20 genuinely concurrent
requests (`asyncio.gather`) against a budget sized for exactly 2 — result: exactly 2
served, final balance exactly `0.000000`.

| condition | arrival | delay (ms) | n | valid | over-served mean |
|---|---|---|---|---|---|
| C3 | concurrent | 0 | 3 | 3 | 0.00 |
| C3 | concurrent | 500 | 3 | 3 | 0.00 |

This is a **local** result (C3 run on the same host as the gateway, via the sibling
worker container; not yet on Azure). The delay parameter is a structural no-op for this
endpoint — no event is queued for an atomic commit, so "D=500" measures the same thing as
"D=0" for this condition. This is expected behavior, not a measurement gap, and is
documented as such in the code (`app/async_routes.py::async_b0_complete_atomic`).

## 4. Failure injection

Source: `results/two_machine/failure_injection_all_20261005T230443Z.json`. All three
scenarios cross-checked against the server's own raw per-request ledger
(`/admin/m-trials/{id}/audit`), not merely against a client-computed expected balance:

| scenario | requests | server audit record count matches | server audit served count matches client | queue drained to 0 | balance reconciled |
|---|---|---|---|---|---|
| worker_kill | 4 | yes | yes | yes | yes |
| network_partition (local, Docker-network disconnect) | 3 | yes | yes | yes | yes |
| extreme_delay (D=10s) | 1 | n/a (single request, demonstrative) | n/a | queue=1 immediately after response (expected) | n/a |

`partition_remote_NOTE()` in `failure_injection.py` explicitly marks the **real** Azure
network-partition variant as `NOT MEASURED`, with the exact steps it requires documented
rather than estimated.

No invariant violation was found in any scenario. None was invented.

## 5. Network baseline

**NOT MEASURED.** `experiments/two_machine/network_baseline.py` is built and does TCP-
connect RTT timed entirely on the local (Host A) monotonic clock (so it does not itself
depend on clock sync), but has not been run against anything, because no Host B exists.

## 6. Clock synchronization

**NOT MEASURED** against a real Host B. `experiments/two_machine/clock_sync_check.py` is
built: it records chrony's own self-report AND an independently measured
`time.time_ns()` offset via repeated SSH round trips (method validated earlier, in Phase
4, on the host-vs-Docker-VM clock-domain mismatch). What WAS measured, locally, in Phase
4: host (Windows) vs. gateway container (Docker Desktop's Linux VM) `time.time_ns()`
differ by ~303 ms. This is a Docker-Desktop-on-Windows artifact, not a prediction for the
real Azure deployment, and is not substituted for a real Host A/B measurement anywhere in
this document.

## 7. Reproducibility

Demonstrated directly (§1): identical seeds across a full container restart produce
identical results. Canonical command sequence: see `REPRODUCIBILITY.md` (new, this
audit). Every raw file this audit cites is committed in `experiments/two_machine/raw/`
and `results/two_machine/`; none was deleted or overwritten.

## 8. Threats to validity (current state)

- **C2 does not exist yet.** Every claim about physical/network separation is
  necessarily about C1 (sibling-container, same host, same clock domain) and local
  failure injection, not a real network boundary. This is the single largest open
  threat and is why the manuscript's existing limitation paragraph
  (`paper/main_fgcs.tex:1394-1410`) remains accurate and unmodified.
- **C3's "delay" is a no-op by construction** (§3) — H3 ("atomic coupling produces zero
  over-serving across tested latency conditions") is trivially true for this condition
  locally because there is no settlement delay to be insensitive to; the real test of
  H3 is whether the atomic path still performs acceptably (and still shows zero
  over-serving) once the ledger it commits to is genuinely across a network, which is
  blocked on the same Azure access.
- **The local network-partition scenario uses Docker network disconnect, not a real
  NSG/firewall-level partition** — explicitly flagged as a stand-in, not equivalent.
- Mock LLM / seeded randomness: cost variation between repetitions comes from the mock
  generator's seeded output-length distribution, not from any uncontrolled source;
  confirmed by the fact identical seeds reproduce identical final balances exactly.

## 9. Claims CURRENTLY supported by this work

- The published single-host B0 over-serving result (0,0,0,1,4 at D=0,10,50,100,500ms)
  is reproduced exactly, repeatedly, across a full stack restart, through both the
  original script and a newly built, more rigorous harness.
- A worker running as a genuinely separate OS process (not merely an asyncio task in
  the gateway) reproduces the same result, PROVIDED it shares the gateway's clock
  domain (C1) — process separation alone does not change the result.
- A newly built atomic-commitment primitive for B0 (`reserve_atomic`-based, not
  previously present in the repository) empirically prevents over-serving under real
  concurrency (20 concurrent requests, 2/20 served, balance exactly 0) and under the
  validated sequential protocol at every tested delay, locally.
- The async settlement pipeline recovers cleanly from a worker crash and from a local
  network partition: no lost events, no double counting, verified against the server's
  own raw per-request records, not merely a final-balance coincidence.

## 10. Claims NOT YET supported (do not write these until C2 exists)

- "The accounting-integrity failure survives physical/network separation of gateway
  and settlement infrastructure." — UNTESTED. This is the actual open scientific
  question and remains open.
- Any number for real network RTT, real cross-host clock offset, or C2's over-serving
  behavior under real latency.
- Any claim that a commercial provider, or any production system, is vulnerable — not
  claimed anywhere in this work and not supported by anything that has been measured.
- Any claim that injected delay represents production latency.
