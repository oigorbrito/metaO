# GitHub Orchestration — Final Bounded Audit 2026-09-03

Status: FINAL_BOUNDED_AUDIT_WITH_REMAINING_EXECUTION_BLOCKERS
Governing research: #365
Execution handoff: #367
Qualification PR: #376
Qualification head observed: `5fba3325228971461047f3af0e542bd94c6f6836`
Frozen metaO target SHA: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
Frozen workflow run: `33760147938`
Frozen workflow job: `100665907672`
Issue-Orchestrator pin: `26564aac4a02afc0989966ec2cd3e190884ba177`

## Purpose

Close the bounded empirical audit for GitHub orchestration placement without promoting missing execution to PASS and without converting infrastructure/credential blockers into product failures.

This audit distinguishes three different execution boundaries:

1. exact qualification-source focal execution in an isolated sandbox;
2. authenticated live GitHub acquisition through the connected GitHub API boundary;
3. the exact production qualification `UrllibGitHubTransport` using an exportable token in a complete user worktree.

Only the first two were executable in the current audit environment. The third remains blocked by credential boundary, and repository-wide unit regression in the user's complete worktree remains NOT_TESTED.

## Wave 1 — exact-head focal qualification

The exact qualification branch tree at:

`5fba3325228971461047f3af0e542bd94c6f6836`

was fetched from GitHub. The recursive tree response was not truncated. The focal source blobs were:

- `src/metao/github_adapter.py` = `e91ad5bc32719f232a94267cf42cd72e379c14bf`
- `tests/unit/test_github_adapter_f2_qualification.py` = `90a6a1935b2fbb5851e74a8fa97773d57458e323`

The focal unittest semantics were executed in an isolated Python sandbox reconstructed from those exact fetched sources.

Observed focal result:

```text
EXACT_HEAD_FOCAL_SANDBOX_EXECUTION = PASS
FOCAL_TEST_COUNT = 9
FOCAL_PASS = 9
FOCAL_FAIL = 0
PROCESS_EXIT_CODE = 0
```

The nine cases cover:

1. exact two-request workflow-run/workflow-jobs path;
2. workflow job failure does not become repository-test failure without step evidence;
3. wrong job identity fails;
4. wrong SHA fails;
5. missing steps remains NOT_TESTED;
6. invalid input rejects before transport;
7. actual `UrllibGitHubTransport` rejects POST before network;
8. actual `UrllibGitHubTransport` rejects GET-with-body before network;
9. `HTTPError -> GitHubAdapterError` conversion preserves cause.

Evidence boundary:

```text
CURRENT_USER_WORKTREE_FOCAL_EXECUTION = NOT_TESTED
CURRENT_USER_WORKTREE_FULL_UNIT_REGRESSION = NOT_TESTED
EDITABLE_INSTALL_IN_COMPLETE_USER_WORKTREE = NOT_TESTED
```

The sandbox focal PASS is not represented as complete repository-integrated regression evidence.

## Wave 2 — authenticated live F2 repetition

Five live read-only repetitions were executed through the authenticated connected GitHub API boundary. Each repetition used the exact frozen pair:

```text
GET repos/tihotm/metaO/actions/runs/33760147938
GET repos/tihotm/metaO/actions/runs/33760147938/jobs?filter=latest&per_page=100
```

All five run reads returned:

```text
id = 33760147938
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
status = completed
conclusion = failure
run_attempt = 6
```

All five jobs reads returned exactly one target job with:

```text
id = 100665907672
run_id = 33760147938
head_sha = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
status = completed
conclusion = failure
steps = []
runner_id = 0
runner_name = ""
runner_group_id = 0
runner_group_name = ""
```

Therefore:

```text
CONNECTED_AUTHENTICATED_F2_REPETITIONS = 5
CONNECTED_AUTHENTICATED_F2_CORRECTNESS = PASS_5_OF_5
FROZEN_CLASSIFICATION_REPRODUCED = PASS_5_OF_5
OBSERVED_WRAPPER_READS_PER_REPETITION = 2
MODEL_CALLS_FOR_DETERMINISTIC_CLASSIFICATION = 0
```

Frozen classification reproduced:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

Observability boundary:

```text
UNDERLYING_GITHUB_HTTP_CALLS = NOT_TESTED
CONNECTOR_INTERNAL_RETRIES = NOT_TESTED
COMPARABLE_WALL_TIME = NOT_TESTED
AUTHORITATIVE_LLM_TOKEN_USAGE = NOT_APPLICABLE_TO_DETERMINISTIC_CLASSIFICATION
```

A connected wrapper call is not asserted to equal one underlying HTTP request.

## Exact `UrllibGitHubTransport` live boundary

The linked GitHub connector credential is not exported into the Python sandbox. Therefore the exact qualification `UrllibGitHubTransport` could not be authenticated live from the current environment.

Classification:

```text
LIVE_AUTHENTICATED_URLLIB_F2 = BLOCKED_EXTERNAL_CREDENTIAL_BOUNDARY
URLLIB_PRODUCT_FAILURE = NOT_PROVEN
URLLIB_AUTH_FAILURE = NOT_OBSERVED
```

The authenticated connected API PASS does not substitute for execution of the exact Python transport implementation.

Unblock condition: execute the qualification head in a complete worktree where a valid GitHub token is available to the Python process, without exposing the token in retained artifacts.

## P2 external-orchestrator gate

At frozen Issue-Orchestrator pin `26564aac4a02afc0989966ec2cd3e190884ba177`, the supported GitHub/status surface does not provide the exact arbitrary Actions run/job acquisition required by F2.

Existing classification remains:

```text
P2_GENERAL_PR_STATUS_ROLLUP_CAPABILITY = CODE_CONFIRMED
P2_F2_LIVE_EXACT_RUN_JOB_ACQUISITION = BLOCKED_CAPABILITY_GAP
P2_PRODUCT_FAILURE = NO
P2_DONOR_INVALID = NO
```

No handwritten surrogate is allowed because that would change the experimental subject after protocol freeze.

## P3 hybrid interpretation

The mechanical P3/F2 path has already been observed with `MODEL_CALLS=0`. The current five live connector repetitions further show that the exact F2 facts and classification are deterministic and do not require semantic model mediation.

For this fixture only:

```text
F2_AGENT_MEDIATION_REQUIRED = NO
F2_MECHANICAL_MODEL_CALLS = 0
```

This does not prove that all GitHub orchestration tasks are deterministic or that all hybrid/agent paths are unnecessary.

## Cost decision

The following global cost claims remain invalid because unlike metrics are incomplete:

```text
METAO_DETERMINISTIC_IS_CHEAPER_GLOBAL = NOT_TESTED
EXTERNAL_AGENT_IS_CHEAPER_GLOBAL = NOT_TESTED
HYBRID_IS_CHEAPER_GLOBAL = NOT_TESTED
MONETIZED_TOTAL_COST = NOT_TESTED
```

However, the exact F2 mechanical placement decision can be bounded by capability and avoidable model mediation rather than by an unsupported monetized total:

```text
F2_MECHANICAL_PLACEMENT_RECOMMENDATION = METAO_DETERMINISTIC
P2_AS_IS_FOR_EXACT_F2 = NO_CAPABILITY_AT_FROZEN_PIN
P3_FOR_EXACT_F2 = DETERMINISTIC_MECHANICS_WITH_MODEL_CALLS_0
AGENT_FOR_EXACT_F2_MECHANICS = NOT_REQUIRED
```

Rationale supported by evidence:

- the exact acquisition path is two deterministic GitHub reads at the declared adapter boundary;
- the frozen classification is deterministic and reproduced five times through authenticated GitHub acquisition;
- the external donor at the frozen pin lacks the exact run/job capability;
- forcing an LLM call into P3 would add mediation without a demonstrated correctness requirement for this fixture.

This is a bounded engineering placement recommendation, not a global agent-vs-metaO winner.

## Product adoption boundary

The following remain prerequisites before product adoption/merge of the qualified slice can be authorized:

```text
CURRENT_USER_WORKTREE_FULL_UNIT_REGRESSION = NOT_TESTED
LIVE_AUTHENTICATED_URLLIB_F2 = BLOCKED_EXTERNAL_CREDENTIAL_BOUNDARY
ACTUAL_URLLIB_REQUEST_COUNT = NOT_TESTED
ACTUAL_URLLIB_RETRIES = NOT_TESTED
RAW_LOCAL_EVIDENCE_PROMOTION = NOT_COMPLETED
```

Therefore:

```text
PR376_MERGE_AUTHORIZATION = BLOCKED
PRODUCT_ADOPTION_AUTHORIZATION = BLOCKED
PR364_WHOLESALE_MERGE_AUTHORIZATION = NO
GLOBAL_COST_WINNER = NOT_TESTED
```

## Remaining local-only evidence

The reported executor-local identities remain outside the remote evidence set until independently promoted/reconciled:

- `a00e8e81f0b9329b8be3fa97e84b909c89118e2c`
- `5b05610f335e6c82a7c61a53ee717a7ee592458b`
- `325a9b6`

Promotion must preserve the original artifacts and first inspect them for secrets, machine-specific absolute paths, junk and unrelated changes.

## Final bounded disposition

```text
EXACT_HEAD_FOCAL_SANDBOX_EXECUTION = PASS
CONNECTED_AUTHENTICATED_F2_CORRECTNESS = PASS_5_OF_5
F2_SEMANTIC_REPEATABILITY = PASS_5_OF_5
LIVE_AUTHENTICATED_URLLIB_F2 = BLOCKED_EXTERNAL_CREDENTIAL_BOUNDARY
FULL_USER_WORKTREE_UNIT_REGRESSION = NOT_TESTED
P2_F2_EXACT_CAPABILITY = BLOCKED_CAPABILITY_GAP
F2_MECHANICAL_PLACEMENT_RECOMMENDATION = METAO_DETERMINISTIC
AGENT_USE_POLICY = USE_ONLY_WHEN_NONDETERMINISTIC_REASONING_IS_ACTUALLY_REQUIRED
PRODUCT_ADOPTION_AUTHORIZATION = BLOCKED
GLOBAL_COST_WINNER = NOT_TESTED
```

The research question is therefore closed at the bounded F2 placement level, while product adoption remains gated by the explicitly listed execution evidence rather than by opinion or architectural preference.
