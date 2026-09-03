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
```

## Screening criteria

A subject advances toward formal admission only if direct repository evidence identifies a GitHub operation path relevant to at least one frozen fixture F1–F4. Preference is given to inspectable issue/PR/status/Actions mechanics whose API/tool boundary can later be counted or instrumented.

Popularity, stars, marketing language, and self-reported performance are not admission evidence.

## S1 — warestack/watchflow

Immutable screening pin: `302a32687d45e73ad431b6193a5f3e4a0ddf6e0c`.

Observed repository evidence:

- local setup requires a GitHub App;
- repository permissions include Actions read-only, Checks read/write, Issues read/write, Pull requests read/write, and Commit statuses read/write;
- subscribed webhook events include Issues, Pull request, Status, Workflow dispatch, Workflow job, and Workflow run;
- repository contains agent/rule logic around PR and repository analysis.

Interpretation:

Watchflow is directly relevant as a GitHub App/webhook/policy-system donor. The inspected evidence establishes a broad event/permission surface, but this screening did not identify an exact reusable API method for arbitrary Actions workflow-run-by-id plus workflow-job-by-id acquisition matching frozen F2.

Code-search attempts for exact workflow-run/job client/acquisition terms returned no match. Because search-index absence is not authoritative, this is classified as `NOT_IDENTIFIED_IN_SCREENING`, not `ABSENT`.

Disposition:

```text
GITHUB_APP_INTEGRATION = DOCUMENTED_AND_REPOSITORY_CONFIRMED
WORKFLOW_RUN_JOB_EVENTS = DOCUMENTED
F2_EXACT_RUN_JOB_API_PATH = NOT_IDENTIFIED_IN_SCREENING
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

Most useful new subject by repository evidence is Watchflow, but its likely value is currently architectural/semantic around GitHub App events, permissions and policy handling rather than an already-proven replacement for the exact F2 run/job acquisition path.

The next formal-candidate step, if warranted, is to freeze a protocol extension for one subject only after identifying a concrete implementation path and response boundary. Until then:

```text
ADDITIONAL_FORMAL_CANDIDATES = 0
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```
