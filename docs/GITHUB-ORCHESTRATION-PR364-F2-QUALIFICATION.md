# PR #364 GitHub Adapter — Frozen F2 Qualification

Status: SOURCE_QUALIFICATION_PLUS_LIVE_REST_ORACLE
Governing research: #365
Subject: metaO PR #364 `feat/github-governed-adapter`
Subject pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`
Frozen metaO baseline: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`

## Question

Does the already-existing adapter implementation in PR #364 contain the deterministic GitHub Actions mechanics required to execute frozen fixture F2 without inventing a second adapter?

This qualification does not authorize merging PR #364. Source inspection is combined here with a read-only live REST oracle against the exact endpoints that PR #364 would call; execution of the PR #364 Python implementation itself remains NOT_TESTED.

## Repository relationship

Direct compare of current frozen baseline to PR #364 head:

```text
status = DIVERGED
merge_base = 2710a2580f6510c479e19c24b6dd4ee491bcdbc9
ahead_by = 11
behind_by = 8
changed_files = 9
```

Therefore:

```text
BLIND_MERGE = FORBIDDEN
BLIND_REBASE_ASSUMED_SAFE = NO
CURRENT_HEAD_QUALIFICATION_REQUIRED = YES
```

## PR #364 source mapping

At subject pin `1c9a9728...`, `src/metao/github_adapter.py` contains:

```text
workflow_run(repository, run_id)
  GET repos/{repository}/actions/runs/{run_id}

list_workflow_jobs(repository, run_id, filter="latest", per_page=100)
  GET repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100
```

The transport returns decoded GitHub JSON without normalizing read payloads, so fields supplied by GitHub remain available to the caller.

## Live REST oracle for the exact PR #364 routes

Read-only GitHub REST calls were executed against the exact frozen identities and exact endpoint shapes used by PR #364.

### GET 1 — workflow run

```text
GET /repos/tihotm/metaO/actions/runs/33760147938
```

Observed relevant fields:

```text
id = 33760147938
head_branch = main
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
status = completed
conclusion = failure
run_attempt = 6
event = push
```

### GET 2 — run jobs

```text
GET /repos/tihotm/metaO/actions/runs/33760147938/jobs?filter=latest&per_page=100
```

Observed relevant fields:

```text
total_count = 1
job.id = 100665907672
job.run_id = 33760147938
job.head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
job.status = completed
job.conclusion = failure
job.name = test
job.steps = []
job.labels = [ubuntu-latest]
job.runner_id = 0
job.runner_name = ""
job.runner_group_id = 0
job.runner_group_name = ""
```

These are the raw REST fields that the PR #364 transport would decode and return.

## F2 semantic sufficiency

The two existing PR #364 GET operations are sufficient for the complete frozen F2 classification on this fixture. No separate job-detail, steps, or logs request is required.

Derived solely from these two observed REST responses:

```text
EXACT_RUN_IDENTITY = PASS
EXACT_HEAD_SHA = PASS
EXACT_JOB_IDENTITY = PASS
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

Reasoning boundary:

- `runner_id=0` and empty runner name establish no runner allocation for this job response;
- `steps=[]` establishes that configured workflow steps did not execute;
- `conclusion=failure` therefore belongs to workflow/job infrastructure state, not to repository test execution;
- repository tests remain `NOT_TESTED`, not `FAIL`;
- no LLM reasoning is required for this deterministic classification.

## Request-count implication

For the PR #364 implementation itself, the source code makes one transport request in `workflow_run()` and one transport request in `list_workflow_jobs()`.

For this exact F2 acquisition algorithm:

```text
PR364_DECLARED_TRANSPORT_REQUESTS = 2
PR364_REQUIRED_REST_ENDPOINTS = 2
THIRD_STEPS_READ_REQUIRED = NO
LOG_READ_REQUIRED = NO
```

This is stronger than wrapper-call inference because the adapter source explicitly issues one transport request per method and the two raw REST endpoint responses have now been observed to contain all required F2 fields.

Actual execution/instrumentation of the transplanted adapter must still confirm that no surrounding caller introduces extra requests or retries.

## Upstream tests present in PR #364

`tests/unit/test_github_adapter_v2.py` contains fake-transport coverage for workflow reads and verifies the jobs route:

```text
repos/tihotm/metaO/actions/runs/77/jobs?filter=latest&per_page=100
```

Current classification:

```text
PR364_F2_RUN_ROUTE = CODE_CONFIRMED
PR364_F2_JOBS_ROUTE = CODE_CONFIRMED
PR364_F2_ROUTE_TEST_PRESENT = YES
PR364_TWO_ROUTE_LIVE_REST_ORACLE = PASS
PR364_TWO_ROUTE_F2_SEMANTIC_SUFFICIENCY = PASS_FOR_FROZEN_FIXTURE
PR364_PYTHON_IMPLEMENTATION_EXECUTED_ON_CURRENT_HEAD = NOT_TESTED
PR364_CURRENT_HEAD_UNIT_REGRESSION = NOT_TESTED
```

## Minimum current-head qualification packet

The executor should transplant only the minimum read-only adapter/test slice to an isolated current-head branch. Do not merge the diverged PR wholesale.

Required tests now reduce to:

1. import/compile the transplanted adapter;
2. run focused adapter unit tests;
3. add an F2 fake-transport test using the exact observed two-response payload shape above;
4. assert exact run/job/head identities;
5. assert `runner_id=0 -> RUNNER_ALLOCATED=NO`;
6. assert `steps=[] -> CONFIGURED_STEPS_EXECUTED=NO`;
7. assert job failure with no executed steps preserves `REPOSITORY_TESTS=NOT_TESTED`;
8. execute exactly the two live GETs through the transplanted adapter if authenticated REST is available;
9. instrument transport request count and retain raw sanitized payloads;
10. only after functional PASS, run five repetitions if latency/reliability becomes decision-relevant.

Required output states:

```text
ADAPTER_UNIT_TESTS = PASS | FAIL | BLOCKED | NOT_TESTED
F2_FAKE_TRANSPORT_SEMANTICS = PASS | FAIL | BLOCKED | NOT_TESTED
F2_LIVE_ADAPTER_ACQUISITION = PASS | FAIL | BLOCKED | NOT_TESTED
F2_ADAPTER_TRANSPORT_REQUEST_COUNT = integer | NOT_TESTED
F2_LIVE_LATENCY = measured distribution | NOT_TESTED
```

## Decision impact

```text
WRITE_NEW_METAO_GITHUB_ADAPTER = NOT_JUSTIFIED
QUALIFY_EXISTING_PR364_SLICE_FIRST = YES
PR364_F2_MECHANICAL_CAPABILITY_GAP = CLOSED_AT_SOURCE_PLUS_REST_ORACLE_LEVEL
PR364_MERGE_AUTHORIZED = NO
P1_P3_F2_TOTAL_COST_WINNER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

The implementation strategy now has a much narrower uncertainty: the remaining question is not whether PR #364 has enough GitHub mechanics for F2. It does. The remaining question is whether the minimal transplanted implementation passes current-head tests and what its measured execution cost/reliability is under the common boundary.
