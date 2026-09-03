# GitHub Orchestration Cost — P3/F2 Live Observation

Status: OBSERVED_LIVE_SINGLE_RUN
Protocol: github-orchestration-cost-v1
Placement: P3 (hybrid: deterministic GitHub mechanics outside LLM)
Fixture: F2 deterministic repository status reconciliation
Target repository: tihotm/metaO
Target SHA: b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
Target workflow run: 33760147938
Target job: 100665907672

## Observed live mechanics

A GitHub Actions wrapper that lists workflow runs by commit SHA was first invoked. That wrapper is documented to filter to pull-request-triggered runs only. Because the frozen F2 target run is a push-triggered run, it returned an empty list. This empty result is NOT evidence that no workflow existed and is retained as an instrumentation/path mismatch, not as fixture output.

The correct deterministic path was then exercised using the exact frozen workflow run id.

Observed job payload:

- id = 100665907672
- name = test
- run_id = 33760147938
- status = completed
- conclusion = failure
- steps = null in the job-list response

A second deterministic read of the exact job steps returned an empty list.

## Semantic classification

WORKFLOW_JOB = FAIL
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN

The previously established runner-allocation classification remains external evidence and was not re-derived from these two wrapper responses because these wrappers do not expose runner_id / runner_name.

## Measurement classification

P3_F2_LIVE_MECHANICS = PASS_FOR_OBSERVED_FIELDS
P3_F2_LIVE_FULL_FIXTURE = PARTIAL
P3_F2_LIVE_REPETITIONS = 1
P3_F2_TIMING_COMPARISON = NOT_TESTED
P3_F2_RELIABILITY_COMPARISON = NOT_TESTED
P3_F2_UNDERLYING_GITHUB_CALLS = NOT_TESTED
P3_F2_LLM_INPUT_TOKENS = NOT_APPLICABLE_TO_DETERMINISTIC_MECHANICS
P3_F2_LLM_OUTPUT_TOKENS = NOT_APPLICABLE_TO_DETERMINISTIC_MECHANICS
P3_F2_MODEL_CALLS = 0_FOR_THIS_MECHANICAL_PATH
P3_F2_COST_WINNER = NOT_TESTED

The zero model-call classification applies only to the deterministic mechanics path exercised here. It is not a claim about all P3 workloads.

## Deviations

1. The commit-SHA workflow-run wrapper was unsuitable for this push-triggered fixture because it filters to pull_request runs. Its empty result must not be interpreted as repository state.
2. Two accidental PR-create probes were attempted outside the F2 fixture. One was rejected by GitHub with HTTP 422 because head and base were both main and had no commits between them; another was rejected client-side for missing head/base. No pull request was created and no repository mutation occurred. These probes are excluded from F2 measurement and retained here for auditability.

## Decision boundary

This single live observation establishes that P3 can acquire and preserve the key F2 job/step semantics with deterministic GitHub mechanics and zero model calls on that mechanical path. It does not establish comparative cost superiority. Five comparable repetitions and a common measurement boundary with P1 are still required before timing/reliability ranking.