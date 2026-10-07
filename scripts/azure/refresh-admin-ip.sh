#!/usr/bin/env bash
# Refresh the Host B NSG's SSH-allow rule to this machine's current public IP.
# Run immediately before any SSH-dependent step -- see refresh-admin-ip.ps1 for why.
#
# Usage:
#   ./scripts/azure/refresh-admin-ip.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
to_win_path() { echo "$1" | sed -E 's#^/([a-zA-Z])/#\1:/#' | tr '/' '\\'; }
PS1_WIN=$(to_win_path "$SCRIPT_DIR/refresh-admin-ip.ps1")

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN"
