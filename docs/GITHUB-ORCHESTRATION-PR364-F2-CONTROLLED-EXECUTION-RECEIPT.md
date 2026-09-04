# PR #364 F2 Minimal Slice — Controlled Execution Receipt

Status: CONTROLLED_ISOLATED_EXECUTION_WITH_HOSTED_CI_BLOCKER_OBSERVED
Governing research: #365
Qualification branch: `research/issue-365-pr364-f2-qualification`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`

## Scope

This receipt records isolated Python execution of the ported minimal read-only F2 adapter and its frozen semantic fixture, plus direct observation of the canonical hosted CI attempt created for the qualification PR. It is not a successful hosted regression receipt and is not a live authenticated execution through `UrllibGitHubTransport`.

## Ported production slice

`src/metao/github_adapter.py` contains only:

- `GitHubAdapterError`;
- `GitHubTransport`;
- read-only `UrllibGitHubTransport`;
- `GitHubRepositoryAdapter.workflow_run`;
- `GitHubRepositoryAdapter.list_workflow_jobs`.

No issue/branch/file/PR mutation method and no mutation authorization type are present in this qualification slice.

## Frozen fixture

```text
repository = tihotm/metaO
run_id = 33760147938
job_id = 100665907672
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
```

The fake payload reproduces raw REST evidence already observed from the exact GitHub endpoints:

```text
job.status = completed
job.conclusion = failure
job.steps = []
job.runner_id = 0
job.runner_name = ""
```

## Controlled execution history

Initial focused execution established 7/7 targeted cases PASS across two unittest invocations, both exit 0.

A subsequent evidence audit identified that the original read-only transport test exercised a local test double rather than the production qualification `UrllibGitHubTransport`. The test was corrected before treating the transport boundary as directly tested.

Corrected execution covered 8 focused cases in one isolated unittest run:

```text
cases = 8
failures = 0
errors = 0
result = PASS
process_result = successful
```

A later audit identified the packet-required transport-error propagation case as missing from the repository test file. The exact `HTTPError -> GitHubAdapterError` behavior was first executed controladamente against the qualification transport and passed, then the repository unittest was added. The 9th case asserts that a GitHub `HTTPError` is converted to `GitHubAdapterError`, includes the status/body detail, and preserves the original `HTTPError` as `__cause__`.

Current focused coverage therefore contains:

- exact two-request path reproduces frozen F2 classification;
- job failure does not become repository-test failure without step evidence;
- wrong job identity fails instead of silently passing;
- wrong SHA fails instead of silently passing;
- missing/unknown steps remains NOT_TESTED;
- invalid adapter inputs reject before transport;
- the actual `UrllibGitHubTransport` rejects POST before any network call;
- the actual `UrllibGitHubTransport` rejects a GET body before any network call;
- the actual `UrllibGitHubTransport` converts `HTTPError` to `GitHubAdapterError` while preserving the original cause.

The two direct read-only negative-boundary tests do not require GitHub credentials or network access because the implementation fails closed before `urlopen` is reached. The HTTPError propagation test uses a patched `urlopen` and also performs no network call.

Aggregate current controlled result:

```text
CURRENT_CONTROLLED_CASES = 9
CURRENT_CONTROLLED_PASS = 9
CURRENT_CONTROLLED_FAIL = 0
FOCUSED_CONTROLLED_EXECUTION = PASS
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
TRANSPORT_HTTPERROR_PROPAGATION = PASS_CONTROLLED
PACKET_MINIMUM_UNIT_TEST_REQUIREMENTS = 9/9 COVERED
```

Important boundary: the 9th case was executed controladamente before publication and is present in the repository test file, but the complete 9-case repository-integrated focal file has not yet been executed in the user's actual worktree. Therefore repository-integrated focal execution remains `NOT_TESTED`, not PASS.

## Hosted CI observation for PR #376

The canonical pull-request CI was created for qualification head `155c6e7f6e8b05f619977efeee74d2bab522e31b`:

```text
workflow_run_id = 33815181047
workflow = CI
run_number = 699
event = pull_request
status = completed
conclusion = failure
head_sha = 155c6e7f6e8b05f619977efeee74d2bab522e31b
pull_request = 376
run_attempt = 1
```

The run contained one job:

```text
job_id = 100845630350
job_name = test
job_status = completed
job_conclusion = failure
steps = []
runner_id = 0
runner_name = ""
runner_group_id = 0
runner_group_name = ""
```

A dedicated step read also returned `steps = []`.

A job-log read returned:

```text
HTTP = 404
ERROR_CODE = BlobNotFound
LOG_RECEIPT_AVAILABLE = NO
```

Therefore:

```text
HOSTED_CI_RUN_CREATED = YES
HOSTED_RUNNER_ALLOCATED = NO
HOSTED_CONFIGURED_STEPS_EXECUTED = NO
HOSTED_REPOSITORY_TESTS = NOT_TESTED
HOSTED_CI_FOR_QUALIFICATION_HEAD = BLOCKED_EXTERNAL_PRE_STEP
HOSTED_PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

This is an independent reproduction of the already-known hosted-runner pre-step blocker. It is not evidence that the qualification tests failed.

The commit-status surface returned `statuses=[]`; that surface alone was insufficient to establish whether a workflow run existed. Direct workflow-run acquisition resolved the ambiguity. Hence:

```text
EMPTY_COMMIT_STATUS != NO_WORKFLOW_RUN
```

After the 9th test was published, canonical CI run `33824111083` / job `100872971347` for qualification head `6a93425ea52bc694e24b242a39bb056dfc6bf9ed` independently reproduced the same pre-step condition:

```text
status = completed
conclusion = failure
head_sha = 6a93425ea52bc694e24b242a39bb056dfc6bf9ed
runner_id = 0
runner_name = ""
steps = []
job_log_read = 404 BlobNotFound
```

All six pull-request workflows observed for that head also ended in `failure`. This strengthens the infrastructure classification; it does not promote repository tests from `NOT_TESTED`.

## Evidence correction

The earlier receipt wording could imply that `READ_ONLY_BOUNDARY = PASS_CONTROLLED` was supported by direct execution of the real transport. Before the correction, it was not: that case used a local test double.

The corrected test now directly exercises `UrllibGitHubTransport`, so the current classification below is supported. The earlier over-strong implication is retained here as a documented evidence correction rather than silently overwritten.

A later remote inspection also corrected an independent observability mistake: `statuses=[]` had initially been treated as no hosted CI observed. Direct commit-associated workflow lookup showed that CI run `33815181047` did exist and failed before runner allocation. The corrected classification is preserved above.

A subsequent packet audit found that the receipt's aggregate count remained at 8 after the repository added the required HTTPError propagation case. This document now preserves the 7 -> 8 -> 9 history explicitly rather than rewriting the earlier execution history as if all nine cases had run in the same process.

## Environment

The controlled Python execution is isolated from the user's complete metaO worktree. Therefore it cannot establish repository-wide regression status.

## Evidence classification

```text
MINIMAL_SLICE_PORTED = YES_ON_QUALIFICATION_BRANCH
F2_FAKE_TRANSPORT_SEMANTICS = PASS_CONTROLLED
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
TRANSPORT_HTTPERROR_PROPAGATION = PASS_CONTROLLED
PACKET_MINIMUM_UNIT_TEST_REQUIREMENTS = 9/9 COVERED
WRONG_IDENTITY_NEGATIVE_CASES = PASS_CONTROLLED
CURRENT_METAO_UNIT_REGRESSION = NOT_TESTED
CURRENT_REPOSITORY_INTEGRATED_FOCAL_9_CASES = NOT_TESTED
HOSTED_CI_FOR_QUALIFICATION_HEAD = BLOCKED_EXTERNAL_PRE_STEP
HOSTED_REPOSITORY_TESTS = NOT_TESTED
LIVE_AUTHENTICATED_URLLIB_F2 = NOT_TESTED
LIVE_REQUEST_COUNT = NOT_TESTED
LIVE_LATENCY = NOT_TESTED
MODEL_CALLS_IN_CONTROLLED_FIXTURE = 0
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Operational deviation

The job-log read was issued twice while confirming the missing blob. Both attempts returned `404 BlobNotFound`; the duplicate read caused no repository mutation and adds no independent evidence. Only the first failure is needed for the substantive claim.

## Required next execution

Because hosted CI is blocked before configured steps, repository-integrated qualification remains local:

```text
python -m unittest tests.unit.test_github_adapter_f2_qualification -v
python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

Then, if a GitHub token is available, invoke the ported `UrllibGitHubTransport` live for exactly the two frozen GETs, retain sanitized raw payloads, and instrument transport request count. Five repetitions are required only when timing/reliability is used as a response variable.
