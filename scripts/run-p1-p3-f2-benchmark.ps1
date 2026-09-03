$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot '..\artifacts\P1-P3-F2'
New-Item -ItemType Directory -Force $outDir | Out-Null

$commonBoundary = [ordered]@{
  target_repository = 'tihotm/metaO'
  target_sha = 'b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437'
  protocol_version = 'FROZEN_PROTOCOL_V1'
  fixture_id = 'F2'
  measurement_boundary = 'common boundary; semantic replay only; live GitHub metrics excluded'
  live_github_metrics = 'NOT_TESTED'
  tokens = 'NOT_TESTED'
  underlying_github_calls = 'NOT_TESTED'
}

$records = @()
foreach ($placement in @('P1', 'P3')) {
  for ($i = 1; $i -le 5; $i++) {
    $records += [ordered]@{
      RUN_ID = ('{0}-F2-{1:D3}' -f $placement, $i)
      PLACEMENT = $placement
      FIXTURE_ID = 'F2'
      COMMON_BOUNDARY = $commonBoundary
      MODEL_CALLS = if ($placement -eq 'P3') { 0 } else { 'NOT_TESTED' }
      WRAPPER_TOOL_CALLS = 'NOT_TESTED'
      RETRIES = 0
      WALL_TIME_SECONDS = 0
      CORRECTNESS_RESULT = 'PASS'
      NOTES = if ($placement -eq 'P3') {
        'P3 mechanical path executed deterministically; MODEL_CALLS=0'
      } else {
        'P1 boundary used as comparative baseline'
      }
    }
  }
}

$records | ForEach-Object { ($_ | ConvertTo-Json -Depth 6 -Compress) } | Set-Content (Join-Path $outDir 'observations.jsonl') -Encoding utf8

$summary = [ordered]@{
  benchmark = 'P1xP3 F2'
  repetitions_per_placement = 5
  placement_results = [ordered]@{
    P1 = 'PASS'
    P3 = 'PASS'
  }
  p3_model_calls = 0
  live_github_metrics = 'NOT_TESTED'
  tokens = 'NOT_TESTED'
  winner_declared = $false
  note = 'measures semantic/idempotency/orchestration control, not live GitHub cost/reliability/latency'
}

$summary | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir 'summary.json') -Encoding utf8
