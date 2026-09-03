# GitHub Orchestration F2 — Connected Live Observation

Status: LIVE_READ_ONLY_OBSERVATION
Governing research: #365
Observation date: 2026-09-03
Repository: `tihotm/metaO`
Frozen target commit: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
Workflow run: `33760147938`
Workflow job: `100665907672`

## Purpose

Record the fields exposed by the currently connected GitHub read boundary for frozen fixture F2 without re-running CI and without mutating repository state.

This is observation evidence for the connected GitHub path. It is not execution of the PR #364 adapter and is not a total-cost comparison.

## Read operations executed

Two connector-level read invocations were executed:

1. fetch jobs for workflow run `33760147938`;
2. fetch steps for workflow job `100665907672`.

Observed jobs response:

```text
jobs_count = 1
job.id = 100665907672
job.name = test
job.run_id = 33760147938
job.status = completed
job.conclusion = failure
job.steps = null
```

Observed job-steps response:

```text
steps = []
```

No workflow/job re-run was requested. No repository mutation was requested.

## Frozen F2 classification supported by this boundary

From the fields observed in these read responses:

```text
WORKFLOW_JOB = FAIL
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

Rationale:

- the workflow job itself completed with conclusion `failure`;
- the connected job listing exposes no steps and the dedicated step read returns an empty list;
- therefore there is no evidence that configured repository test steps executed;
- a failed workflow job before configured steps is not evidence that repository tests failed;
- product functional failure is therefore not established by this observation.

## Fields not exposed at this boundary

The connected wrappers used in this observation do not expose `runner_id` or `runner_name`.

Therefore this observation alone does not independently establish:

```text
RUNNER_ALLOCATED = NO
```

That classification remains supported by earlier direct job evidence where runner fields were observable, but it must not be re-derived from hidden prior knowledge in this boundary-specific observation.

Boundary-local state:

```text
RUNNER_ALLOCATED = NOT_TESTED_AT_THIS_BOUNDARY
```

## Request-count boundary

Observed connector/tool invocations:

```text
CONNECTED_WRAPPER_INVOCATIONS = 2
```

Do not convert that automatically into `UNDERLYING_GITHUB_CALLS = 2` unless the connector implementation or authoritative transport instrumentation proves one GitHub request per wrapper invocation.

Therefore:

```text
UNDERLYING_GITHUB_CALLS = NOT_TESTED
```

## Minimum F2 acquisition implication for PR #364

PR #364 exposes:

```text
GET /repos/{repository}/actions/runs/{run_id}
GET /repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100
```

The connected observation demonstrates that run-jobs acquisition can identify the exact target job and expose job status/conclusion. Whether the jobs-list response obtained through PR #364 also contains sufficient step information for `CONFIGURED_STEPS_EXECUTED=NO` must be established by that adapter's live response, not assumed from this connector wrapper.

Consequently the qualification should distinguish:

```text
PR364_MINIMUM_CANDIDATE_PATH = 2_DIRECT_GITHUB_READS
PR364_OPTIONAL_CONFIRMATORY_JOB_DETAIL_OR_STEPS_READ = ONLY_IF_REQUIRED_BY_OBSERVED_PAYLOAD
```

Adding a third request merely because the connected wrapper offers a dedicated steps action would bias the adapter cost upward if its two existing responses are already sufficient.

## Cost and placement impact

This observation strengthens functional decomposition:

- deterministic F2 classification requires no LLM call at this observed mechanical boundary;
- exact job failure versus repository-test execution can be preserved deterministically;
- no cross-placement cost winner follows because underlying request counts, common-boundary timing, and authoritative token telemetry remain incomplete.

Current disposition:

```text
CONNECTED_F2_LIVE_MECHANICS = PASS_FOR_OBSERVED_FIELDS
CONNECTED_F2_LIVE_FULL_FIXTURE = PARTIAL
CONNECTED_F2_MODEL_CALLS = 0_FOR_MECHANICAL_READ_CLASSIFICATION_PATH
PR364_LIVE_EXECUTION = NOT_TESTED
P1_P3_TOTAL_COST_WINNER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```
