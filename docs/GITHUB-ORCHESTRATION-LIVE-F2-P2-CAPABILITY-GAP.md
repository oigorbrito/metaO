# GitHub Orchestration Live F2 — P2 Capability Gap

Status: EVIDENCE_RECORD
Governing research: #365
Execution handoff: #367
Frozen live packet: `docs/GITHUB-ORCHESTRATION-LIVE-F2-COST-PACKET-V1.md`

## Claim

At Issue-Orchestrator pin `26564aac4a02afc0989966ec2cd3e190884ba177`, the inspected supported GitHub/status surface provides PR/head-commit status-rollup acquisition but no supported path was identified for the exact F2 live requirement: acquire an arbitrary GitHub Actions workflow run by run identity and its workflow job by job identity, then preserve runner-allocation and configured-step-execution distinctions.

This is a fixture capability gap. It is not a product failure and does not invalidate the donor's status-rollup capability.

## Frozen F2 identities

- metaO target SHA: `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
- workflow run: `33760147938`
- workflow job: `100665907672`
- Issue-Orchestrator pin: `26564aac4a02afc0989966ec2cd3e190884ba177`

Required classification:

```text
WORKFLOW_JOB = FAIL
RUNNER_ALLOCATED = NO
CONFIGURED_STEPS_EXECUTED = NO
REPOSITORY_TESTS = NOT_TESTED
HOSTED_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
PRODUCT_FUNCTIONAL_FAILURE = NOT_PROVEN
```

## Exact-pin positive evidence

Inspected code at the immutable donor pin confirms a concrete PR/head-commit status path:

- `src/issue_orchestrator/ports/pull_request_tracker.py`
  - exposes `read_pr_status_check_rollup(pr_number, ...)`;
  - models status values `SUCCESS`, `FAILURE`, `PENDING`, `EXPECTED`, `ERROR`;
  - explicitly models read capability `ok`, `permission_denied`, `transient_error`.
- `src/issue_orchestrator/adapters/github/http_client.py`
  - aggregates REST `/check-runs` for a commit;
  - reads legacy combined commit status;
  - uses a fail-safe allow-list for passing completed check conclusions;
  - distinguishes permission denial, transient errors and truncated reads.
- `src/issue_orchestrator/adapters/github/github_adapter.py`
  - implements `PullRequestTracker` and maps PR/head-commit rollup states through the GitHub adapter.

Repository code search at this same pin reports multiple references to `read_pr_status_check_rollup` and `/check-runs`, confirming that this is an intentional supported surface rather than an incidental string.

## Exact F2 run/job path reconnaissance

Targeted code searches against the exact pin were performed for GitHub Actions run/job acquisition concepts and routes, including:

```text
"actions/runs"
"actions/runs/"
"actions/jobs"
"workflow-runs"
"workflow job"
"jobs/{"
"/actions/runner"
```

These targeted searches returned zero matches. A broader `workflow_run` search returned one match in `tests/unit/test_github_workflows.py`; inspection showed that file validates the donor repository's workflow YAML / merge-group behavior and is not an API client for reading Actions run or job state.

A broad `runs/{` search produced unrelated application/documentation routes and is therefore not evidence of GitHub Actions run acquisition.

Important evidence rule: zero search results alone are not treated as proof of absence. The capability-gap classification combines the exhaustive exact-pin repository reconnaissance with direct inspection of the relevant GitHub adapter/client/port surfaces and positive confirmation of the different PR/head-commit status abstraction that the donor actually exposes.

## Classification

```text
P2_GENERAL_PR_STATUS_ROLLUP_CAPABILITY = CODE_CONFIRMED
P2_CONTROLLED_F2_SEMANTICS = PASS
P2_F2_LIVE_EXACT_RUN_JOB_ACQUISITION = BLOCKED_CAPABILITY_GAP
P2_F2_LIVE_COST_MEASUREMENT = BLOCKED
P2_F2_LIVE_COST_RANKING = NOT_TESTED
P2_PRODUCT_FAILURE = NO
P2_DONOR_INVALID = NO
```

The earlier controlled replay PASS remains valid within its replay boundary. It cannot be promoted to a live F2 cost observation because the live packet requires the candidate-supported acquisition path rather than a handwritten surrogate.

## P3 impact

The gap does not block P3 under the frozen packet. P3 explicitly permits deterministic GitHub acquisition of the exact run/job facts and delegates semantic reasoning only when required. If deterministic classification suffices, the correct observation is:

```text
MODEL_CALLS = 0
```

No LLM call may be forced merely to make P3 differ from P1.

## Cost interpretation

No P1 × P2 × P3 three-way live cost winner can be declared for this exact F2 packet because P2 does not satisfy the live fixture's acquisition capability gate.

This result is nevertheless cost-relevant engineering evidence: adopting the donor as-is for exact Actions run/job reconciliation would require either extending/adapting its GitHub surface or keeping that deterministic acquisition outside the donor. The cost of such adaptation has not been measured and must not be assumed.

## Unblock conditions

P2/F2 live becomes executable only if one of the following occurs under a new, predeclared evidence state:

1. an existing exact-pin supported Actions run/job API path is identified with code/test evidence that was missed here; or
2. a donor version/pin containing that capability is evaluated under a protocol extension frozen before comparative results; or
3. an explicit adapter extension is implemented and then evaluated as an adapted subject, not misrepresented as the original donor.

## Decision boundary

```text
METAO_DETERMINISTIC_IS_CHEAPER = NOT_TESTED
EXTERNAL_AGENT_IS_CHEAPER = NOT_TESTED
HYBRID_IS_CHEAPER = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```
