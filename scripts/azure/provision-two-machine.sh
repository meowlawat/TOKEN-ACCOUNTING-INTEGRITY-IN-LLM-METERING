#!/usr/bin/env bash
# Thin wrapper: the actual provisioning logic lives in provision-two-machine.ps1.
#
# Why PowerShell and not pure bash: Azure CLI on this machine is a pip-installed Windows
# Python entry point (E:\python\Scripts\az.bat / az). MSYS bash's automatic Unix-to-Windows
# path translation for arguments passed to native Windows executables is unreliable here --
# confirmed directly: the same `az account show` invocation returned exit 0 with no output
# at all through plain bash (silently wrong) but the correct exit 1 + "Please run az login"
# through both PowerShell and `cmd //c`. Rather than fight MSYS path-mangling across many
# multi-argument az calls (resource group/NSG/VM create, each with several flags), the
# actual Azure logic is one PowerShell script, invoked here the same reliable way.
#
# Usage:
#   ./scripts/azure/provision-two-machine.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Convert the MSYS-style path (/e/se paper/...) to a Windows path (E:\se paper\...)
# without depending on cygpath, which this Git-Bash install does not ship.
WIN_SCRIPT=$(echo "$SCRIPT_DIR/provision-two-machine.ps1" | sed -E 's#^/([a-zA-Z])/#\1:/#')
WIN_SCRIPT=$(echo "$WIN_SCRIPT" | tr '/' '\\')
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_SCRIPT" "$@"
