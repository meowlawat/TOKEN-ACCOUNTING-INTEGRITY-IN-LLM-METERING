# Two-Machine Experiment — Canonical Reproduction Sequence

A fresh researcher, starting from a clean checkout of this repository, does the
following in order. Steps 1-4 require your own Azure for Students account and are not
performed by any script on your behalf.

**This sequence has been run end-to-end against real Azure infrastructure** (resource
group `rg-llm-metering-two-machine`, VM `vm-llm-metering-hostb`, Central India,
`Standard_B2ls_v2`, public IP `20.198.74.220`). Results: `FINAL_EXPERIMENT_AUDIT.md`.
Three practical gotchas hit during that run, fixed below rather than only in the audit:

1. **Git-Bash/MSYS path mangling.** Any CLI argument starting with `/` (e.g.
   `--endpoint /async/b0/complete`) gets silently rewritten into a Windows path (e.g.
   `E:/Git/async/b0/complete`) when a Python command is run from Git Bash. Fix: prefix
   every `python -m experiments.two_machine...` invocation below with
   `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"` when running from Git Bash on Windows.
2. **Rotating administrator IP (CGNAT).** If your ISP rotates your public IP faster than
   you can refresh a `/32` NSG rule (confirmed on this run: rotation faster than a single
   detect-and-update cycle), a single IP cannot be used for the NSG's SSH/Postgres/Redis
   allow rules. This requires a deliberate, explicit decision (not a default): either get
   a stable IP, or scope the rule to your ISP's actual observed CGNAT range instead of a
   single address. See `FINAL_EXPERIMENT_AUDIT.md` §2 for how this was resolved.
3. **Port 8000 / Compose project-name collision with a local dev stack.** If you already
   have the repository's default `docker compose up` stack running locally (project name
   derived from the directory, e.g. `sepaper`), `docker-compose.machineA.yml` will collide
   on host port 8000. Give Machine A its own project name
   (`COMPOSE_PROJECT_NAME=llm-metering-machinea`) to keep its network fully isolated from
   the local dev stack (important for the "prove it's not talking to localhost" check in
   step 7), and stop the local dev gateway container first (`docker stop sepaper-app-1`;
   it is stateless and safe to restart afterward).

## 0. Local prerequisites

- Docker Desktop running.
- `docker compose up -d --build` from the repository root.

## 1. Azure login (manual, interactive -- yours to run)

```
E:\python\Scripts\az.bat login
```

(or wherever your `az` CLI is installed). Confirm with:

```
az account show
```

## 2. Provision Host B

```
./scripts/azure/provision-two-machine.sh
```

Idempotent. Writes `experiments/two_machine/azure_vm_info.json` (git-ignored). Creates a
dedicated resource group, NSG (22/5432/6379 restricted to your detected public IP only),
and VM. Never touches any other Azure resource.

## 3. Bootstrap Host B

```
./scripts/azure/bootstrap-machine-b.sh
```

Installs Docker, Compose plugin, chrony, diagnostics. Reports `chronyc tracking`/`sources`.

## 4. Deploy the settlement stack to Host B

```
./scripts/azure/deploy-machine-b.sh
```

Ships `Dockerfile`, `requirements.txt`, `app/`, `docker-compose.machineB.yml` and brings
up `db` + `redis` + `worker` there (no gateway on Host B).

## 5. Network baseline (Host A -> Host B)

```
HOSTB_IP=$(python -c "import json; print(json.load(open('experiments/two_machine/azure_vm_info.json'))['public_ip'])")
python -m experiments.two_machine.network_baseline --host "$HOSTB_IP" --port 5432 --n 100
```

## 6. Clock synchronization check

```
python -m experiments.two_machine.clock_sync_check --host "$HOSTB_IP"
```

Review the output before trusting any cross-host latency number. Do not proceed to treat
timestamps as comparable if this reports a large, unbounded offset.

## 7. Deploy Host A (gateway) pointed at Host B

```
docker stop sepaper-app-1   # if the local dev stack's gateway is running, to free port 8000
HOSTB_PUBLIC_IP="$HOSTB_IP" COMPOSE_PROJECT_NAME=llm-metering-machinea \
    docker compose -f docker-compose.machineA.yml up -d --build
curl -s http://localhost:8000/admin/db-info   # confirms the gateway can actually reach Host B's Postgres
```

If the container exits immediately with `OSError: [Errno 101] Network is unreachable`
inside asyncpg/uvloop: this was observed to be specific to the container created by
`up -d`, not a general networking problem (a plain `docker run` or
`docker compose run --rm` on the identical network connected fine). Fix:
`docker rm -f llm-metering-machinea-app-1` then re-run the `up -d` command above — a fresh
container (new IP in the bridge subnet) resolved it every time it was tried. Do not
conclude the network/NSG is broken from this error alone; verify with a throwaway
container first.

**Proving Machine A is talking to Host B, not localhost** (do this once, not optional):
```
docker exec llm-metering-machinea-app-1 env | grep -E "DATABASE_URL|REDIS_URL"   # must show the literal public IP
curl -s -X POST http://localhost:8000/admin/accounts -H "Content-Type: application/json" -d '{"name":"PROOF","balance":0.0}'
ssh -i ~/.ssh/llm-metering-two-machine azureuser@"$HOSTB_IP" \
    "sudo docker exec llm-metering-db-1 psql -U postgres -d metering -t -c \"SELECT id,name FROM accounts WHERE name='PROOF';\""
```
The account must appear in Host B's database and be absent from the local dev DB
(`docker exec sepaper-db-1 psql -U postgres -d metering -t -c "SELECT ... WHERE name='PROOF';"` — empty).

## 8. D=0 control (mandatory before any delay sweep)

```
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival sequential --delays 0 --reps 10 --endpoint /async/b0/complete
```

Expected: zero over-serving at every repetition. **If this fails, stop and diagnose --
do not proceed to step 9.** Observed result: `results/two_machine/C2_sequential_20261006T233241Z.summary.json` — 10/10 valid, served=2, over_served=0 every rep.

## 9. C2 full delay sweep (the actual two-machine experiment)

```
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival sequential --delays 0,10,50,100,500 --reps 10 --endpoint /async/b0/complete
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival concurrent --delays 0,10,50,100,500 --reps 10 --endpoint /async/b0/complete
```

Observed results: `results/two_machine/C2_sequential_20261006T233416Z.summary.json` (0
over-served at every delay — expected negative control) and
`results/two_machine/C2_concurrent_20261006T234156Z.summary.json` (over-served stabilizes
at 4/6 for every D≥10ms rep — the primary reproduction result). See
`FINAL_EXPERIMENT_AUDIT.md` §6.

## 10. C3 on the same two-machine topology (atomic control)

```
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C3 --arrival concurrent --delays 0,10,50,100,500 --reps 10
```

Observed result: `results/two_machine/C3_concurrent_20261006T234655Z.summary.json` — all
50 cells `served=2, over_served=0, final_balance=0.000000`.

## 11. Failure injection against the real deployment

```
python -m experiments.two_machine.failure_injection_remote --scenario worker_kill
python -m experiments.two_machine.failure_injection_remote --scenario network_partition_remote
python -m experiments.two_machine.failure_injection_remote --scenario extreme_delay
```

(`failure_injection.py`, targeting the local sibling-container topology by name, is kept
unchanged as the historical C1 record. `failure_injection_remote.py` is the real-Host-B
variant: `worker_kill` stops/starts Host B's actual worker container over SSH;
`network_partition_remote` uses a temporary, higher-priority Azure NSG Deny rule,
verified by direct measurement to actually block new connections before being trusted for
a result — an earlier in-VM `iptables -I DOCKER-USER` attempt was tried first and found to
be a silent no-op on this Docker/Ubuntu setup; `extreme_delay` needs no orchestration, only
the HTTP API.) Results and the pooled-connection caveat on `network_partition_remote`: see
`FINAL_EXPERIMENT_AUDIT.md` §8.

## 12. Analysis

```
python -m experiments.two_machine.analyze_results results/two_machine/C2_sequential_*.summary.json results/two_machine/C2_concurrent_*.summary.json results/two_machine/C3_concurrent_*.summary.json
```

Output: `results/two_machine/analysis_summary.json`. (Pass explicit filenames rather than
a glob pattern in quotes if your shell does not expand globs before `argparse` sees them.)

## 13. Cleanup

```
powershell.exe -File scripts/azure/cleanup-two-machine.ps1 -Mode Deallocate   # safe, resumable
```

or, to permanently delete everything this experiment created:

```
az group delete --name rg-llm-metering-two-machine --yes --no-wait
```

(printed, not auto-executed, by `cleanup-two-machine.ps1 -Mode Delete`).
