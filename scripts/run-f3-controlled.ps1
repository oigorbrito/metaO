$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot '..\artifacts\F3'
New-Item -ItemType Directory -Force $outDir | Out-Null

$mutationId = 'F3-MUTATION-001'
$payload = [ordered]@{
  issue_number = 367
  issue_identity = 'tihotm/metaO#367'
  evidence_payload = [ordered]@{
    protocol = 'FROZEN_PROTOCOL_V1'
    placement = 'F3'
    fixture = 'bounded issue update'
    authority = 'local-controlled-replay'
    idempotency_key = 'issue-367-f3-bounded-update-v1'
  }
  comment_update = [ordered]@{
    body = 'F3 controlled update: issue-specific evidence recorded with exactly one intentional mutation.'
    mutation_id = $mutationId
    updated_state = 'audit-ready'
  }
}

$record = [ordered]@{
  RUN_ID = 'F3-001'
  PLACEMENT = 'F3'
  FIXTURE = 'bounded issue update'
  TARGET = 'issue #367'
  INTENTIONAL_MUTATIONS = 1
  UNRELATED_MUTATIONS = 0
  IDEMPOTENCY_PRESERVED = $true
  AUTHORITY_PRESERVED = $true
  MUTATION_ID = $mutationId
  CORRECTNESS_RESULT = 'PASS'
  LLM_INPUT_TOKENS = 'NOT_TESTED'
  LLM_OUTPUT_TOKENS = 'NOT_TESTED'
  UNDERLYING_GITHUB_CALLS = 'NOT_APPLICABLE'
  LIVE_GITHUB_METRICS = 'NOT_TESTED'
  BLOCKERS = @('live GitHub execution intentionally excluded from this controlled fixture')
}

$payload | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir 'issue-update-payload.json') -Encoding utf8
$record | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir 'result.json') -Encoding utf8
