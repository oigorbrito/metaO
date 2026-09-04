# GitHub Orchestration Live F2 Cost Packet V1

Status: FROZEN_EXECUTION_PACKET_V1
Governing research: #365
Parent protocol: `docs/GITHUB-ORCHESTRATION-COST-EXPERIMENT.md`
Replay extension: `docs/GITHUB-ORCHESTRATION-COST-REPLAY-EXTENSION-V1.md`

## Purpose

Measure live, read-only GitHub orchestration cost for the frozen F2 status-reconciliation task across P1 deterministic/direct, P2 Issue-Orchestrator, and P3 hybrid placement without changing correctness criteria or authority boundaries.

This packet is frozen before any P2/P3 live comparative measurement under this packet.

## Exact subject pins

- metaO target SHA: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
- Issue-Orchestrator: `26564aac4a02afc0989966ec2cd3e190884ba177`
- GitHub Actions run: `33760147938`
- GitHub Actions job: `100665907672`

## Frozen expected semantic outcome

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

A cheaper result that violates these distinctions is a correctness FAIL and is excluded from cost ranking.

## Placements

### P1 — deterministic/direct

Read the exact live GitHub run/job state through deterministic GitHub API/connector operations. Perform the frozen classification without LLM mediation.

### P2 — external orchestrator

Use the actual pinned Issue-Orchestrator runtime and its supported GitHub/status path. Do not replace candidate behavior with a handwritten surrogate. If the exact run/job semantics cannot be represented by the candidate-supported path, classify `BLOCKED_CAPABILITY_GAP` rather than adapting the expected result after execution.

### P3 — hybrid

Use deterministic GitHub acquisition for the exact run/job facts. Delegate only the semantic classification step to the external reasoning/orchestrator path if such delegation is actually required by the implementation under test. GitHub acquisition remains outside the model-mediated path. If no semantic reasoning call is required, record `MODEL_CALLS = 0`; do not force an LLM call merely to make P3 different from P1.

## Measurement boundary

One repetition begins immediately before the first operation required to obtain the F2 inputs and ends immediately after the frozen classification object is produced and validated.

Record per repetition:

```text
PLACEMENT
FIXTURE_ID = F2
TARGET_SHA
RUN_ID
JOB_ID
SUBJECT_PIN
EXECUTION_MODE = LIVE_GITHUB_READ_ONLY
CACHE_STATE
START_TIMESTAMP
END_TIMESTAMP
WALL_TIME_SECONDS
WRAPPER_TOOL_CALLS
UNDERLYING_GITHUB_CALLS
PRIMARY_GITHUB_REQUEST_COUNT
FALLBACK_GITHUB_REQUEST_COUNT
RETRY_COUNT
FAILED_ATTEMPTS
MODEL_PROVIDER_VERSION
MODEL_CALLS
LLM_INPUT_TOKENS
LLM_OUTPUT_TOKENS
HUMAN_CORRECTIONS
CORRECTNESS_RESULT
OBSERVED_CLASSIFICATION
RAW_ARTIFACT_POINTERS
DEVIATIONS
BLOCKERS
```

## Observability rules

- Directly observed wrapper/tool calls may be counted.
- Underlying GitHub requests are counted only when instrumented at that boundary.
- A wrapper call with unknown internal HTTP behavior is not one underlying GitHub request.
- Token usage is recorded only from authoritative provider/runtime telemetry.
- Missing token telemetry is `NOT_TESTED`, never zero.
- Timing is comparable only when all placements use the same outer measurement boundary and timer implementation.
- Connector-internal latency metadata that is unavailable to the executor or not consistently available across placements is not a comparative timing metric.

## Repetition and ordering

- Minimum 5 valid repetitions per placement before timing/reliability comparison.
- Retain all valid observations.
- Retain failed and blocked observations separately.
- No rerun-until-success filtering.
- Retry policy must be fixed before the first measured repetition for each placement and reported.
- Prefer the same machine/network session for P1/P2/P3 when technically possible.

## Correctness gate

A repetition passes only if it preserves all frozen F2 distinctions exactly or produces a semantically equivalent structured representation with an explicit mapping.

```text
FAIL != BLOCKED
NOT_TESTED != PASS
RUNNER_ALLOCATED=NO does not imply REPOSITORY_TESTS=FAIL
WORKFLOW_JOB=FAIL does not imply PRODUCT_FUNCTIONAL_FAILURE
```

## Cost interpretation

Report the vector first. Do not sum unlike units.

```text
C_vector = {
  llm_input_tokens,
  llm_output_tokens,
  model_calls,
  wrapper_tool_calls,
  underlying_github_calls,
  retries,
  failed_attempts,
  wall_time_seconds,
  human_corrections
}
```

A placement may be Pareto-dominated only on metrics that are actually comparable and observed.

No monetized total is allowed without pinned, dated conversion factors.

## Existing P1/F1 repeated observation

Before this packet was frozen, the already-governed P1/F1 read-only fixture was repeated five times through the authenticated connector. All five repetitions returned Issue #365 with the expected identity and `docs/EMPIRICAL-RESEARCH-AND-REPRODUCIBILITY.md` at baseline pin `b57017...` with blob `8ab20fd9870ae88da186d1ac0ad54b5e8296ca36`.

This supports bounded P1/F1 repeatable correctness only. It does not provide a cross-placement cost result. Accepted comparable wall-time telemetry was not exposed at the protocol boundary, so P1/F1 timing remains `NOT_TESTED`.

## Authority invariants

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
SECOND_METAO_CORE = NO
SECOND_POLICY_AUTHORITY = NO
SECOND_DURABLE_WORKFLOW_AUTHORITY = NO
SECOND_EVIDENCE_AUTHORITY = NO
SECOND_ACCEPTANCE_AUTHORITY = NO
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Pre-execution state

```text
P1_F2_LIVE_COST_PACKET = READY
P2_F2_LIVE_COST_PACKET = READY_IF_RUNTIME_AND_AUTH_AVAILABLE
P3_F2_LIVE_COST_PACKET = READY_IF_RUNTIME_AND_AUTH_AVAILABLE
P1_VS_P2_VS_P3_LIVE_COST_WINNER = NOT_TESTED
TOKEN_COMPARISON = NOT_TESTED
UNDERLYING_GITHUB_REQUEST_COMPARISON = NOT_TESTED
LIVE_TIMING_COMPARISON = NOT_TESTED
MONETIZED_TOTAL_COST = NOT_TESTED
```
