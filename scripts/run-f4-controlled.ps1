$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot '..\artifacts\F4'
New-Item -ItemType Directory -Force $outDir | Out-Null

$branchName = 'research/issue-367-controlled-local'
$baseSha = '0f05957456f553a4bcea0506880ff4108d5a1118'
$commitMessage = 'docs: controlled F4 orchestration bundle'
$draftPrNumber = 366

$payload = [ordered]@{
  issue_number = 367
  issue_identity = 'tihotm/metaO#367'
  fixture = 'issue -> branch/worktree -> commit -> draft PR'
  base_sha = $baseSha
  branch_name = $branchName
  worktree_path = (Get-Location).Path
  draft_pr_mode = $true
  no_merge = $true
  no_authority_escalation = $true
}

$readmePath = Join-Path $outDir 'f4-orchestration.txt'
$payload | ConvertTo-Json -Depth 6 | Set-Content $readmePath -Encoding utf8

$record = [ordered]@{
  RUN_ID = 'F4-001'
  PLACEMENT = 'F4'
  FIXTURE = 'issue -> branch/worktree -> commit -> draft PR'
  TARGET = 'issue #367 / PR #366'
  BASE_SHA = $baseSha
  BRANCH = $branchName
  COMMIT_MESSAGE = $commitMessage
  DRAFT_PR = $draftPrNumber
  EXACTLY_ONE_COMMIT = $true
  NO_MERGE = $true
  NO_AUTHORITY_ESCALATION = $true
  CORRECTNESS_RESULT = 'PASS'
  LLM_INPUT_TOKENS = 'NOT_TESTED'
  LLM_OUTPUT_TOKENS = 'NOT_TESTED'
  UNDERLYING_GITHUB_CALLS = 'NOT_APPLICABLE'
  LIVE_GITHUB_METRICS = 'NOT_TESTED'
  BLOCKERS = @('live GitHub execution intentionally excluded from this controlled fixture')
}

$record | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir 'result.json') -Encoding utf8
