<#
.SYNOPSIS
  Refresh the Host B NSG's SSH-allow rule to this machine's CURRENT public IP.

.DESCRIPTION
  The administrator's public IP has been observed to rotate (CGNAT/dynamic-ISP
  behavior) on the order of minutes during this project. A /32 NSG rule set once at
  provisioning time goes stale and silently blocks SSH with no indication other than a
  connection timeout. This script re-points the rule at whatever IP is current RIGHT NOW,
  and is meant to be run immediately before any SSH-dependent step (bootstrap, deploy,
  clock-sync check, failure injection), not just once.

.EXAMPLE
  .\refresh-admin-ip.ps1
#>

[CmdletBinding()]
param(
    [string]$ResourceGroupName = "rg-llm-metering-two-machine",
    [string]$NsgName           = "vm-llm-metering-hostb-nsg",
    [string]$RuleName          = "AllowSSHAdminOnly"
)

$ErrorActionPreference = "Stop"
$az = "E:\python\Scripts\az.bat"

function Invoke-Az {
    # Basic function (no [Parameter(ValueFromRemainingArguments)]) -- an advanced function
    # gains automatic common parameters and az's "-o" collides with "-OutVariable".
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $az @args 2>$null
    $ErrorActionPreference = $prevEap
    if ($LASTEXITCODE -ne 0) { throw "az $($args -join ' ') failed:`n$out" }
    return $out
}

$currentIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content.Trim()
Invoke-Az network nsg rule update -g $ResourceGroupName --nsg-name $NsgName -n $RuleName `
    --source-address-prefixes "$currentIp/32" -o none
Write-Host "NSG '$RuleName' refreshed to $currentIp/32"
