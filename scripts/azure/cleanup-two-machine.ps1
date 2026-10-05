<#
.SYNOPSIS
  Stop (deallocate) or fully delete the two-machine experiment's Azure resources.

.DESCRIPTION
  NEVER run automatically. This script is for the user to invoke deliberately when the
  experiment is genuinely finished and Host B is no longer needed.

  Two modes:
    -Mode Deallocate  (default, recommended): stops billing for compute while PRESERVING
                       the VM, its disk, and its public IP association for inspection or
                       a later resume. `az vm start` brings it back exactly as it was.
    -Mode Delete       permanently deletes the VM and the dedicated resource group
                       (and therefore the disk, NIC, NSG, public IP -- everything this
                       experiment created). Irreversible. Only the resource group THIS
                       script's provisioning counterpart created is touched; no other
                       Azure resource is affected.

.EXAMPLE
  .\cleanup-two-machine.ps1 -Mode Deallocate
  .\cleanup-two-machine.ps1 -Mode Delete
#>

[CmdletBinding()]
param(
    [ValidateSet("Deallocate", "Delete")]
    [string]$Mode = "Deallocate",
    [string]$ResourceGroupName = "rg-llm-metering-two-machine",
    [string]$VmName            = "vm-llm-metering-hostb"
)

$ErrorActionPreference = "Stop"
$az = "E:\python\Scripts\az.bat"

function Invoke-Az {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $out = & $az @Args 2>&1
    if ($LASTEXITCODE -ne 0) { throw "az $($Args -join ' ') failed:`n$out" }
    return $out
}

$exists = (Invoke-Az group exists --name $ResourceGroupName) -eq "true"
if (-not $exists) {
    Write-Host "Resource group '$ResourceGroupName' does not exist -- nothing to clean up."
    exit 0
}

if ($Mode -eq "Deallocate") {
    Write-Host "Deallocating VM '$VmName' (stops compute billing; disk/IP/config preserved)..."
    Invoke-Az vm deallocate -g $ResourceGroupName -n $VmName | Out-Null
    Write-Host "Done. Resume later with:"
    Write-Host "  $az vm start -g $ResourceGroupName -n $VmName"
    Write-Host "NOTE: a Standard-SKU public IP (used here, per the provisioning script) is"
    Write-Host "retained and billed at its own small rate even while the VM is deallocated."
    Write-Host "To stop that too, either accept the small cost, or use -Mode Delete when"
    Write-Host "truly finished."
} else {
    Write-Host "This will PERMANENTLY DELETE resource group '$ResourceGroupName' and" -ForegroundColor Yellow
    Write-Host "everything in it (VM, disk, NIC, NSG, public IP). This cannot be undone." -ForegroundColor Yellow
    Write-Host "Re-run with -Mode Delete only when you are certain." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To actually proceed, run:"
    Write-Host "  $az group delete --name $ResourceGroupName --yes --no-wait"
    Write-Host ""
    Write-Host "(Not executed automatically by this script -- confirm by running that"
    Write-Host "command yourself.)"
}
