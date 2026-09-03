# PR #364 GitHub Adapter — Frozen F2 Qualification

Status: SOURCE_QUALIFICATION_ONLY
Governing research: #365
Subject: metaO PR #364 `feat/github-governed-adapter`
Subject pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`
Frozen metaO baseline: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`

## Question

Does the already-existing adapter implementation in PR #364 contain the deterministic GitHub Actions mechanics required to attempt frozen fixture F2 without inventing a second adapter?

This qualification does not authorize merging PR #364 and does not count source inspection as execution evidence.

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

## F2 required mechanics

Frozen F2 requires exact repository/commit/run evidence and must preserve distinctions including:

```text
WORKFLOW_JOB = FAIL | other observed state
CONFIGURED_STEPS_EXECUTED = YES | NO | NOT_TESTED
REPOSITORY_TESTS = PASS | FAIL | NOT_TESTED
PRODUCT_FUNCTIONAL_FAILURE = PROVEN | NOT_PROVEN
```

The acquisition path must not infer test execution from workflow/job conclusion alone.

## PR #364 source mapping

At subject pin `1c9a9728...`, `src/metao/github_adapter.py` contains:

```text
workflow_run(repository, run_id)
  GET repos/{repository}/actions/runs/{run_id}

list_workflow_jobs(repository, run_id, filter="latest", per_page=100)
  GET repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100
```

The transport returns decoded GitHub JSON without normalizing read payloads, so fields supplied by GitHub in these responses remain available to the caller.

This establishes a deterministic two-request candidate acquisition path for the known frozen F2 run:

```text
GET /repos/tihotm/metaO/actions/runs/33760147938
GET /repos/tihotm/metaO/actions/runs/33760147938/jobs?filter=latest&per_page=100
```

The known target job is `100665907672` and can be selected from the returned jobs collection by exact id. No separate job-by-id method is required to attempt F2 if the list response contains the required fields.

## Upstream tests present in PR #364

`tests/unit/test_github_adapter_v2.py` contains a fake-transport test for workflow read routing. It verifies that workflow run listing and workflow job listing are GET operations and that the jobs route is exactly:

```text
repos/tihotm/metaO/actions/runs/77/jobs?filter=latest&per_page=100
```

The tests also cover fail-closed mutation authorization and other adapter surfaces. They are source-level test evidence only in this qualification.

Current classification:

```text
PR364_F2_RUN_ROUTE = CODE_CONFIRMED
PR364_F2_JOBS_ROUTE = CODE_CONFIRMED
PR364_F2_ROUTE_TEST_PRESENT = YES
PR364_TESTS_EXECUTED_ON_SUBJECT_PIN = NOT_TESTED_IN_THIS_WAVE
PR364_TESTS_EXECUTED_ON_CURRENT_MAIN = NOT_TESTED
PR364_LIVE_F2 = NOT_TESTED
```

## Minimum current-head qualification packet

The code executor should create an isolated qualification branch/worktree from current `main` or the current research-approved base and transplant only the minimum adapter/test slice needed for F2. Do not merge the diverged PR wholesale.

Required direct tests:

1. import/compile the transplanted adapter;
2. run `python -m unittest discover -s tests/unit -p 'test_github_adapter*.py' -v`;
3. add/execute an F2-specific fake-transport test asserting:
   - exact run-id route;
   - exact jobs route;
   - exact job-id selection;
   - `steps=[]` or missing/empty steps maps to `CONFIGURED_STEPS_EXECUTED=NO` only when the GitHub payload actually establishes that condition;
   - job `conclusion=failure` does not map repository tests to FAIL without configured test-step execution evidence;
4. if authenticated GitHub REST is available, execute the two GETs against run `33760147938`, select job `100665907672`, and retain raw JSON with secrets removed;
5. repeat live acquisition 5 times only when timing/reliability becomes a response variable; one live run is sufficient only for functional acquisition evidence;
6. count actual HTTP requests at the transport boundary; do not count a wrapper invocation as an unknown number of GitHub requests.

Required output states:

```text
ADAPTER_UNIT_TESTS = PASS | FAIL | BLOCKED | NOT_TESTED
F2_FAKE_TRANSPORT_SEMANTICS = PASS | FAIL | BLOCKED | NOT_TESTED
F2_LIVE_ACQUISITION = PASS | FAIL | BLOCKED | NOT_TESTED
F2_LIVE_REQUEST_COUNT = integer | NOT_TESTED
F2_LIVE_LATENCY = measured distribution | NOT_TESTED
```

## Decision impact

The source qualification materially changes implementation strategy but not the cost winner:

```text
WRITE_NEW_METAO_GITHUB_ADAPTER = NOT_JUSTIFIED
QUALIFY_EXISTING_PR364_SLICE_FIRST = YES
PR364_MERGE_AUTHORIZED = NO
P1/P3_F2_TOTAL_COST_WINNER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

The reason is engineering economy: an existing code-confirmed deterministic route should be qualified before creating duplicate implementation. This is not sunk-cost reasoning; it is avoidance of redundant implementation when a candidate implementation already satisfies the source-level capability gate.
