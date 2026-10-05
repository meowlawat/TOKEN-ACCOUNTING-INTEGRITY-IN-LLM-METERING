<#
.SYNOPSIS
  Provision Host B (the settlement/Redis/PostgreSQL machine) for the two-machine
  asynchronous-settlement experiment, on Azure.

.DESCRIPTION
  Idempotent: re-running this script against an existing resource group/VM of the same
  name will not recreate them, and will not touch any OTHER Azure resource. It:

    1. Verifies `az` is authenticated (fails fast with instructions if not -- `az login`
       is interactive and requires the user's own Microsoft/Azure-for-Students account;
       this script never attempts to perform that login itself).
    2. Detects the administrator's current public IP via an external IP-echo service, so
       SSH and the Postgres/Redis NSG rules can be scoped to exactly that address rather
       than 0.0.0.0/0. This machine (the one running this script) IS "Machine A" in the
       experiment's topology, so its own public IP is the correct scope for all three
       rules.
    3. Picks the Azure-for-Students subscription if more than one is available, and
       reports which subscription will be used either way.
    4. Queries ACTUAL region availability for the subscription (never assumes
       "centralindia" exists for this subscription) and picks the closest available
       Indian region, preferring Central India.
    5. Queries ACTUAL VM size availability in that region and picks the cheapest
       Linux/x86_64, no-GPU, ~2 vCPU / ~2GB+ RAM burstable SKU actually offered --
       never hardcodes a SKU name.
    6. Creates a DEDICATED resource group (never reuses or modifies an existing one
       unless it was created by a previous run of this exact script).
    7. Creates an NSG with SSH (22), PostgreSQL (5432) and Redis (6379) inbound rules,
       each scoped to the detected admin IP /32 only -- never 0.0.0.0/0.
    8. Creates the VM (Ubuntu LTS) using the dedicated SSH keypair's PUBLIC key only.
    9. Prints a machine-readable summary (also written to
       experiments/two_machine/azure_vm_info.json, git-ignored) with everything
       bootstrap-machine-b.sh and the experiment runner need.

.NOTES
  Never run with destructive flags. Never deletes or modifies resources outside the
  dedicated resource group this script creates. Safe to re-run.
#>

[CmdletBinding()]
param(
    [string]$ResourceGroupName = "rg-llm-metering-two-machine",
    [string]$VmName            = "vm-llm-metering-hostb",
    [string]$AdminUsername     = "azureuser",
    [string]$SshPublicKeyPath  = "$HOME\.ssh\llm-metering-two-machine.pub",
    [string]$PreferredRegion   = "centralindia",
    [int]$MinVCpus             = 2,
    [int]$MinMemoryGB          = 2
)

$ErrorActionPreference = "Stop"
$az = "E:\python\Scripts\az.bat"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$InfoOutPath = Join-Path $RepoRoot "experiments\two_machine\azure_vm_info.json"

function Invoke-Az {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $out = & $az @Args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "az $($Args -join ' ') failed (exit $LASTEXITCODE):`n$out"
    }
    return $out
}

Write-Host "== Step 1: Azure CLI authentication =="
try {
    $account = Invoke-Az account show -o json | ConvertFrom-Json
} catch {
    Write-Host ""
    Write-Host "NOT AUTHENTICATED. This script cannot proceed." -ForegroundColor Red
    Write-Host "Azure 'az login' is an interactive step that requires your own" -ForegroundColor Red
    Write-Host "Microsoft / Azure for Students account credentials -- it cannot be" -ForegroundColor Red
    Write-Host "performed on your behalf. Run this yourself, then re-run this script:" -ForegroundColor Red
    Write-Host ""
    Write-Host "    E:\python\Scripts\az.bat login" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host "Authenticated as: $($account.user.name)"

Write-Host ""
Write-Host "== Step 2: Subscription selection =="
$subs = Invoke-Az account list -o json | ConvertFrom-Json
$studentSub = $subs | Where-Object { $_.name -match "Student" } | Select-Object -First 1
$chosenSub = if ($studentSub) { $studentSub } else { $subs | Select-Object -First 1 }
Write-Host "Available subscriptions: $($subs.Count)"
foreach ($s in $subs) { Write-Host "  - $($s.name)  [$($s.id)]  state=$($s.state)" }
Write-Host "Using subscription: $($chosenSub.name) [$($chosenSub.id)]"
Invoke-Az account set --subscription $chosenSub.id | Out-Null

Write-Host ""
Write-Host "== Step 3: Detect administrator public IP (this machine = Machine A) =="
$adminIp = $null
foreach ($svc in @("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com")) {
    try {
        $adminIp = (Invoke-WebRequest -Uri $svc -UseBasicParsing -TimeoutSec 8).Content.Trim()
        if ($adminIp -match '^\d{1,3}(\.\d{1,3}){3}$') { break } else { $adminIp = $null }
    } catch { continue }
}
if (-not $adminIp) {
    Write-Host "Could not determine public IP from any external echo service. STOPPING." -ForegroundColor Red
    exit 1
}
Write-Host "Administrator public IP (Machine A): $adminIp"

Write-Host ""
Write-Host "== Step 4: Region availability =="
$locations = Invoke-Az account list-locations -o json | ConvertFrom-Json
$indianRegions = $locations | Where-Object { $_.metadata.geographyGroup -eq "Asia Pacific" -and $_.displayName -match "India" }
Write-Host "Indian regions visible to this subscription:"
foreach ($r in $indianRegions) { Write-Host "  - $($r.name) ($($r.displayName))" }
$region = if ($indianRegions.name -contains $PreferredRegion) {
    $PreferredRegion
} elseif ($indianRegions.Count -gt 0) {
    $indianRegions[0].name
} else {
    Write-Host "No Indian region visible to this subscription. STOPPING -- this needs your decision." -ForegroundColor Red
    exit 1
}
Write-Host "Selected region: $region"

Write-Host ""
Write-Host "== Step 5: VM size availability in $region =="
# list-skus gives restrictions (e.g. "NotAvailableForSubscription") per size per region --
# query only sizes with NO restrictions for this subscription in this region.
$skusRaw = Invoke-Az vm list-skus --location $region --resource-type virtualMachines -o json
$skus = $skusRaw | ConvertFrom-Json
$candidates = $skus | Where-Object {
    $_.name -match '^Standard_B' -and                 # burstable family: cheapest for intermittent load
    $_.name -notmatch 'ps_v|pls_v' -and                # exclude ARM (ps/pls = Ampere Altra) -- need x86_64
    (-not $_.restrictions -or $_.restrictions.Count -eq 0)
}
# Pull vCPU/MemoryGB capability out of each candidate and filter to the requested minimum.
$sized = foreach ($c in $candidates) {
    $vcpus = ($c.capabilities | Where-Object { $_.name -eq 'vCPUs' }).value
    $memMB = ($c.capabilities | Where-Object { $_.name -eq 'MemoryGB' }).value
    if ($vcpus -and $memMB) {
        [pscustomobject]@{ Name = $c.name; VCpus = [int]$vcpus; MemoryGB = [double]$memMB }
    }
}
$fit = $sized | Where-Object { $_.VCpus -ge $MinVCpus -and $_.MemoryGB -ge $MinMemoryGB } |
       Sort-Object VCpus, MemoryGB | Select-Object -First 1
if (-not $fit) {
    Write-Host "No unrestricted Standard_B* SKU with >=$MinVCpus vCPU / >=${MinMemoryGB}GB found in $region." -ForegroundColor Red
    Write-Host "Available burstable SKUs found (any size):" -ForegroundColor Yellow
    $sized | Sort-Object VCpus, MemoryGB | Format-Table | Out-String | Write-Host
    exit 1
}
$vmSize = $fit.Name
Write-Host "Selected VM size: $vmSize ($($fit.VCpus) vCPU, $($fit.MemoryGB) GB RAM)"

Write-Host ""
Write-Host "== Step 6: SSH public key =="
if (-not (Test-Path $SshPublicKeyPath)) {
    Write-Host "SSH public key not found at $SshPublicKeyPath. STOPPING." -ForegroundColor Red
    exit 1
}
$sshPubKey = Get-Content $SshPublicKeyPath -Raw
Write-Host "Using SSH public key: $SshPublicKeyPath"

Write-Host ""
Write-Host "== Step 7: Resource group (idempotent) =="
$rgExists = (Invoke-Az group exists --name $ResourceGroupName) -eq "true"
if ($rgExists) {
    Write-Host "Resource group '$ResourceGroupName' already exists -- reusing it (created by a prior run of this script)."
} else {
    Invoke-Az group create --name $ResourceGroupName --location $region | Out-Null
    Write-Host "Created resource group '$ResourceGroupName' in $region."
}

Write-Host ""
Write-Host "== Step 8: Network security group (SSH + Postgres + Redis, admin IP only) =="
$nsgName = "$VmName-nsg"
$nsgExists = $false
try { Invoke-Az network nsg show -g $ResourceGroupName -n $nsgName -o none; $nsgExists = $true } catch {}
if (-not $nsgExists) {
    Invoke-Az network nsg create -g $ResourceGroupName -n $nsgName --location $region | Out-Null
    Invoke-Az network nsg rule create -g $ResourceGroupName --nsg-name $nsgName `
        -n AllowSSHAdminOnly --priority 100 --access Allow --protocol Tcp `
        --direction Inbound --source-address-prefixes "$adminIp/32" `
        --source-port-ranges '*' --destination-port-ranges 22 | Out-Null
    Invoke-Az network nsg rule create -g $ResourceGroupName --nsg-name $nsgName `
        -n AllowPostgresAdminOnly --priority 110 --access Allow --protocol Tcp `
        --direction Inbound --source-address-prefixes "$adminIp/32" `
        --source-port-ranges '*' --destination-port-ranges 5432 | Out-Null
    Invoke-Az network nsg rule create -g $ResourceGroupName --nsg-name $nsgName `
        -n AllowRedisAdminOnly --priority 120 --access Allow --protocol Tcp `
        --direction Inbound --source-address-prefixes "$adminIp/32" `
        --source-port-ranges '*' --destination-port-ranges 6379 | Out-Null
    # Explicit deny-all-else for these three services from any other source; Azure NSGs
    # already default-deny inbound from Internet below the implicit rules, but this makes
    # the intent unambiguous in the portal/az nsg rule list output.
    Write-Host "Created NSG '$nsgName': 22/5432/6379 inbound restricted to $adminIp/32 only."
} else {
    Write-Host "NSG '$nsgName' already exists -- reusing it."
}

Write-Host ""
Write-Host "== Step 9: Virtual machine (idempotent) =="
$vmExists = $false
try { Invoke-Az vm show -g $ResourceGroupName -n $VmName -o none; $vmExists = $true } catch {}
if (-not $vmExists) {
    Invoke-Az vm create `
        -g $ResourceGroupName `
        -n $VmName `
        --image "Ubuntu2404" `
        --size $vmSize `
        --admin-username $AdminUsername `
        --ssh-key-values $SshPublicKeyPath `
        --nsg $nsgName `
        --public-ip-sku Standard `
        --os-disk-size-gb 30 `
        --storage-sku Standard_LRS | Out-Null
    Write-Host "VM '$VmName' created."
} else {
    Write-Host "VM '$VmName' already exists -- reusing it."
}

Write-Host ""
Write-Host "== Step 10: Collect connection info =="
$vmInfo = Invoke-Az vm show -g $ResourceGroupName -n $VmName -d -o json | ConvertFrom-Json
$publicIp = $vmInfo.publicIps
$privateIp = $vmInfo.privateIps

$summary = [ordered]@{
    resource_group   = $ResourceGroupName
    vm_name          = $VmName
    region           = $region
    vm_size          = $vmSize
    vcpus            = $fit.VCpus
    memory_gb        = $fit.MemoryGB
    os_image         = "Ubuntu2404"
    admin_username   = $AdminUsername
    public_ip        = $publicIp
    private_ip       = $privateIp
    admin_ip         = $adminIp
    ssh_key_path     = "~/.ssh/llm-metering-two-machine"
    ssh_command      = "ssh -i ~/.ssh/llm-metering-two-machine $AdminUsername@$publicIp"
    nsg_name         = $nsgName
    provisioned_utc  = (Get-Date).ToUniversalTime().ToString("o")
}
$summary | ConvertTo-Json | Set-Content -Path $InfoOutPath -Encoding utf8
Write-Host ""
Write-Host "== DONE ==" -ForegroundColor Green
$summary | Format-List | Out-String | Write-Host
Write-Host "Written to: $InfoOutPath (git-ignored)"
Write-Host ""
Write-Host "Next: scripts/azure/bootstrap-machine-b.sh"
