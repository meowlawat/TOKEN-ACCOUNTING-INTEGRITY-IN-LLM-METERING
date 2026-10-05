# Two-Machine Experiment — Canonical Reproduction Sequence

A fresh researcher, starting from a clean checkout of this repository, does the
following in order. Steps 1-4 require your own Azure for Students account and are not
performed by any script on your behalf.

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
HOSTB_PUBLIC_IP="$HOSTB_IP" docker compose -f docker-compose.machineA.yml up -d --build
curl -s http://localhost:8000/admin/db-info   # confirms the gateway can actually reach Host B's Postgres
```

## 8. D=0 control (mandatory before any delay sweep)

```
python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival sequential --delays 0 --reps 10
```

Expected: zero over-serving at every repetition. **If this fails, stop and diagnose --
do not proceed to step 9.**

## 9. C2 full delay sweep (the actual two-machine experiment)

```
python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival sequential --delays 0,10,50,100,500 --reps 10
python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival concurrent --delays 0,10,50,100,500 --reps 10
```

## 10. C3 on the same two-machine topology (atomic control)

```
python -m experiments.two_machine.run_distributed_experiment \
    --condition C3 --arrival sequential --delays 0,10,50,100,500 --reps 10
python -m experiments.two_machine.run_distributed_experiment \
    --condition C3 --arrival concurrent --delays 0,10,50,100,500 --reps 10
```

## 11. Failure injection (point BASE at the real deployment if adapting the script)

```
python -m experiments.two_machine.failure_injection --scenario all
```

(Currently targets the local sibling-container topology by name --
`sepaper-worker-1`/`sepaper_default`. Adapt the container/network names if running
against Host B's actual containers over SSH, or extend `partition_remote_NOTE()` into a
real implementation once Host B exists.)

## 12. Analysis

```
python -m experiments.two_machine.analyze_results "results/two_machine/C2_*.summary.json" "results/two_machine/C3_*.summary.json"
```

## 13. Cleanup

```
powershell.exe -File scripts/azure/cleanup-two-machine.ps1 -Mode Deallocate   # safe, resumable
```

or, to permanently delete everything this experiment created:

```
az group delete --name rg-llm-metering-two-machine --yes --no-wait
```

(printed, not auto-executed, by `cleanup-two-machine.ps1 -Mode Delete`).
