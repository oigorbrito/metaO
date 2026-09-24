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

## Revalidation on current main

On 2026-09-24, the exact run and jobs REST reads were repeated from current main
`5624bb9de6109119f762487a86b064b8dc416637` without mutation:

```text
RUN_ID = 33760147938
JOB_ID = 100665907672
RUN_HEAD_SHA = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
RUN_STATUS = completed
RUN_CONCLUSION = failure
JOB_STATUS = completed
JOB_CONCLUSION = failure
RUNNER_ID = 0
RUNNER_NAME = empty
STEPS_COUNT = 0
READ_INVOCATIONS = 2 (run lookup + jobs lookup)
MUTATIONS = 0
```

The bounded classification remains `HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP`;
`REPOSITORY_TESTS = NOT_TESTED` and `PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN`.
This revalidation does not establish comparable cost, latency, reliability, token
usage, or a placement winner.

## Read operations executed

Three connector-level read invocations were attempted:

1. fetch jobs for workflow run `33760147938`;
2. fetch steps for workflow job `100665907672`;
3. fetch decoded logs for workflow job `100665907672`.

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

Observed job-log response:

```text
HTTP = 404
ERROR_CODE = BlobNotFound
LOG_RECEIPT_AVAILABLE = NO
```

The log read failed because the backing log blob does not exist. This is retained as an observed read failure; it is not a repository functional failure.

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
- no job log receipt is available (`404 BlobNotFound`);
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
CONNECTED_WRAPPER_INVOCATIONS_SUCCESSFUL = 2
CONNECTED_WRAPPER_INVOCATIONS_FAILED = 1
```

The failed log read is not part of the minimum functional F2 acquisition path; it was an evidence-probing read after the classification-relevant job/steps observations.

Do not convert connector invocations automatically into underlying GitHub request counts unless the connector implementation or authoritative transport instrumentation proves the mapping.

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
LOG_READ = NOT_REQUIRED_FOR_MINIMUM_F2_AND_CURRENTLY_UNAVAILABLE
```

Adding a third request merely because another observation surface exists would bias the adapter cost upward if its two existing responses are already sufficient.

## Cost and placement impact

This observation strengthens functional decomposition:

- deterministic F2 classification requires no LLM call at this observed mechanical boundary;
- exact job failure versus repository-test execution can be preserved deterministically;
- lack of logs does not require an LLM fallback and must remain an evidence-state condition;
- no cross-placement cost winner follows because underlying request counts, common-boundary timing, and authoritative token telemetry remain incomplete.

Current disposition:

```text
CONNECTED_F2_LIVE_MECHANICS = PASS_FOR_OBSERVED_FIELDS
CONNECTED_F2_LIVE_FULL_FIXTURE = PARTIAL
CONNECTED_F2_MODEL_CALLS = 0_FOR_MECHANICAL_READ_CLASSIFICATION_PATH
CONNECTED_F2_LOG_READ = BLOCKED_MISSING_BLOB
PR364_LIVE_EXECUTION = NOT_TESTED
P1_P3_TOTAL_COST_WINNER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```
