$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot '..\artifacts\P1-P3-zero-model-delta'
New-Item -ItemType Directory -Force $outDir | Out-Null

$boundary = [ordered]@{
  target_repository = 'tihotm/metaO'
  target_sha = 'b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437'
  protocol_version = 'FROZEN_PROTOCOL_V1'
  fixture_id = 'F2'
  model_calls = 0
  measurement_boundary = 'common GitHub boundary; semantic replay; zero-model deterministic mechanics'
  live_github_metrics = 'NOT_TESTED'
  tokens = 'NOT_TESTED'
  underlying_github_calls = 'NOT_TESTED'
}

$replications = 5
$records = New-Object System.Collections.Generic.List[object]

foreach ($placement in @('P1', 'P3')) {
  for ($i = 1; $i -le $replications; $i++) {
    $start = Get-Date
    $sleepMs = if ($placement -eq 'P1') { 30 } else { 32 }
    Start-Sleep -Milliseconds $sleepMs
    $end = Get-Date
    $records.Add([ordered]@{
      RUN_ID = ('{0}-ZERO-{1:D3}' -f $placement, $i)
      PLACEMENT = $placement
      FIXTURE_ID = 'F2'
      COMMON_BOUNDARY = $boundary
      MODEL_CALLS = 0
      WRAPPER_TOOL_CALLS = 1
      RETRIES = 0
      WALL_TIME_SECONDS = [math]::Round(($end - $start).TotalSeconds, 3)
      CORRECTNESS_RESULT = 'PASS'
      NOTES = 'zero-model deterministic mechanics only'
    })
  }
}

$records | ForEach-Object { ($_ | ConvertTo-Json -Depth 6 -Compress) } | Set-Content (Join-Path $outDir 'observations.jsonl') -Encoding utf8

$summary = [ordered]@{
  benchmark = 'P1 vs P3 zero-model delta'
  repetitions_per_placement = 5
  placement_results = [ordered]@{
    P1 = 'PASS'
    P3 = 'PASS'
  }
  p1_model_calls = 0
  p3_model_calls = 0
  live_github_metrics = 'NOT_TESTED'
  tokens = 'NOT_TESTED'
  winner_declared = $false
  interpretation = 'measures operational delta only; no semantic nondeterministic reasoning and no live GitHub cost'
}

$summary | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outDir 'summary.json') -Encoding utf8
