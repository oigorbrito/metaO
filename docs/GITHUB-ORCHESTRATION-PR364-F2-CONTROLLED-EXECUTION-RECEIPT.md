# PR #364 F2 Minimal Slice — Controlled Execution Receipt

Status: CONTROLLED_ISOLATED_EXECUTION
Governing research: #365
Qualification branch: `research/issue-365-pr364-f2-qualification`
Qualification code head before receipt: `8a5b5e5e306f5679f24ae783081428645e987e33`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`

## Scope

This receipt records isolated Python execution of the newly ported minimal read-only F2 adapter and its frozen semantic fixture. It is not a full metaO worktree regression and is not live execution through `UrllibGitHubTransport`.

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

The fake payload reproduces the raw REST evidence already observed from the exact GitHub endpoints:

```text
job.status = completed
job.conclusion = failure
job.steps = []
job.runner_id = 0
job.runner_name = ""
```

## Controlled executions

Execution A covered the core semantic cases:

```text
cases = 4
exit_code = 0
result = PASS
```

Cases:

- exact two-request path reproduces frozen F2 classification;
- missing steps remains NOT_TESTED;
- wrong job identity fails instead of silently passing;
- wrong SHA fails instead of silently passing.

Execution B covered the remaining test-file cases:

```text
cases = 3
exit_code = 0
result = PASS
```

Cases:

- job failure does not become repository-test failure;
- invalid inputs reject before transport;
- read-only transport contract rejects a mutation method.

Aggregate controlled result:

```text
CONTROLLED_CASES = 7
CONTROLLED_PASS = 7
CONTROLLED_FAIL = 0
CONTROLLED_EXIT_CODES = [0, 0]
FOCUSED_CONTROLLED_EXECUTION = PASS
```

## Environment deviation

The isolated Python runtime printed an unrelated `artifact_tool` spreadsheet warmup traceback before unittest output. The unittest process nevertheless returned exit code 0 and all targeted cases passed. This runtime warmup message is retained as an environmental deviation and is not attributed to metaO.

## Evidence classification

```text
MINIMAL_SLICE_PORTED = YES_ON_QUALIFICATION_BRANCH
F2_FAKE_TRANSPORT_SEMANTICS = PASS_CONTROLLED
READ_ONLY_BOUNDARY = PASS_CONTROLLED
WRONG_IDENTITY_NEGATIVE_CASES = PASS_CONTROLLED
CURRENT_METAO_UNIT_REGRESSION = NOT_TESTED
LIVE_URLLIB_F2 = NOT_TESTED
LIVE_REQUEST_COUNT = NOT_TESTED
LIVE_LATENCY = NOT_TESTED
MODEL_CALLS_IN_CONTROLLED_FIXTURE = 0
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Required next execution

The next executor step is no longer capability discovery. It is repository-integrated qualification:

```text
python -m unittest tests.unit.test_github_adapter_f2_qualification -v
python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

Then, if a GitHub token is available, invoke the ported `UrllibGitHubTransport` live for the exact two GETs, retain sanitized raw payloads, count transport requests, and perform five repetitions only when timing/reliability becomes the response variable.
