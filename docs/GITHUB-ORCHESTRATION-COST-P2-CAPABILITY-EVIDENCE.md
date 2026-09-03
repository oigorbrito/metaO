# GitHub Orchestration Cost — P2 Capability Evidence

Status: CODE_AND_UPSTREAM_TEST_EVIDENCE
Protocol: `github-orchestration-cost-v1`
Governing Issue: #365
Execution handoff: #367
Product code change: NO
Architecture decision: NOT AUTHORIZED

## Purpose

Reduce uncertainty around whether the pinned external candidate contains concrete GitHub mechanics relevant to fixtures F1/F2/F3/F4 before runtime execution.

This record is not a P2 benchmark result. It does not convert repository inspection or upstream tests into `EXECUTED_IN_METAO_FIXTURE`, does not measure cost, and does not authorize a placement decision.

## Candidate pin

```text
repository = issue-orchestrator/issue-orchestrator
pin = 26564aac4a02afc0989966ec2cd3e190884ba177
```

## Evidence ladder disposition

```text
DOCUMENTED_RELEVANCE = YES
CODE_CONFIRMED_GITHUB_ADAPTER = YES
TEST_CONFIRMED_UPSTREAM_ISSUE_OPERATIONS = YES
TEST_CONFIRMED_UPSTREAM_PR_WRITE_SURFACE = YES
EXECUTED_IN_METAO_FIXTURE = NO
MEASURED_IN_COMPARABLE_METAO_FIXTURE = NO
```

The upstream-test classification means tests exist at the pinned revision. They were inspected, not executed by metaO in this session.

## Code-confirmed GitHub boundary

At the pinned revision, `src/issue_orchestrator/adapters/github/github_adapter.py` defines `GitHubAdapter` as an HTTP-API adapter implementing IssueTracker, LabelSet, and PullRequestTracker-style operations.

Observed properties include:

- issue retrieval and listing;
- label reads/writes;
- pull-request retrieval and creation;
- upstream HTTP errors propagated rather than collapsed into empty results;
- cache invalidation on writes;
- explicit write verification through an injected verification service;
- retry/verification budgets with timeout, max attempts, backoff, and jitter parameters;
- failure classification separating systemic verification failures from issue-local verification failures.

This establishes a concrete execution-layer GitHub implementation rather than README-only capability.

## F1 relevance

F1 requires exact Issue retrieval plus a repository-file read without mutation.

The pinned GitHub adapter has explicit issue retrieval/listing behavior. Upstream unit tests in `tests/unit/test_github_adapter.py` include:

- `test_get_issue_success` — maps number/title/labels/state/body/milestone/timestamps/comment count and asserts one HTTP `get_issue` call;
- `test_get_issue_not_found` — 404 becomes expected absence;
- `test_get_issue_http_error_propagates` — non-404 upstream failure remains an error;
- `test_list_issues_success`;
- stale-cache recovery tests that retry without cache when required stable IDs are missing, while avoiding the retry when required IDs are present.

Therefore:

```text
P2_F1_ISSUE_READ_CAPABILITY = TEST_CONFIRMED_UPSTREAM
P2_F1_REPOSITORY_FILE_READ_CAPABILITY = NOT_YET_MAPPED_TO_EXACT_SUPPORTED_P2_PATH
P2_F1_CORRECTNESS_IN_METAO_FIXTURE = NOT_TESTED
```

F1 as a whole cannot be marked PASS until the same exact fixture executes through the candidate-supported P2 path and returns the required file provenance without mutation.

## F2 relevance

F2 requires status reconciliation without converting incomplete observation into product PASS or product FAIL.

The pinned candidate has explicit typed status models in `src/issue_orchestrator/ports/pull_request_tracker.py`:

- status-check rollups distinguish `SUCCESS`, `FAILURE`, `PENDING`, `EXPECTED`, and `ERROR`;
- `StatusCheckRollupRead` separates `ok`, `permission_denied`, and `transient_error` capabilities;
- merge-queue reads distinguish `PRESENT`, `ABSENT`, and `INDETERMINATE`;
- `INDETERMINATE` is documented as non-actionable rather than equivalent to absence;
- PR state normalization distinguishes merged from closed-unmerged.

The HTTP client additionally models fail-safe check-rollup behavior. `src/issue_orchestrator/adapters/github/http_client.py` records:

- completed check conclusions are considered passing only for an explicit allow-list (`success`, `skipped`, `neutral`);
- unknown/new completed conclusions are non-passing;
- missing permission and transient failures are classified separately;
- partial/capped status reads are not treated as trustworthy absence;
- aggregate precedence preserves observable failure over incomplete weaker sources.

Therefore:

```text
P2_STATUS_CLASSIFICATION_DISCIPLINE = CODE_CONFIRMED
P2_FAIL_CLOSED_INCOMPLETE_STATUS_MODEL = CODE_CONFIRMED
P2_EXACT_ACTIONS_RUNNER_PRESTEP_CLASSIFICATION = NOT_TESTED
P2_F2_CORRECTNESS_IN_METAO_FIXTURE = NOT_TESTED
```

The candidate's PR/check model is relevant to F2 semantics, but F2 specifically targets the exact metaO Actions run/job state and the `tests NOT_TESTED` distinction. That exact behavior remains an execution requirement, not an inferred PASS from architectural similarity.

## F3/F4 relevance

Although this wave is limited to reducing P2 uncertainty before F1/F2 execution, the pinned adapter also exposes concrete write surfaces relevant to later fixtures:

- issue creation and label mutation;
- PR creation;
- write verification after mutation;
- explicit cache invalidation;
- idempotent handling for at least some already-absent write states;
- pull-request lookup and lightweight PR-reference search.

Upstream unit tests inspect issue creation and PR creation paths and verify expected HTTP-client calls/write-verification behavior.

This establishes candidate relevance only:

```text
P2_F3_CAPABILITY_RELEVANCE = TEST_CONFIRMED_UPSTREAM_PARTIAL
P2_F4_CAPABILITY_RELEVANCE = TEST_CONFIRMED_UPSTREAM_PARTIAL
P2_F3_EXECUTION = NOT_TESTED
P2_F4_EXECUTION = NOT_TESTED
```

Branch creation, commit creation, exact base/head binding, and the full predefined metaO F4 sequence still require execution under the frozen fixture.

## Cost-relevant code facts

The code contains several mechanics that can materially affect cost and therefore must be measured rather than assumed:

1. cache-enabled issue/label/PR paths may reduce requests in warm state;
2. required-ID stale-cache recovery can cause an additional non-cached request;
3. write verification can perform repeated reads under a bounded retry budget;
4. status-check rollup may use GraphQL and fallback REST sources;
5. a lightweight PR-reference search is explicitly designed to avoid one full fetch per candidate PR;
6. permission backoff can skip an already-known-unavailable primary source and avoid a wasted round trip.

These facts prevent simplistic cost accounting such as `one orchestrator action == one GitHub request`.

## Measurement consequences for #367

P2/P3 runtime observations MUST expose or instrument, where possible:

```text
CACHE_STATE
PRIMARY_GITHUB_REQUEST_COUNT
FALLBACK_GITHUB_REQUEST_COUNT
WRITE_VERIFY_REQUEST_COUNT
RETRY_COUNT
STATUS_SOURCE_USED
GRAPHQL_PRIMARY_SKIPPED
```

If the candidate runtime does not expose these, retain the existing protocol rule:

```text
UNDERLYING_GITHUB_CALLS = NOT_TESTED
```

Do not substitute source-code expected counts for observed runtime counts.

## Claim boundary

The strongest supported claim after this inspection is:

> At pin `26564aac4a02afc0989966ec2cd3e190884ba177`, Issue-Orchestrator contains concrete and upstream-unit-tested GitHub Issue/label/PR mechanics, plus code-confirmed fail-closed status-read semantics that are relevant to the frozen metaO GitHub orchestration fixtures.

Unsupported claims remain:

```text
P2_F1_CORRECTNESS = NOT_TESTED
P2_F2_CORRECTNESS = NOT_TESTED
P2_IS_CHEAPER = NOT_TESTED
P2_USES_FEWER_GITHUB_CALLS = NOT_TESTED
P2_USES_FEWER_TOKENS = NOT_TESTED
P2_IS_MORE_RELIABLE = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

## Evidence pointers

Pinned candidate files inspected:

```text
src/issue_orchestrator/adapters/github/github_adapter.py
src/issue_orchestrator/adapters/github/http_client.py
src/issue_orchestrator/ports/pull_request_tracker.py
tests/unit/test_github_adapter.py
README.md
```

Candidate pin verification:

```text
26564aac4a02afc0989966ec2cd3e190884ba177
```

## Next requirement

Execute F1/F2 through P2 and P3 under Issue #367. Repository inspection has now reduced capability uncertainty enough that lack of execution should be classified as a runtime/measurement blocker, not as uncertainty over whether the candidate has any GitHub integration implementation.