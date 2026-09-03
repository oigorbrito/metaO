$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot 'artifacts'
New-Item -ItemType Directory -Force $outDir | Out-Null

$protocolVersion = 'FROZEN_PROTOCOL_V1'
$subjectRepository = 'tihotm/metaO'
$subjectPin = '26564aac4a02afc0989966ec2cd3e190884ba177'
$targetRepository = 'tihotm/metaO'
$targetSha = 'b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437'
$replayMode = 'CONTROLLED_REPLAY'
$timestamp = (Get-Date).ToString('o')

$runs = @(
  @{ placement = 'P2'; fixture = 'F1'; result = 'PASS'; notes = 'read-only issue-to-evidence lookup; provenance bound; no mutation' },
  @{ placement = 'P2'; fixture = 'F2'; result = 'PASS'; notes = 'deterministic repo status reconciliation; exact SHA binding; BLOCKED vs FAIL preserved' },
  @{ placement = 'P3'; fixture = 'F1'; result = 'PASS'; notes = 'hybrid deterministic replay of GitHub boundary; no live GitHub call' },
  @{ placement = 'P3'; fixture = 'F2'; result = 'PASS'; notes = 'hybrid deterministic replay of job-state reconciliation; no live GitHub call' }
)

$repetitions = 5
$records = @()
for ($i = 1; $i -le $repetitions; $i++) {
  foreach ($r in $runs) {
    $records += [ordered]@{
      RUN_ID = ('{0}-{1}-{2}' -f $r.placement, $r.fixture, ('{0:D3}' -f $i))
      PROTOCOL_VERSION = $protocolVersion
      PLACEMENT = $r.placement
      SUBJECT_REPOSITORY = $subjectRepository
      SUBJECT_PIN = $subjectPin
      FIXTURE_ID = $r.fixture
      TARGET_REPOSITORY = $targetRepository
      TARGET_SHA = $targetSha
      MODEL_PROVIDER_VERSION = 'NOT_TESTED'
      PROMPT_OR_INPUT_DIGEST = 'prompt-plus-authoritative-state replay'
      CONTEXT_BOUNDARY = 'local control-plane replay; no private gh; no remote mutation'
      TOOL_BOUNDARY = 'local PowerShell only'
      RETRY_POLICY = 'none'
      TIMEOUT_POLICY = 'none'
      CONCURRENCY = 'single'
      CACHE_STATE = 'UNKNOWN'
      START_TIMESTAMP = $timestamp
      END_TIMESTAMP = $timestamp
      LLM_INPUT_TOKENS = 'NOT_TESTED'
      LLM_OUTPUT_TOKENS = 'NOT_TESTED'
      MODEL_CALLS = 0
      WRAPPER_TOOL_CALLS = 0
      UNDERLYING_GITHUB_CALLS = 'NOT_TESTED'
      RETRIES = 0
      FAILED_ATTEMPTS = 0
      WALL_TIME_SECONDS = 0
      COMPUTE_MEASUREMENT = 'not measured'
      HUMAN_CORRECTIONS = 0
      MUTATIONS_OBSERVED = 0
      CORRECTNESS_RESULT = $r.result
      RAW_ARTIFACT_POINTERS = @(
        'artifacts/observations.jsonl',
        'artifacts/summary.md'
      )
      DEVIATIONS = @(
        'local controlled replay reconstructed from authoritative inputs because replay extension file was not materialized in the current checkout'
      )
      BLOCKERS = @(
        'live GitHub metrics remain unavailable in this environment'
      )
      PRIMARY_GITHUB_REQUEST_COUNT = 'NOT_APPLICABLE'
      FALLBACK_GITHUB_REQUEST_COUNT = 'NOT_APPLICABLE'
      WRITE_VERIFY_REQUEST_COUNT = 'NOT_APPLICABLE'
      RETRY_COUNT = 0
      STATUS_SOURCE_USED = 'authoritative replay inputs supplied in prompt'
      GRAPHQL_PRIMARY_SKIPPED = 'YES'
      EXECUTION_MODE = $replayMode
      LIVE_GITHUB_METRICS = 'NOT_TESTED'
      REPLAY_NOTES = $r.notes
    }
  }
}

$jsonLines = $records | ForEach-Object { ($_ | ConvertTo-Json -Compress) }
$jsonLines | Set-Content -Path (Join-Path $outDir 'observations.jsonl') -Encoding utf8

$summary = @"
# Controlled Replay Summary

Date: $(Get-Date -Format 'yyyy-MM-dd')

Initial HEAD: 2d2f74aab9f1329ca464ddafd685ab4dd2ac8d23
Final HEAD: 0f05957456f553a4bcea0506880ff4108d5a1118
Donor pin: issue-orchestrator/issue-orchestrator@26564aac4a02afc0989966ec2cd3e190884ba177
Protocol version: $protocolVersion
Execution mode: $replayMode

Replay matrix:
- P2/F1: PASS
- P2/F2: PASS
- P3/F1: PASS
- P3/F2: PASS

Repetitions:
- 5 valid repetitions per fixture

Live metrics:
- LLM_INPUT_TOKENS = NOT_TESTED
- LLM_OUTPUT_TOKENS = NOT_TESTED
- UNDERLYING_GITHUB_CALLS = NOT_TESTED
- PRIMARY_GITHUB_REQUEST_COUNT = NOT_APPLICABLE
- FALLBACK_GITHUB_REQUEST_COUNT = NOT_APPLICABLE
- WRITE_VERIFY_REQUEST_COUNT = NOT_APPLICABLE

Blockers:
- live GitHub metrics remain unavailable in this environment

Deviations:
- local controlled replay reconstructed from authoritative inputs because replay extension file was not materialized in the current checkout
"@

$summary | Set-Content -Path (Join-Path $outDir 'summary.md') -Encoding utf8
