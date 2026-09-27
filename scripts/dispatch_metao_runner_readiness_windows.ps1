$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Repo = if ($env:METAO_GITHUB_REPOSITORY) { $env:METAO_GITHUB_REPOSITORY } else { 'oigorbrito/metaO' }
$Workflow = 'self-hosted-runner-readiness-windows.yml'
$TargetHead = if ($args.Count -gt 0) { $args[0] } elseif ($env:METAO_TARGET_HEAD) { $env:METAO_TARGET_HEAD } else { '' }

function Fail([string]$Message) { throw $Message }

if ($Repo -ne 'oigorbrito/metaO') { Fail 'METAO_GITHUB_REPOSITORY must be exactly oigorbrito/metaO' }
if ($TargetHead -notmatch '^[0-9a-fA-F]{40}$') { Fail 'provide an exact 40-character target commit SHA' }
$TargetHead = $TargetHead.ToLowerInvariant()
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { Fail 'gh CLI is required' }
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { Fail 'GitHub CLI is not authenticated' }
& gh api "repos/$Repo/commits/$TargetHead" --silent *> $null
if ($LASTEXITCODE -ne 0) { Fail "target SHA is not readable in $Repo" }

& gh workflow run $Workflow --repo $Repo --ref main --field "target_head=$TargetHead"
if ($LASTEXITCODE -ne 0) { Fail 'workflow dispatch failed' }

[ordered]@{
    dispatch='SUBMITTED'; repository=$Repo; workflow=$Workflow; workflow_ref='main';
    target_head=$TargetHead; runner_readiness='NOT_RUN'; pilot_operational_pass=$false
} | ConvertTo-Json -Compress

Write-Error "Observe with: gh run list --repo $Repo --workflow $Workflow --event workflow_dispatch --limit 5" -ErrorAction Continue
