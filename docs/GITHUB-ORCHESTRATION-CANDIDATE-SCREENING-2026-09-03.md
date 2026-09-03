# GitHub Orchestration Candidate Screening — 2026-09-03

Status: EXPLORATORY_PRE_ADMISSION_SCREENING
Governing research: #365
Research branch: `research/issue-365-github-orchestration-cost`

## Purpose

Record exploratory discovery of additional public GitHub-oriented agent/orchestrator candidates without admitting them into the frozen comparative experiment.

This document is not a protocol extension and creates no cross-candidate cost result. Under `FROZEN_PROTOCOL_V1`, a newly discovered subject may enter the formal comparison only after a protocol extension/new version is frozen with an immutable pin and a comparable GitHub task boundary.

Therefore:

```text
DISCOVERY_SCREENING != FORMAL_CANDIDATE_ADMISSION
README_CLAIM != CODE_CONFIRMED
CODE_SEARCH_MISS != EVIDENCE_OF_ABSENCE
WORKFLOW_AUTOMATION != COMPARABLE_GITHUB_API_ADAPTER
OPAQUE_EXTERNAL_ACTION != ONE_GITHUB_API_CALL
SUBSCRIBED_WEBHOOK_EVENT != REGISTERED_RUNTIME_HANDLER
```

## Screening criteria

A subject advances toward formal admission only if direct repository evidence identifies a GitHub operation path relevant to at least one frozen fixture F1–F4. Preference is given to inspectable issue/PR/status/Actions mechanics whose API/tool boundary can later be counted or instrumented.

Popularity, stars, marketing language, and self-reported performance are not admission evidence.

## S1 — warestack/watchflow

Immutable screening pin: `302a32687d45e73ad431b6193a5f3e4a0ddf6e0c`.

Observed repository evidence:

- local setup requires a GitHub App;
- repository permissions include Actions read-only, Checks read/write, Issues read/write, Pull requests read/write, and Commit statuses read/write;
- documented subscribed webhook events include Issues, Pull request, Status, Workflow dispatch, Workflow job, and Workflow run;
- `src/webhooks/router.py` receives `X-GitHub-Event`, validates the payload, converts the event name to the project's `EventType`, and dispatches it;
- `src/core/models.py` defines `EventType.WORKFLOW_RUN`, but does not define `WORKFLOW_JOB` at the inspected pin;
- `src/rules/conditions/workflow.py` consumes `workflow_run` fields directly from the incoming event payload to calculate duration; this is webhook-payload evaluation, not arbitrary Actions run/job REST acquisition;
- `src/main.py` registers runtime handlers for PR, PR review/thread, push, check-run, issue-comment and deployment families, but does not register a `WORKFLOW_RUN` handler at the inspected pin;
- `src/webhooks/dispatcher.py` stores handler keys as provided but dispatches lookup using `event.event_type.value` (a string). `src/main.py` supplies `EventType` enum members as registration keys. Because `EventType` subclasses `str`, equality/hash behavior must be execution-tested before claiming this is a routing defect; source inspection alone is insufficient for a FAIL classification;
- upstream integration tests exercise Router -> Dispatcher -> TaskQueue and deduplication with string handler keys such as `"pull_request"` and `"push"`; the inspected tests do not establish enum-key registration compatibility used by `src/main.py`;
- `src/integrations/github/service.py` uses direct `httpx` requests to `https://api.github.com`, but the observed methods are repository metadata and contents/governance-file checks; no Actions run/job acquisition method is present in that inspected service.

Interpretation:

Watchflow is directly relevant as a GitHub App/webhook/policy-system donor. The deeper source inspection narrows the earlier uncertainty: the repository has a real `workflow_run` semantic consumer, but that consumer evaluates webhook payload already supplied by GitHub. The runtime bootstrap inspected at the same immutable pin does not register a `workflow_run` handler, and the inspected REST service does not expose arbitrary Actions run/job acquisition.

This is stronger than a code-search miss but still does not justify a repository-wide absence claim: another uninspected path could exist. The defensible F2 classification remains `NOT_IDENTIFIED_AT_INSPECTED_PIN/PATHS`, not `ABSENT`.

For frozen F2, this distinction is material. F2 starts from exact repository/run/job identities and must acquire current GitHub Actions state while preserving workflow/job failure versus configured-step execution. A webhook-only payload path is not operationally equivalent to arbitrary run/job lookup.

Disposition:

```text
GITHUB_APP_INTEGRATION = DOCUMENTED_AND_CODE_CONFIRMED
WORKFLOW_RUN_EVENT_MODEL = CODE_CONFIRMED
WORKFLOW_RUN_PAYLOAD_CONDITION = CODE_CONFIRMED
WORKFLOW_RUN_RUNTIME_HANDLER_REGISTRATION = NOT_IDENTIFIED_AT_INSPECTED_BOOTSTRAP
WORKFLOW_JOB_EVENT_MODEL = NOT_IDENTIFIED_AT_INSPECTED_PIN
DIRECT_GITHUB_REST_SERVICE = CODE_CONFIRMED_FOR_REPO_METADATA_AND_CONTENTS
DISPATCHER_STRING_KEY_PATH = TEST_PRESENT_UPSTREAM
DISPATCHER_ENUM_KEY_COMPATIBILITY = NOT_TESTED
F2_EXACT_RUN_JOB_API_PATH = NOT_IDENTIFIED_AT_INSPECTED_PIN/PATHS
F2_OPERATIONAL_EQUIVALENCE = NOT_ESTABLISHED
FORMAL_COST_CANDIDATE = NOT_ADMITTED
POTENTIAL_ROLE = REFERENCE/ADAPT_FOR_GITHUB_APP_WEBHOOK_POLICY_BOUNDARY
```

## S2 — PR-Pilot-AI/smart-workflows

Immutable screening pin: `8d6db3cc358a06b2561fb781bf204f76c0d270bb`.

Observed repository evidence:

`automations/pr-auto-review/workflow.yaml` triggers on `pull_request: opened` and delegates handling to:

```text
PR-Pilot-AI/smart-actions/pr-creation-handler@v1
```

with `PR_PILOT_API_KEY` and PR number as inputs.

Interpretation:

The repository is a GitHub Actions workflow donor rather than a directly observed GitHub API adapter. At the inspected boundary, underlying GitHub requests, model calls, retries and token usage are hidden behind an external action/service. Treating one workflow/action invocation as one GitHub API call would violate the frozen counting rule.

Disposition:

```text
PR_EVENT_AUTOMATION = CODE_CONFIRMED_WORKFLOW
EXTERNAL_ACTION_DELEGATION = YES
UNDERLYING_GITHUB_CALLS = NOT_TESTED
TOKEN_TELEMETRY = NOT_TESTED
F2_COMPARABLE_PATH = NOT_IDENTIFIED
FORMAL_COST_CANDIDATE = NOT_ADMITTED
POTENTIAL_ROLE = WORKFLOW_PATTERN_REFERENCE
```

## S3 — wajidraza/mcp-github-orchestrator

Immutable screening pin: `5ef0d16f71ba8c32fd0b4e9918ad00b2bb37a4a9`.

Observed repository evidence:

README claims a stack including FastMCP, PyGithub and Anthropic SDK and describes the project as a GitHub repository orchestrator/PR reviewer. A repository code search for issues/pulls/Actions workflow run/job/API terms returned no matching implementation in this screening.

The README also makes strong architecture/performance/coverage claims without the screening locating executable evidence for the frozen fixtures. Those claims are therefore not used for admission.

Disposition:

```text
DOCUMENTED_GITHUB_RELEVANCE = YES
CODE_CONFIRMED_COMPARABLE_GITHUB_OPERATION = NO_IN_SCREENING
README_PERFORMANCE_CLAIMS_USED = NO
FORMAL_COST_CANDIDATE = NOT_ADMITTED
```

## Screening outcome

No newly screened subject is admitted to the frozen cost experiment in this document.

The deeper Watchflow inspection changes the precision, not the decision. It confirms useful GitHub webhook/policy mechanics but does not establish the arbitrary Actions run/job lookup required by F2. Therefore there is no scientific basis to spend a formal comparative-cost arm on Watchflow F2 yet.

Watchflow remains potentially useful as a donor for event ingestion, signature verification, dedup/routing and policy-trigger semantics. Those capabilities must remain below metaO authority boundaries if ever adapted.

The next formal-candidate step, if warranted, is to freeze a protocol extension for one subject only after identifying a concrete implementation path and response boundary. Until then:

```text
ADDITIONAL_FORMAL_CANDIDATES = 0
WATCHFLOW_F2_EXTENSION = NOT_JUSTIFIED_BY_CURRENT_EVIDENCE
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```
