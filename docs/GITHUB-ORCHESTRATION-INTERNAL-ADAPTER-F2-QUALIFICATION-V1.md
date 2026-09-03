# GitHub Orchestration — Internal Adapter F2 Qualification V1

Status: FROZEN_EXECUTION_PACKET_V1
Governing research: #365
Execution handoff: #367
Internal donor source: PR #364
Internal donor branch: `feat/github-governed-adapter`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`
Target research branch baseline: `research/issue-365-github-orchestration-cost`
Frozen target baseline SHA at packet creation: `5a0a4e0868a891492f880c87df7fdcaef10f6500`

## Purpose

Qualify the minimum deterministic GitHub Actions read slice from the internal experimental adapter in PR #364 against the already frozen F2 semantics before any product adoption or broader mutation-surface port.

This packet does not authorize merging PR #364, does not authorize porting its complete history, and does not change the product placement decision.

## Subject classification

`src/metao/github_adapter.py` is absent from `main` at the time this packet is frozen. Therefore PR #364 is treated as an INTERNAL_DONOR_CODE subject rather than current product code.

Required evidence implications:

```text
CODE_PRESENT_IN_EXPERIMENTAL_BRANCH != CODE_PRESENT_IN_MAIN
CODE_CONFIRMED != EXECUTED
EXECUTED_ON_OLD_BRANCH != QUALIFIED_ON_CURRENT_BASELINE
INTERNAL_DONOR_REUSE != MERGE_DONOR_BRANCH
```

## Frozen source slice

Source must be taken from exact pin `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`.

Initial F2 qualification may port only the minimum read-only concepts required for exact workflow run/job acquisition:

- `GitHubAdapterError`
- `GitHubTransport`
- `UrllibGitHubTransport`
- exact workflow-run GET by run identity
- exact workflow-jobs GET by run identity

The implementation may be reduced or reshaped only to fit the current repository boundary. Any semantic change from the donor source must be recorded as an adaptation.

Excluded from the initial F2 qualification slice unless mechanically required by imports:

- issue mutation
- branch creation
- file creation
- pull-request creation
- PR comments/reviews
- merge operations
- mutation authorization classes
- old PR #364 cost protocol
- old PR #364 CI workflow

## Frozen F2 identity

Repository: `tihotm/metaO`
Target commit SHA: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
Workflow run: `33760147938`
Workflow job: `100665907672`

Expected classification:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

If the ported adapter cannot expose sufficient fields for an expected classification member, that member must be `NOT_TESTED` or the run must be classified `PARTIAL`; it must not be fabricated from hidden prior knowledge.

## Correctness gate

Cheaper or faster incorrect acquisition is FAIL and excluded from cost ranking.

Minimum acquisition assertions:

```text
workflow_run.id == 33760147938
workflow_run.head_sha == b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
workflow_job.id == 100665907672
workflow_job.run_id == 33760147938
workflow_job.status == completed
workflow_job.conclusion == failure
```

Configured-step execution must be derived only from returned run/job evidence available to the implementation under test.

## Isolation rules

- no live mutation;
- no issue/PR creation probes;
- no merge;
- no authority escalation;
- no fallback to handwritten expected fixture after a live acquisition failure;
- no use of the external Issue-Orchestrator subject as a surrogate;
- retain all failed/blocked attempts.

## Execution sequence

1. branch from current remote research head;
2. import/adapt minimum F2 read slice from exact internal donor pin;
3. add focused unit tests using deterministic fake transport;
4. execute focused tests;
5. execute repository unit regression gate;
6. if authenticated live GitHub access is available, execute frozen F2 read-only acquisition;
7. retain raw output and deviations;
8. record git status after execution;
9. create one coherent commit only after successful direct/regression gates or explicitly record BLOCKED/FAIL.

## Required unit tests

At minimum:

- exact workflow-run route;
- exact workflow-jobs route;
- no mutation surface needed for read qualification;
- transport error propagation;
- invalid input rejected before transport where applicable;
- returned payload is not rewritten into product PASS semantics.

## Repetition and cost

A single exact deterministic unit run can establish structural correctness for immutable fake-transport cases.

Any live timing/reliability comparison requires at least five valid repetitions at a common outer boundary with P1/P3.

Cost output remains a vector. No heterogeneous scalar total is authorized without dated conversion factors.

```text
C_vector = {
  model_calls,
  llm_input_tokens,
  llm_output_tokens,
  wrapper_tool_calls,
  underlying_github_calls,
  retries,
  failed_attempts,
  wall_time_seconds,
  human_corrections
}
```

For the deterministic read slice, model invocation is not required merely to preserve a hybrid label. If no model call occurs, record `MODEL_CALLS = 0` for that exact path; do not generalize to other workloads.

## Acceptance states

```text
INTERNAL_DONOR_SOURCE_PINNED = YES
MINIMAL_SLICE_PORTED = NOT_TESTED
FOCUSED_UNIT_TESTS = NOT_TESTED
UNIT_REGRESSION = NOT_TESTED
LIVE_F2_ACQUISITION = NOT_TESTED
FROZEN_F2_CLASSIFICATION = NOT_TESTED
P1_P3_COST_COMPARISON_CHANGED = NO
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Decision rule

If the minimal slice qualifies, it becomes evidence that deterministic GitHub Actions acquisition can be implemented inside the metaO GitHub boundary with a small internal donor-derived surface. It does not by itself authorize broader PR #364 adoption.

If the minimal slice fails, diagnose whether the cause is adaptation regression, donor defect, current-base incompatibility, authentication/environment blocker, or missing semantic field. Do not convert the entire donor to FAIL without causal evidence.
