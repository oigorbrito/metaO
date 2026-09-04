# PR #364 F2 Minimal Slice — Controlled Execution Receipt

Status: CONTROLLED_ISOLATED_EXECUTION_WITH_HOSTED_CI_BLOCKER_OBSERVED
Governing research: #365
Execution handoff: #367
Qualification PR: #376
Qualification branch: `research/issue-365-pr364-f2-qualification`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`

## Scope

This receipt records controlled execution evidence for the minimal read-only F2 adapter slice, the exact frozen semantic fixture, and direct observation of hosted CI attempts. It is not a repository-integrated regression receipt and is not a live authenticated execution through `UrllibGitHubTransport`.

The production slice contains only:

- `GitHubAdapterError`;
- `GitHubTransport`;
- read-only `UrllibGitHubTransport`;
- `GitHubRepositoryAdapter.workflow_run`;
- `GitHubRepositoryAdapter.list_workflow_jobs`.

No issue/branch/file/PR mutation method and no mutation-authorization type are present.

## Frozen F2 fixture

```text
repository = tihotm/metaO
run_id = 33760147938
job_id = 100665907672
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
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

## Controlled execution history

The qualification evolved through three evidence states rather than rewriting history:

1. Initial 7-case execution: 7/7 PASS, two unittest invocations, both exit 0.
2. Evidence correction: the read-only negative boundary was changed from a local test double to the actual `UrllibGitHubTransport`; corrected 8-case controlled execution: 8/8 PASS. The Python execution surface did not expose a separate OS exit code for this corrected run.
3. Packet-completeness correction: a direct `HTTPError -> GitHubAdapterError` propagation case was executed controladamente, passed 1/1, and was then added to the repository test file at commit `6a93425ea52bc694e24b242a39bb056dfc6bf9ed`.

Current focal coverage:

```text
CURRENT_CONTROLLED_CASES = 9
CURRENT_CONTROLLED_PASS = 9
CURRENT_CONTROLLED_FAIL = 0
PACKET_MINIMUM_UNIT_TEST_REQUIREMENTS = 9/9 COVERED
FOCUSED_CONTROLLED_EXECUTION = PASS
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
TRANSPORT_HTTPERROR_PROPAGATION = PASS_CONTROLLED
```

Current cases cover:

- exact workflow-run route;
- exact workflow-jobs route;
- exact job-id/head-sha selection;
- runner allocation classification;
- empty-steps classification;
- failure does not imply repository-test failure;
- invalid adapter input rejected before transport;
- actual `UrllibGitHubTransport` rejects POST before network;
- actual `UrllibGitHubTransport` rejects GET-with-body before network;
- `HTTPError` is converted to `GitHubAdapterError` with response detail and original `HTTPError` preserved as `__cause__`.

The frozen packet lists nine minimum requirement categories; some assertions are combined in one test case. The current repository test file has nine unittest methods and covers all listed categories.

## Hosted CI evidence

### Earlier qualification head

Head `155c6e7f6e8b05f619977efeee74d2bab522e31b` created canonical CI run `33815181047`, job `100845630350`:

```text
status = completed
conclusion = failure
runner_id = 0
runner_name = ""
steps = []
job_logs = 404 BlobNotFound
```

### Current nine-case head

Head `6a93425ea52bc694e24b242a39bb056dfc6bf9ed` created canonical CI run `33824111083`, job `100872971347`:

```text
status = completed
conclusion = failure
runner_id = 0
runner_name = ""
steps = []
job_logs = 404 BlobNotFound
```

The same head also created five additional pull-request workflows, all observed as `completed/failure`. Earlier cross-workflow inspection showed the same pre-step pattern on independent workflows and across `ubuntu-latest` and `ubuntu-24.04` labels.

Therefore:

```text
HOSTED_CI_RUN_CREATED = YES
HOSTED_RUNNER_ALLOCATED = NO
HOSTED_CONFIGURED_STEPS_EXECUTED = NO
HOSTED_REPOSITORY_TESTS = NOT_TESTED
HOSTED_CI_FOR_QUALIFICATION_HEAD = BLOCKED_EXTERNAL_PRE_STEP
HOSTED_PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
CROSS_WORKFLOW_REPRODUCTION = YES
CROSS_RUNNER_LABEL_REPRODUCTION = YES
```

A workflow/job `failure` with `runner_id=0` and `steps=[]` is not treated as repository-test FAIL.

## Evidence corrections retained

Two evidence mistakes were corrected explicitly:

- a read-only boundary result initially relied on a test double rather than the real `UrllibGitHubTransport`; this was corrected and re-executed;
- `statuses=[]` was initially treated as absence of hosted CI; direct commit-associated workflow lookup proved that CI runs existed. Hence `EMPTY_COMMIT_STATUS != NO_WORKFLOW_RUN`.

A later audit found that this receipt still reported the 8-case state after the ninth repository test had been added. This version corrects that traceability drift and preserves the 7 -> 8 -> 9 chronology.

## Current evidence classification

```text
MINIMAL_SLICE_PORTED = YES_ON_QUALIFICATION_BRANCH
PACKET_MINIMUM_UNIT_TEST_REQUIREMENTS = 9/9 COVERED
F2_FAKE_TRANSPORT_SEMANTICS = PASS_CONTROLLED
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
TRANSPORT_HTTPERROR_PROPAGATION = PASS_CONTROLLED
WRONG_IDENTITY_NEGATIVE_CASES = PASS_CONTROLLED
MODEL_CALLS_IN_CONTROLLED_FIXTURE = 0
CURRENT_METAO_FOCAL_REPOSITORY_EXECUTION = NOT_TESTED
CURRENT_METAO_UNIT_REGRESSION = NOT_TESTED
HOSTED_CI_FOR_QUALIFICATION_HEAD = BLOCKED_EXTERNAL_PRE_STEP
HOSTED_REPOSITORY_TESTS = NOT_TESTED
LIVE_AUTHENTICATED_URLLIB_F2 = NOT_TESTED
LIVE_REQUEST_COUNT = NOT_TESTED
LIVE_RETRIES = NOT_TESTED
LIVE_LATENCY = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Operational deviations

- One duplicate job-log read was issued while confirming `BlobNotFound`; it caused no mutation and adds no independent evidence.
- Multiple documentation-only commits were created during receipt reconciliation. They are not independent empirical observations and must not be counted as repetitions.
- Hosted workflow failures caused by runner non-allocation must not be reused as product-failure evidence.

## Required next execution

Repository-integrated qualification remains local because hosted CI is blocked before configured steps:

```text
python -m pip install -e .
python -m unittest tests.unit.test_github_adapter_f2_qualification -v
python -m unittest discover -s tests/unit -p 'test_*.py' -v
git status --short
```

If those gates pass and GitHub authentication is available, execute the ported `UrllibGitHubTransport` live for exactly the two frozen GETs, retain sanitized raw responses, and instrument:

```text
transport_requests
retries
failed_attempts
wall_time_seconds
model_calls = 0 for this deterministic code path
```

One live run is sufficient for immutable-fixture functional acquisition. Timing/reliability claims require at least five comparable valid repetitions. No broader #364 adoption, cost winner, or product placement decision is authorized by this receipt alone.
