# PR #364 F2 Minimal Slice — Controlled Execution Receipt

Status: CONTROLLED_ISOLATED_EXECUTION
Governing research: #365
Qualification branch: `research/issue-365-pr364-f2-qualification`
Qualification head after evidence correction: `a2be902dcf45f0bdb9d10614e94986d3478eea8f`
Internal donor pin: `1c9a9728ec4ba69a59c7ae722e06d13616b73fb0`

## Scope

This receipt records isolated Python execution of the ported minimal read-only F2 adapter and its frozen semantic fixture. It is not a full metaO worktree regression and is not a live authenticated execution through `UrllibGitHubTransport`.

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

Corrected execution covered the exact current test semantics in one isolated unittest run:

```text
cases = 8
failures = 0
errors = 0
result = PASS
process_result = successful
```

Cases:

- exact two-request path reproduces frozen F2 classification;
- job failure does not become repository-test failure without step evidence;
- wrong job identity fails instead of silently passing;
- wrong SHA fails instead of silently passing;
- missing/unknown steps remains NOT_TESTED;
- invalid adapter inputs reject before transport;
- the actual `UrllibGitHubTransport` rejects POST before any network call;
- the actual `UrllibGitHubTransport` rejects a GET body before any network call.

The two direct `UrllibGitHubTransport` negative tests do not require GitHub credentials or network access because the implementation fails closed before `urlopen` is reached.

Aggregate current controlled result:

```text
CURRENT_CONTROLLED_CASES = 8
CURRENT_CONTROLLED_PASS = 8
CURRENT_CONTROLLED_FAIL = 0
FOCUSED_CONTROLLED_EXECUTION = PASS
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
```

## Evidence correction

The earlier receipt wording could imply that `READ_ONLY_BOUNDARY = PASS_CONTROLLED` was supported by direct execution of the real transport. Before the correction, it was not: that case used a local test double.

The corrected test now directly exercises `UrllibGitHubTransport`, so the current classification below is supported. The earlier over-strong implication is retained here as a documented evidence correction rather than silently overwritten.

## Environment

The controlled Python execution is isolated from the user's complete metaO worktree. Therefore it cannot establish repository-wide regression status.

## Evidence classification

```text
MINIMAL_SLICE_PORTED = YES_ON_QUALIFICATION_BRANCH
F2_FAKE_TRANSPORT_SEMANTICS = PASS_CONTROLLED
REAL_URLLIB_READ_ONLY_NEGATIVE_BOUNDARY = PASS_CONTROLLED
WRONG_IDENTITY_NEGATIVE_CASES = PASS_CONTROLLED
CURRENT_METAO_UNIT_REGRESSION = NOT_TESTED
HOSTED_CI_FOR_QUALIFICATION_HEAD = NOT_EXECUTED
LIVE_AUTHENTICATED_URLLIB_F2 = NOT_TESTED
LIVE_REQUEST_COUNT = NOT_TESTED
LIVE_LATENCY = NOT_TESTED
MODEL_CALLS_IN_CONTROLLED_FIXTURE = 0
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Remote CI observation

At qualification head inspection, the commit-status surface returned no statuses. Absence of statuses is not PASS and is recorded as `HOSTED_CI_FOR_QUALIFICATION_HEAD = NOT_EXECUTED/NOT_OBSERVED`.

## Required next execution

The next executor step is repository-integrated qualification:

```text
python -m unittest tests.unit.test_github_adapter_f2_qualification -v
python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

Then, if a GitHub token is available, invoke the ported `UrllibGitHubTransport` live for exactly the two frozen GETs, retain sanitized raw payloads, and instrument transport request count. Five repetitions are required only when timing/reliability is used as a response variable.
