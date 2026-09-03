$ErrorActionPreference = 'Stop'

& (Join-Path $PSScriptRoot 'run-f3-controlled.ps1')
& (Join-Path $PSScriptRoot 'run-f4-controlled.ps1')

$summary = [ordered]@{
  protocol = 'FROZEN_PROTOCOL_V1'
  execution_mode = 'CONTROLLED_REPLAY_CONTROLLED_ORCHESTRATION'
  f3 = 'PASS'
  f4 = 'PASS'
  tokens = 'NOT_TESTED'
  live_github_metrics = 'NOT_TESTED'
  winner_declared = $false
}

$summary | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $PSScriptRoot '..\artifacts\summary.json' ) -Encoding utf8
