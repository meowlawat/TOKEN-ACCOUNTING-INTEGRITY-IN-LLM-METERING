#!/usr/bin/env bash
# Bootstrap Host B (Ubuntu) for the two-machine experiment: Docker, chrony, diagnostics,
# and the repository's accounting worker. Idempotent -- safe to re-run.
#
# Usage:
#   ./scripts/azure/bootstrap-machine-b.sh
#
# Reads connection info from experiments/two_machine/azure_vm_info.json (written by
# provision-two-machine.ps1/.sh). Does not touch the historical v1.0.1 artifact or
# anything under paper/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFO_JSON="$REPO_ROOT/experiments/two_machine/azure_vm_info.json"
SSH_KEY="$HOME/.ssh/llm-metering-two-machine"

if [[ ! -f "$INFO_JSON" ]]; then
    echo "ERROR: $INFO_JSON not found. Run scripts/azure/provision-two-machine.sh first." >&2
    exit 1
fi

# `python` here is the native Windows python.exe, which needs a Windows-style path
# (E:\...), not the MSYS-style path (/e/...) bash itself uses.
to_win_path() { echo "$1" | sed -E 's#^/([a-zA-Z])/#\1:/#' | tr '/' '\\'; }
INFO_JSON_WIN=$(to_win_path "$INFO_JSON")

PUBLIC_IP=$(python -c "import json; print(json.load(open(r'$INFO_JSON_WIN', encoding='utf-8-sig'))['public_ip'])")
ADMIN_USER=$(python -c "import json; print(json.load(open(r'$INFO_JSON_WIN', encoding='utf-8-sig'))['admin_username'])")

if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
    echo "ERROR: no public_ip in $INFO_JSON -- VM may not be fully provisioned yet." >&2
    exit 1
fi

SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 ${ADMIN_USER}@${PUBLIC_IP}"

# The administrator's public IP rotates (CGNAT/dynamic ISP) faster than a per-attempt
# /32 refresh can track (confirmed: rotation cycle shorter than one refresh+connect round
# trip). The NSG's SSH/Postgres/Redis rules are therefore scoped to the observed /21 ISP
# range (157.49.120.0/21, user-approved -- see FINAL_EXPERIMENT_AUDIT.md limitations)
# instead of a single IP. Do NOT call refresh-admin-ip.sh here: it narrows the rule back
# to a /32 of whatever IP is current, undoing the approved range.
echo "== Waiting for SSH to become reachable on $PUBLIC_IP =="
for i in $(seq 1 30); do
    if $SSH -o ConnectTimeout=5 "echo ok" 2>/dev/null | grep -q ok; then
        echo "SSH reachable."
        break
    fi
    if [[ "$i" -eq 30 ]]; then
        echo "ERROR: SSH did not become reachable after repeated tries with IP refresh. Check NSG rules / VM boot state." >&2
        exit 1
    fi
    sleep 5
done

echo ""
echo "== Installing packages (Docker, chrony, diagnostics) =="
$SSH 'bash -s' <<'REMOTE_SCRIPT'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "--- apt update ---"
sudo apt-get update -qq

echo "--- installing chrony, diagnostics, prerequisites ---"
sudo apt-get install -y -qq \
    chrony curl jq iproute2 iputils-ping traceroute netcat-openbsd \
    ca-certificates gnupg git >/dev/null

echo "--- chrony status ---"
sudo systemctl enable --now chrony >/dev/null 2>&1 || true
sleep 2
chronyc tracking || true
chronyc sources || true

echo "--- Docker ---"
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. NOTE: group membership requires a new SSH session to take effect."
else
    echo "Docker already installed: $(docker --version)"
fi

echo "--- Docker Compose plugin ---"
if ! docker compose version >/dev/null 2>&1; then
    sudo apt-get install -y -qq docker-compose-plugin >/dev/null
fi
sudo docker compose version || true

mkdir -p ~/llm-metering/experiments/two_machine/raw
echo "--- bootstrap complete ---"
REMOTE_SCRIPT

echo ""
echo "== Re-checking chrony after install (fresh connection, in case group/service needs settling) =="
sleep 3
$SSH "chronyc tracking; echo ---; chronyc sources -v" || true

echo ""
echo "== DONE =="
echo "Host B ready at ${ADMIN_USER}@${PUBLIC_IP}"
echo "Next: copy the app/ directory and docker-compose config, then run the worker there."
echo "See scripts/azure/deploy-machine-b.sh"
