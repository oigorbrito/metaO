# GitHub Orchestration Cost — Controlled Replay Extension V1

Status: FROZEN_PROTOCOL_EXTENSION_V1
Parent protocol: `github-orchestration-cost-v1`
Governing Issue: #365
Execution handoff: #367
Product code change: NO
Architecture decision: NOT AUTHORIZED

## Purpose

Provide a controlled replay path for P2/P3 F1/F2 when the executor environment cannot authenticate to the private metaO repository, without changing the parent protocol's correctness rules or converting replay into evidence of live GitHub integration.

This extension is frozen before any replay result is inspected.

## Evidence boundary

Replay results may establish only:

```text
EXECUTED_IN_CONTROLLED_REPLAY_FIXTURE
```

They MUST NOT be reported as:

```text
EXECUTED_AGAINST_LIVE_METAO_GITHUB
LIVE_GITHUB_REQUEST_COST
LIVE_GITHUB_RELIABILITY
LIVE_GITHUB_LATENCY
```

A replay PASS does not erase the live-environment blocker. A replay FAIL is a failure against the frozen replay fixture and requires causal diagnosis before generalization.

## Candidate pin

```text
repository = issue-orchestrator/issue-orchestrator
pin = 26564aac4a02afc0989966ec2cd3e190884ba177
```

The candidate is public. Executors SHOULD obtain this exact pin through unauthenticated public GitHub clone/fetch when network access permits. If public GitHub itself is unavailable, record `BLOCKED_EXTERNAL_SOURCE_ACCESS`.

## Replay transport

Use a deterministic local HTTP stub, fake transport, or injected adapter client. The candidate code under test must remain the pinned candidate implementation; do not replace candidate behavior with a handwritten surrogate that merely mimics its outputs.

The replay transport may replace only the external GitHub network boundary.

## Frozen F1 replay inputs

Target semantic identity:

```text
repository = tihotm/metaO
issue_number = 365
subject_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
```

Issue response facts to replay:

```text
number = 365
state = open
title = Research: compare GitHub orchestration placement cost with controlled evidence
```

Relevant acceptance semantics:

- protocol frozen before measurement;
- exact pins;
- common fixtures/correctness;
- raw observations retained;
- missing token observability remains NOT_TESTED;
- no placement decision before comparable evidence.

Required repository evidence identity:

```text
path = docs/EMPIRICAL-RESEARCH-AND-REPRODUCIBILITY.md
ref = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
```

The replay may return the file body from a recorded fixture artifact or a content digest plus exact identity if the P2 supported path does not require the complete body. The correctness oracle must verify exact repository/path/ref binding and that the returned evidence is not silently substituted from another ref.

F1 replay correctness remains:

- correct issue identity;
- correct file identity/ref;
- no mutation;
- auditable provenance.

## Frozen F2 replay inputs

Target:

```text
repository = tihotm/metaO
sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
workflow_run_id = 33760147938
workflow_job_id = 100665907672
```

Recorded upstream observations:

```text
workflow_status = completed
workflow_conclusion = failure
run_attempt = 6
job_status = completed
job_conclusion = failure
runner_id = 0
runner_name = empty
configured_steps = none observed
```

Correct semantic classification oracle:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

F2 replay correctness requires exact SHA/run/job binding and preservation of the distinction between workflow/job `FAIL`, hosted execution `BLOCKED_EXTERNAL_PRE_STEP`, and repository tests `NOT_TESTED`.

Any implementation that maps this fixture to repository-test PASS or product functional FAIL fails F2 replay correctness.

## P2 replay

P2 must exercise the pinned Issue-Orchestrator GitHub-facing code path as far as its supported interfaces permit, with only the network boundary substituted by the deterministic replay transport.

For F1, if Issue-Orchestrator has no supported repository-file-read primitive in the same orchestration path, report:

```text
P2_F1_REPLAY = BLOCKED_CAPABILITY_GAP
```

Do not add a new candidate feature solely to make the benchmark pass.

For F2, if the candidate has PR/check-state semantics but no supported Actions workflow/job observation primitive sufficient to bind the exact run/job fixture, report:

```text
P2_F2_REPLAY = BLOCKED_CAPABILITY_GAP
```

This is a capability-boundary observation, not proof that the donor is generally defective.

## P3 replay

P3 may use deterministic replay reads outside the agent/LLM path and delegate only interpretation/synthesis required by the frozen fixture.

The deterministic mechanics and interpretation boundary must be logged separately.

A P3 implementation must not receive hidden oracle labels such as the expected final PASS/BLOCKED classification as model input. It may receive the frozen raw observations and the general parent-protocol correctness rules.

## Repetition

Functional deterministic replay:

- one exact run may establish replay correctness for an immutable fixture;
- execute at least 5 repetitions if timing/reliability is reported.

Agent/LLM-mediated replay:

- minimum 5 valid repetitions for timing/reliability or stochastic correctness claims;
- retain all valid observations, including failures and blocked runs;
- no rerun-until-favorable filtering.

## Replay metrics

Record the parent raw observation schema plus:

```text
EXECUTION_MODE = CONTROLLED_REPLAY
REPLAY_FIXTURE_VERSION = github-orchestration-cost-replay-v1
NETWORK_TO_PRIVATE_METAO_GITHUB = NO
CANDIDATE_SOURCE_PIN_VERIFIED = YES|NO
REPLAY_TRANSPORT = <implementation>
REPLAY_REQUEST_COUNT = <observed count or NOT_TESTED>
LIVE_GITHUB_REQUEST_COUNT = NOT_APPLICABLE
LIVE_GITHUB_LATENCY = NOT_APPLICABLE
```

If authoritative model usage telemetry is unavailable, tokens remain `NOT_TESTED`.

## Comparability rules

P1 live connector observations and P2/P3 replay observations are NOT directly comparable for live network latency, live request count, or live reliability.

Replay can close these narrower questions:

1. can the pinned candidate satisfy the semantic fixture when GitHub responses are controlled and available?
2. does its supported API surface contain the exact primitives required by F1/F2?
3. can a hybrid boundary satisfy the semantic fixture without placing deterministic mechanics inside the LLM path?
4. what model/token/tool cost is observable above the replay network boundary, if authoritative telemetry exists?

No overall `cheaper` winner may be declared solely from mixed live-vs-replay measurements.

## Anti-oracle rules

Forbidden:

```text
FEED_EXPECTED_FINAL_CLASSIFICATION_TO_MODEL = NO
MODIFY_FIXTURE_AFTER_OBSERVING_CANDIDATE_RESULT = NO
HANDWRITE_SURROGATE_CANDIDATE_BEHAVIOR = NO
TREAT_REPLAY_NETWORK_COST_AS_LIVE_GITHUB_COST = NO
PROMOTE_REPLAY_PASS_TO_LIVE_PASS = NO
```

## Authority invariants

Unchanged from parent protocol:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
RUNTIME_SELF_REPORT != GOVERNANCE_AUTHORITY
SECOND_METAO_CORE = NO
SECOND_POLICY_AUTHORITY = NO
SECOND_DURABLE_WORKFLOW_AUTHORITY = NO
SECOND_EVIDENCE_AUTHORITY = NO
SECOND_ACCEPTANCE_AUTHORITY = NO
```

## Objective next execution

An executor with public GitHub access but no private metaO authentication can now:

1. clone/fetch Issue-Orchestrator at the exact candidate pin;
2. build the deterministic replay transport from this frozen extension;
3. execute P2/P3 F1/F2 without private GitHub credentials;
4. preserve raw results as controlled-replay evidence;
5. keep live GitHub measurements explicitly NOT_APPLICABLE/NOT_TESTED.

Live authenticated F1/F2 remains required before claiming live integration behavior or live total cost.