#!/usr/bin/env bash
# Deploy the settlement worker + Postgres + Redis stack to Host B and bring it up.
#
# Copies only what Host B's image build needs (Dockerfile, requirements.txt, app/) plus
# docker-compose.machineB.yml -- not the whole repository (paper/, release/ zips, etc.
# have no business being on the experiment VM).
#
# Usage:
#   ./scripts/azure/deploy-machine-b.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFO_JSON="$REPO_ROOT/experiments/two_machine/azure_vm_info.json"
SSH_KEY="$HOME/.ssh/llm-metering-two-machine"

if [[ ! -f "$INFO_JSON" ]]; then
    echo "ERROR: $INFO_JSON not found. Run provision-two-machine first." >&2
    exit 1
fi

PUBLIC_IP=$(python -c "import json; print(json.load(open('$INFO_JSON'))['public_ip'])")
ADMIN_USER=$(python -c "import json; print(json.load(open('$INFO_JSON'))['admin_username'])")
REMOTE_DIR="llm-metering"

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

echo "== Staging files for transfer (Dockerfile, requirements.txt, app/, compose file) =="
cd "$REPO_ROOT"
ssh $SSH_OPTS "${ADMIN_USER}@${PUBLIC_IP}" "mkdir -p ~/${REMOTE_DIR}"

tar czf - Dockerfile requirements.txt app docker-compose.machineB.yml | \
    ssh $SSH_OPTS "${ADMIN_USER}@${PUBLIC_IP}" "cat > ~/${REMOTE_DIR}/payload.tar.gz"

ssh $SSH_OPTS "${ADMIN_USER}@${PUBLIC_IP}" bash -s <<REMOTE
set -euo pipefail
cd ~/${REMOTE_DIR}
tar xzf payload.tar.gz
rm payload.tar.gz
echo "-- files on Host B: --"
find . -maxdepth 2 -type d
REMOTE

echo ""
echo "== Bringing up db + redis + worker on Host B =="
ssh $SSH_OPTS "${ADMIN_USER}@${PUBLIC_IP}" bash -s <<REMOTE
set -euo pipefail
cd ~/${REMOTE_DIR}
sudo docker compose -f docker-compose.machineB.yml up -d --build
echo "-- waiting for health --"
for i in \$(seq 1 30); do
    status=\$(sudo docker compose -f docker-compose.machineB.yml ps --format json 2>/dev/null | python3 -c "
import sys, json
rows = [json.loads(l) for l in sys.stdin if l.strip()]
bad = [r['Service'] for r in rows if r.get('Health') not in (None, 'healthy') and r['Service'] != 'worker']
print('OK' if not bad else ','.join(bad))
" 2>/dev/null || echo "PENDING")
    if [[ "\$status" == "OK" ]]; then echo "db/redis healthy."; break; fi
    sleep 2
done
sudo docker compose -f docker-compose.machineB.yml ps
echo "-- worker log tail --"
sudo docker compose -f docker-compose.machineB.yml logs --tail 20 worker
REMOTE

echo ""
echo "== DONE =="
echo "Host B stack is up. Verify externally with:"
echo "  nc -zv -w5 ${PUBLIC_IP} 5432  (should succeed from the admin IP only)"
echo "  nc -zv -w5 ${PUBLIC_IP} 6379  (should succeed from the admin IP only)"
