# GitHub Orchestration — Internal Adapter F2 Qualification V1

Status: FROZEN_EXECUTION_PACKET_V1_WITH_REST_ORACLE
Governing research: #365
Execution handoff: #367
Internal donor source: PR #364
Internal donor branch: `feat/github-governed-adapter`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`
Target research branch baseline at original freeze: `5a0a4e0868a891492f880c87df7fdcaef10f6500`

## Purpose

Qualify the minimum deterministic GitHub Actions read slice from PR #364 against frozen F2 semantics before product adoption or broader mutation-surface port.

This packet does not authorize merging PR #364 or importing its complete history.

## Frozen source slice

Initial F2 qualification may port only:

- `GitHubAdapterError`
- `GitHubTransport`
- `UrllibGitHubTransport`
- exact workflow-run GET by run identity
- exact workflow-jobs GET by run identity

Excluded unless mechanically required:

- issue/branch/file/PR mutations
- comments/reviews/merge
- mutation authorization
- old #364 cost protocol
- old #364 CI workflow

## Frozen F2 identity

```text
repository = tihotm/metaO
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
workflow_run = 33760147938
workflow_job = 100665907672
```

Expected classification:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

## Live REST oracle acquired after packet freeze

The exact two REST endpoint shapes already implemented in PR #364 were subsequently read live, without mutation and without CI rerun.

Run endpoint observed:

```text
id = 33760147938
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
status = completed
conclusion = failure
run_attempt = 6
```

Jobs endpoint observed:

```text
total_count = 1
job.id = 100665907672
job.run_id = 33760147938
job.head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
job.status = completed
job.conclusion = failure
job.steps = []
job.runner_id = 0
job.runner_name = ""
```

Therefore, for the frozen fixture:

```text
TWO_PR364_REST_ROUTES_SEMANTICALLY_SUFFICIENT = YES
THIRD_JOB_STEPS_REQUEST_REQUIRED = NO
JOB_LOG_REQUEST_REQUIRED = NO
```

This closes the source/payload capability question. It does not replace execution of the transplanted Python implementation.

## Correctness gate

The minimal implementation under test must perform no more than the two declared REST acquisitions for the basic F2 path unless an observed transport failure requires a recorded retry.

Required assertions:

```text
workflow_run.id == 33760147938
workflow_run.head_sha == b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
workflow_job.id == 100665907672
workflow_job.run_id == 33760147938
workflow_job.head_sha == b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
workflow_job.status == completed
workflow_job.conclusion == failure
workflow_job.runner_id == 0
workflow_job.runner_name == ""
workflow_job.steps == []
```

The classifier must produce:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

A failed job must not become repository-test FAIL when no configured steps executed.

## Execution sequence

1. branch from current remote research head or current `main` as appropriate for the qualification worktree;
2. import/adapt only the minimum F2 read slice from exact donor pin;
3. add focused fake-transport tests using the exact oracle payload shape;
4. execute focused tests;
5. execute repository unit regression gate;
6. if authenticated REST is available, execute the two GETs through the transplanted adapter;
7. instrument actual transport request count;
8. retain sanitized raw output and deviations;
9. record git status after execution;
10. commit one coherent qualification unit only after PASS or explicitly preserve FAIL/BLOCKED.

## Required unit tests

At minimum:

- exact workflow-run route;
- exact workflow-jobs route;
- exact job-id/head-sha selection;
- runner allocation classification;
- empty-steps classification;
- failure does not imply repository-test failure;
- transport error propagation;
- invalid input rejected before transport where applicable;
- no mutation surface required for F2.

## Repetition and cost

One deterministic fake-transport run can establish structural correctness. One live acquisition can establish functional acquisition for this immutable fixture.

Timing/reliability claims require at least five comparable repetitions.

Cost remains a vector:

```text
C_vector = {
  model_calls,
  llm_input_tokens,
  llm_output_tokens,
  underlying_github_calls,
  retries,
  failed_attempts,
  wall_time_seconds,
  human_corrections
}
```

For the minimal deterministic F2 path:

```text
EXPECTED_MODEL_CALLS = 0
DECLARED_BASE_TRANSPORT_REQUESTS = 2
```

Actual execution must confirm the request count and any retries.

## Acceptance states

```text
INTERNAL_DONOR_SOURCE_PINNED = YES
TWO_ROUTE_REST_ORACLE = PASS
TWO_ROUTE_F2_SEMANTIC_SUFFICIENCY = PASS_FOR_FROZEN_FIXTURE
MINIMAL_SLICE_PORTED = NOT_TESTED
FOCUSED_UNIT_TESTS = NOT_TESTED
UNIT_REGRESSION = NOT_TESTED
LIVE_ADAPTER_F2_ACQUISITION = NOT_TESTED
LIVE_ADAPTER_REQUEST_COUNT = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Decision rule

If the transplanted slice passes current-head tests and reproduces the two-response live classification, the internal donor becomes `EXECUTED_IN_METAO_FIXTURE` evidence for deterministic F2 mechanics. That still does not authorize broader #364 adoption or decide P1/P3 total cost.

If it fails, classify the cause: adaptation regression, donor defect, current-base incompatibility, authentication/environment blocker, retry/transport behavior, or semantic classifier defect.
