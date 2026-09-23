$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Repo = 'oigorbrito/metaO'
$Workflow = 'project-multi-provider-pilot-windows-fenced.yml'
$AuditedHead = 'ccb0c93d761ad0598ea1d9dcc76476cb0a73a861'
$Authorization = if ($args.Count -gt 0) { $args[0] } else { '' }
$OpenAIModel = if ($args.Count -gt 1) { $args[1] } else { 'gpt-5.6-luna' }
$GeminiTarget = if ($args.Count -gt 2) { $args[2] } else { 'gemma-4-26b-a4b-it' }

if ($Authorization -ne 'I_AUTHORIZE_METAO_MULTI_PROVIDER_PROJECT_PILOT') {
    throw 'first argument must be the exact pilot authorization string'
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'gh CLI is required' }
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI is not authenticated' }
& gh api "repos/$Repo/commits/$AuditedHead" --silent *> $null
if ($LASTEXITCODE -ne 0) { throw 'audited pilot SHA is not readable' }

& gh workflow run $Workflow `
    --repo $Repo `
    --ref main `
    --field "authorization=$Authorization" `
    --field "expected_head=$AuditedHead" `
    --field "openai_model=$OpenAIModel" `
    --field "gemini_target=$GeminiTarget"
if ($LASTEXITCODE -ne 0) { throw 'Windows credential-backed pilot dispatch failed' }

[ordered]@{
    dispatch='SUBMITTED'
    repository=$Repo
    workflow=$Workflow
    workflow_ref='main'
    audited_head=$AuditedHead
    runner_os='Windows'
    operational_pilot='NOT_RUN'
    project_operational_pass=$false
} | ConvertTo-Json -Compress

Write-Error "Observe with: gh run list --repo $Repo --workflow $Workflow --event workflow_dispatch --limit 5" -ErrorAction Continue
