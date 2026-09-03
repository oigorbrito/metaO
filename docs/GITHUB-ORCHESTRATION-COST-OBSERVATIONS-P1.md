# GitHub Orchestration Cost Observations — P1

Status: EMPIRICAL_OBSERVATION_RECORD
Protocol: `github-orchestration-cost-v1`
Governing Issue: #365
Execution placement: P1 deterministic/direct
Product code change: NO
Architecture decision: NOT AUTHORIZED

## Scope

This record preserves the first direct-path observations for fixtures F1 and F2 under the frozen protocol in `docs/GITHUB-ORCHESTRATION-COST-EXPERIMENT.md`.

It does not change the protocol, add criteria, or promote a cross-placement winner.

## Subject and target pins

```text
SUBJECT_REPOSITORY = tihotm/metaO
SUBJECT_PIN = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
PROTOCOL_HEAD_AT_EXECUTION = d577e20959254caf451def31e543aa83ef493957
ISSUE_ORCHESTRATOR_COMPARATOR_PIN = 26564aac4a02afc0989966ec2cd3e190884ba177
```

## Observation P1-F1-001

```text
RUN_ID: P1-F1-001
PROTOCOL_VERSION: github-orchestration-cost-v1
PLACEMENT: P1 deterministic/direct
SUBJECT_REPOSITORY: tihotm/metaO
SUBJECT_PIN: b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
FIXTURE_ID: F1
TARGET_REPOSITORY: tihotm/metaO
TARGET_SHA: b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
MODEL_PROVIDER_VERSION: NOT_TESTED
PROMPT_OR_INPUT_DIGEST: NOT_RECORDED — execution initiated from the frozen fixture definition
CONTEXT_BOUNDARY: Issue #365 plus exact repository file read
TOOL_BOUNDARY: GitHub connector wrapper invocations
RETRY_POLICY: no retry requested; none observed
TIMEOUT_POLICY: connector default / not independently measured
CONCURRENCY: sequential
CACHE_STATE: NOT_TESTED
START_TIMESTAMP: NOT_RECORDED_AT_FIXTURE_BOUNDARY
END_TIMESTAMP: NOT_RECORDED_AT_FIXTURE_BOUNDARY
LLM_INPUT_TOKENS: NOT_TESTED
LLM_OUTPUT_TOKENS: NOT_TESTED
MODEL_CALLS: NOT_TESTED
WRAPPER_TOOL_CALLS: 2 successful reads
UNDERLYING_GITHUB_CALLS: NOT_TESTED
RETRIES: 0
FAILED_ATTEMPTS: 0
WALL_TIME_SECONDS: NOT_TESTED
COMPUTE_MEASUREMENT: NOT_TESTED
HUMAN_CORRECTIONS: 0 within the fixture
MUTATIONS_OBSERVED: 0
CORRECTNESS_RESULT: PASS
RAW_ARTIFACT_POINTERS: Issue #365; docs/EMPIRICAL-RESEARCH-AND-REPRODUCIBILITY.md at subject pin
DEVIATIONS: timestamps, prompt digest and token/runtime telemetry were not exposed at the declared measurement boundary
BLOCKERS: BLK-COST-001; BLK-COST-002; BLK-COST-005
```

Observed required outcome:

- exact Issue `#365` identity and state were retrieved;
- the governing empirical methodology file was retrieved from the frozen subject pin;
- no mutation occurred;
- provenance is auditable through the issue and file identities.

Bounded interpretation:

`P1` satisfied F1 correctness in this immutable fixture instance with two observed wrapper invocations and no retry. This is not a token, network-request, timing, reliability, monetary, or cross-placement superiority claim.

## Observation P1-F2-001

```text
RUN_ID: P1-F2-001
PROTOCOL_VERSION: github-orchestration-cost-v1
PLACEMENT: P1 deterministic/direct
SUBJECT_REPOSITORY: tihotm/metaO
SUBJECT_PIN: b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
FIXTURE_ID: F2
TARGET_REPOSITORY: tihotm/metaO
TARGET_SHA: b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
MODEL_PROVIDER_VERSION: NOT_TESTED
PROMPT_OR_INPUT_DIGEST: NOT_RECORDED — execution initiated from the frozen fixture definition
CONTEXT_BOUNDARY: exact SHA, Actions run, latest job state
TOOL_BOUNDARY: GitHub connector wrapper invocations
RETRY_POLICY: no retry requested inside this fixture execution; none observed
TIMEOUT_POLICY: connector default / not independently measured
CONCURRENCY: sequential
CACHE_STATE: NOT_TESTED
START_TIMESTAMP: NOT_RECORDED_AT_FIXTURE_BOUNDARY
END_TIMESTAMP: NOT_RECORDED_AT_FIXTURE_BOUNDARY
LLM_INPUT_TOKENS: NOT_TESTED
LLM_OUTPUT_TOKENS: NOT_TESTED
MODEL_CALLS: NOT_TESTED
WRAPPER_TOOL_CALLS: 2 successful reads
UNDERLYING_GITHUB_CALLS: NOT_TESTED
RETRIES: 0
FAILED_ATTEMPTS: 0
WALL_TIME_SECONDS: NOT_TESTED
COMPUTE_MEASUREMENT: NOT_TESTED
HUMAN_CORRECTIONS: 0 within the fixture
MUTATIONS_OBSERVED: 0
CORRECTNESS_RESULT: PASS
RAW_ARTIFACT_POINTERS: Actions run 33760147938; job 100665907672; Issue #368
DEVIATIONS: runner-allocation detail is based on the latest previously inspected attempt evidence; the compact job wrapper returned no configured steps
BLOCKERS: BLK-WAVE-005; BLK-WAVE-006; BLK-COST-001; BLK-COST-002; BLK-COST-005
```

Observed classification:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

Bounded interpretation:

`P1` satisfied F2 correctness because the result was bound to the exact subject SHA and did not convert absent repository-test execution into PASS or into a metaO product failure.

## Protocol deviations outside F1/F2

During evidence bookkeeping after the fixture executions, temporary Issues `#370`, `#371`, `#372`, `#373`, and `#374` were accidentally created. Each was immediately reclassified and closed as `not_planned` with an explicit explanation.

These mutations occurred outside the F1/F2 read-only measurement boundary and are therefore not counted as fixture mutations. They remain recorded as an operational deviation and evidence-handling defect; they are not hidden or deleted.

The valid research tracking Issues created deliberately are:

- `#365` — governing comparison;
- `#367` — P2/P3 execution handoff;
- `#368` — first P1 F1/F2 observation record;
- `#369` — request to persist the P1 evidence in a repository artifact.

## Current comparative disposition

```text
P1_F1_CORRECTNESS = PASS
P1_F2_CORRECTNESS = PASS
P2_F1 = NOT_TESTED
P2_F2 = NOT_TESTED
P3_F1 = NOT_TESTED
P3_F2 = NOT_TESTED
TOKEN_COMPARISON = NOT_TESTED
UNDERLYING_GITHUB_REQUEST_COMPARISON = NOT_TESTED
TIMING_COMPARISON = NOT_TESTED
RELIABILITY_COMPARISON = NOT_TESTED
MONETIZED_TOTAL_COST = NOT_TESTED
METAO_DETERMINISTIC_IS_CHEAPER = NOT_TESTED
EXTERNAL_AGENT_IS_CHEAPER = NOT_TESTED
HYBRID_IS_CHEAPER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Next executable requirement

Execute F1/F2 for P2 and P3 under Issue #367 using the exact frozen subject pins and correctness gates. Minimum five valid repetitions remain required before any timing/reliability claim on agent-mediated placements.