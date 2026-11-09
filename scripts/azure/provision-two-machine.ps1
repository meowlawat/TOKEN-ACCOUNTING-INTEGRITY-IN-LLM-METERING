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
    # Deliberately a BASIC function (no [Parameter()]/[CmdletBinding()]), using the
    # automatic $args variable rather than a named ValueFromRemainingArguments parameter.
    # Root cause of an earlier, confusing failure: a named parameter attribute makes this
    # an "advanced" function, which gets PowerShell's automatic common parameters
    # (-OutVariable, -OutBuffer, ...) -- and `-o` (az's short form of --output) is
    # ambiguous with -OutVariable, so EVERY call like `Invoke-Az account show -o json`
    # threw "Parameter cannot be processed because the parameter name 'o' is ambiguous"
    # before the function body ever ran, which looked identical to "not authenticated"
    # in the catch block below. Also: do not merge stderr via 2>&1 -- with
    # $ErrorActionPreference = "Stop", PowerShell 5.1 wraps each stderr line from a
    # native exe in a terminating NativeCommandError even on exit 0 (az CLI routinely
    # writes informational text to stderr on success).
    # The script sets $ErrorActionPreference = "Stop" globally. Under that setting,
    # PowerShell 5.1 treats ANY stderr line from a native exe as a terminating error --
    # merely redirecting it (2>&1, 2>$null, anywhere) does not prevent this; the
    # redirect target only controls where the TEXT goes, not whether receiving stderr at
    # all raises. az CLI routinely writes benign warnings to stderr (e.g. "resource
    # provider not registered, registering for you") even on ultimate success, so this
    # was turning normal az output into a false "not authenticated" / false failure at
    # arbitrary later steps. Fix: locally relax EAP to Continue for just this call.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $az @args 2>$null
    $ErrorActionPreference = $prevEap
    if ($LASTEXITCODE -ne 0) {
        throw "az $($args -join ' ') failed (exit $LASTEXITCODE):`n$out"
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
# KNOWN ISSUE (observed in practice): some ISPs rotate the visible public IP via CGNAT on
# a timescale of ~1-2 minutes -- faster than a script can detect-and-refresh a /32 NSG
# rule. If SSH/Postgres/Redis connectivity mysteriously times out shortly after this step,
# check `curl https://api.ipify.org` against the NSG rules' current source prefix before
# assuming a code bug. The fix applied in one such case was a deliberate, user-approved
# widening of the NSG source range to the ISP's observed CGNAT block (e.g. a /21) instead
# of a single /32 -- NOT something this script does automatically, since it trades off the
# "restricted to actual administrator IP" requirement and needs an explicit decision.

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
# `az vm list-skus` returns per-subscription restriction metadata, which is what the
# first version of this script used to pick a guaranteed-available SKU -- but on this
# subscription/region it measured 87-200+ seconds (confirmed by direct timing, three
# separate runs), apparently server-side/Azure-API latency for that specific endpoint,
# not a problem in the PowerShell filtering logic (confirmed separately: ConvertFrom-Json
# took 0.4s and the filter took 0.006s on the same payload once it arrived). `az vm
# list-sizes` returns the same name/vCPU/memory facts without restriction metadata, in
# ~2.6 seconds. Trade-off: it can't tell us in advance whether THIS subscription is
# restricted from a given SKU -- so instead of filtering for that up front, Step 9
# (VM create) tries each size in priority order and falls back on a restriction error.
$sizesRaw = Invoke-Az vm list-sizes --location $region -o json
$sizes = $sizesRaw | ConvertFrom-Json
$sized = foreach ($s in $sizes) {
    if ($s.name -like 'Standard_B*' -and $s.name -notmatch 'pts_v|pls_v|pds_v') {
        [pscustomobject]@{ Name = $s.name; VCpus = [int]$s.numberOfCores; MemoryGB = [double]($s.memoryInMB / 1024) }
    }
}
$fits = $sized | Where-Object { $_.VCpus -ge $MinVCpus -and $_.MemoryGB -ge $MinMemoryGB } |
        Sort-Object VCpus, MemoryGB
if (-not $fits) {
    Write-Host "No Standard_B* SKU with >=$MinVCpus vCPU / >=${MinMemoryGB}GB found in $region." -ForegroundColor Red
    exit 1
}
Write-Host "Candidate VM sizes (cheapest first), to be tried in order at create time:"
foreach ($f in $fits) { Write-Host "  - $($f.Name) ($($f.VCpus) vCPU, $($f.MemoryGB) GB RAM)" }
$vmSizeCandidates = $fits.Name

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
    Write-Host "Created NSG '$nsgName'."
} else {
    Write-Host "NSG '$nsgName' already exists -- reusing it."
}

# Idempotency is per-RULE, not per-NSG: an earlier run can create the bare NSG and then
# fail before any rule exists (observed in practice -- a prior run left this NSG with zero
# custom rules, silently blocking SSH for days because the NSG-existence check above
# skipped rule creation on every subsequent re-run). Check and create each rule
# individually so a partial prior failure is always completed on the next run.
$requiredRules = @(
    @{ Name = "AllowSSHAdminOnly";      Priority = 100; Port = 22   },
    @{ Name = "AllowPostgresAdminOnly"; Priority = 110; Port = 5432 },
    @{ Name = "AllowRedisAdminOnly";    Priority = 120; Port = 6379 }
)
foreach ($rule in $requiredRules) {
    $ruleExists = $false
    try { Invoke-Az network nsg rule show -g $ResourceGroupName --nsg-name $nsgName -n $rule.Name -o none; $ruleExists = $true } catch {}
    if ($ruleExists) {
        Invoke-Az network nsg rule update -g $ResourceGroupName --nsg-name $nsgName `
            -n $rule.Name --source-address-prefixes "$adminIp/32" -o none
        Write-Host "Rule '$($rule.Name)' already existed -- refreshed to $adminIp/32."
    } else {
        Invoke-Az network nsg rule create -g $ResourceGroupName --nsg-name $nsgName `
            -n $rule.Name --priority $rule.Priority --access Allow --protocol Tcp `
            --direction Inbound --source-address-prefixes "$adminIp/32" `
            --source-port-ranges '*' --destination-port-ranges $rule.Port -o none
        Write-Host "Created rule '$($rule.Name)' (port $($rule.Port)) restricted to $adminIp/32."
    }
}

Write-Host ""
Write-Host "== Step 9: Virtual machine (idempotent, tries candidate sizes in order) =="
$vmExists = $false
try { $existing = Invoke-Az vm show -g $ResourceGroupName -n $VmName -o json | ConvertFrom-Json; $vmExists = $true } catch {}
if ($vmExists) {
    $vmSize = $existing.hardwareProfile.vmSize
    Write-Host "VM '$VmName' already exists -- reusing it (size: $vmSize)."
} else {
    $vmSize = $null
    foreach ($candidate in $vmSizeCandidates) {
        Write-Host "Trying size $candidate ..."
        try {
            Invoke-Az vm create `
                -g $ResourceGroupName `
                -n $VmName `
                --image "Ubuntu2404" `
                --size $candidate `
                --admin-username $AdminUsername `
                --ssh-key-values $SshPublicKeyPath `
                --nsg $nsgName `
                --public-ip-sku Standard `
                --os-disk-size-gb 30 `
                --storage-sku Standard_LRS | Out-Null
            $vmSize = $candidate
            Write-Host "VM '$VmName' created with size $candidate."
            break
        } catch {
            $firstLine = ($_.Exception.Message -split "`n")[0]
            Write-Host "  $candidate failed (likely restricted for this subscription/region): $firstLine" -ForegroundColor Yellow
            continue
        }
    }
    if (-not $vmSize) {
        Write-Host "All candidate sizes failed. STOPPING -- this needs your decision (quota/offer restriction)." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "== Step 10: Collect connection info =="
$vmInfo = Invoke-Az vm show -g $ResourceGroupName -n $VmName -d -o json | ConvertFrom-Json
$publicIp = $vmInfo.publicIps
$privateIp = $vmInfo.privateIps

$vmSizeInfo = $sized | Where-Object { $_.Name -eq $vmSize } | Select-Object -First 1
$summary = [ordered]@{
    resource_group   = $ResourceGroupName
    vm_name          = $VmName
    region           = $region
    vm_size          = $vmSize
    vcpus            = $vmSizeInfo.VCpus
    memory_gb        = $vmSizeInfo.MemoryGB
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
