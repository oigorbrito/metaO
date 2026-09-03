# GitHub Orchestration Cost Experiment

Status: FROZEN_PROTOCOL_V1
Governing Issue: #365
Product code change: NO
Architecture decision: NOT AUTHORIZED BY THIS PROTOCOL

## Research question

For a fixed GitHub engineering task with identical correctness and authority constraints, which execution placement has the lowest observable total cost:

1. deterministic metaO/direct GitHub API or connector operations;
2. external agent/orchestrator execution;
3. hybrid execution where deterministic mechanics remain outside the LLM path and reasoning is delegated only when required?

The experiment evaluates execution placement. It does not grant GitHub, an agent framework, or an orchestrator any metaO policy, budget, durable-state, evidence, or independent-acceptance authority.

## Frozen subjects

Baseline metaO:

```text
repository = tihotm/metaO
pin = b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437
code_search_indexed = false
```

Candidate A:

```text
repository = issue-orchestrator/issue-orchestrator
pin = 26564aac4a02afc0989966ec2cd3e190884ba177
```

Additional candidates may be added only as a new protocol version or as an explicitly recorded protocol extension before their results are inspected. They must have an immutable pin and a comparable GitHub task path.

## Current evidence boundary

Repository-tree inspection of the metaO baseline has not identified a dedicated GitHub integration module under `src/metao/`. Because GitHub code search for `tihotm/metaO` is not indexed, zero code-search results are not evidence of absence.

The current metaO engineering workflow uses GitHub as a persistent operational ledger and uses repository/API/connector operations outside Core. This is an observed repository/workflow fact, not proof that deterministic placement is cheaper.

At the pinned Issue-Orchestrator revision, repository documentation states that it claims eligible GitHub issues, uses GitHub labels and observed worktree state, re-observes GitHub before state advancement, and can publish pull requests for human merge. These documented capabilities establish candidate relevance only; they are not cost evidence.

## Cost model

Do not add heterogeneous quantities directly.

Primary result is a cost vector:

```text
C_vector = {
  llm_input_tokens,
  llm_output_tokens,
  model_calls,
  github_api_or_tool_calls,
  retries,
  failed_attempts,
  wall_time_seconds,
  compute_measurement,
  human_corrections,
  maintenance_proxy
}
```

A monetized `C_total` is allowed only when every included conversion factor is pinned to a dated source and the measurement boundaries are comparable.

Project objective remains conceptually:

```text
C_total = C_llm_tokens + C_api_calls + C_compute + C_failure_retry + C_maintenance
```

but that expression MUST NOT be evaluated numerically until units are normalized by declared conversion factors.

## Status vocabulary

For each metric or task:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
NOT_APPLICABLE
```

Missing observability is `NOT_TESTED`, never zero.

## Fixtures

### F1 Read-only issue-to-evidence lookup

Input:
- exact repository;
- exact issue number;
- request to return issue title/state, relevant acceptance criteria, and one exact repository file required by the issue.

Required outcome:
- correct issue identity;
- correct file identity;
- no mutation;
- provenance sufficient to audit both reads.

Purpose: isolates deterministic GitHub retrieval from reasoning-heavy implementation.

### F2 Deterministic repository status reconciliation

Input:
- exact repository;
- exact commit SHA;
- request to report CI/workflow state without inferring product PASS from absent execution.

Required outcome:
- exact SHA binding;
- distinguish workflow/job failure from tests not executed;
- preserve `BLOCKED` versus `FAIL` semantics;
- no repository mutation.

Purpose: exercises multi-call GitHub observation and classification.

### F3 Bounded issue update

Input:
- exact issue;
- predeclared evidence payload;
- exact required comment/update contents.

Required outcome:
- exactly one intended mutation;
- no unrelated issue/repository mutation;
- returned mutation identifier or auditable updated state.

Purpose: measures deterministic write mechanics separately from content generation.

### F4 Issue-to-branch-to-PR orchestration

Input:
- bounded research/documentation issue;
- exact base SHA;
- predefined file payload requiring no architectural reasoning.

Required outcome:
- issue association preserved;
- branch from exact base;
- one coherent commit;
- draft PR with exact base/head binding;
- no merge;
- no authority escalation.

Purpose: compares end-to-end GitHub mechanics around the same predetermined change.

## Correctness gate

A candidate run is comparable only if all fixture-required outcomes are met.

A cheaper incorrect run is `FAIL`, not a cost winner.

For write fixtures, extra mutation is a correctness failure even if the requested mutation also succeeds.

## Execution placements

### P1 Deterministic/direct

GitHub operations are executed through deterministic API/connector calls. LLM reasoning may choose the already-declared operation sequence for the experimental harness, but payload-independent GitHub mechanics are not delegated to another coding agent.

### P2 External orchestrator/agent

The same fixture is handed to the candidate's supported orchestration path. GitHub mechanics performed internally by that system remain inside its measurement boundary.

### P3 Hybrid

Deterministic GitHub reads/writes are executed directly; only portions requiring interpretation or synthesis enter an LLM/agent path.

## Controlled variables

For a comparable run record, hold constant or record:

- fixture version;
- subject pin;
- target repository and target SHA;
- GitHub account/permission class;
- model/provider/version when an LLM is used;
- prompt/input payload;
- context supplied to the model;
- tool availability;
- retry policy;
- timeout policy;
- concurrency;
- cache assumptions;
- warm/cold state when material;
- network/proxy conditions when observable;
- measurement start/end boundary.

## LLM/token rules

Token claims require directly exposed usage from the model/provider/runtime or an artifact that is explicitly defined as the authoritative usage record.

Forbidden:

```text
INFER_TOKENS_FROM_TEXT_LENGTH = NO
ESTIMATE_UNOBSERVED_AGENT_TOKENS = NO
TREAT_UNOBSERVED_TOKENS_AS_ZERO = NO
```

If only the direct path exposes tokens while a candidate does not, token cost is not comparable and remains `NOT_TESTED` for the cross-candidate claim.

## API/tool-call rules

Count calls at the declared boundary. Record successful and failed calls separately.

A wrapper call that internally performs unknown multiple GitHub operations cannot be compared as one API call against individually exposed REST calls unless the internal call count is observable. In that case report:

```text
wrapper_invocations = observed
underlying_github_calls = NOT_TESTED
```

Do not silently equate wrapper invocations with network requests.

## Repetition

Deterministic paths:
- one run may establish functional correctness for an exact immutable fixture;
- cost timing claims require at least 5 comparable repetitions when timing is material.

LLM/agent paths:
- minimum 5 valid repetitions for comparative cost/reliability claims;
- retain every valid observation;
- report median and full range at minimum;
- report failures and retries separately;
- no rerun-until-success filtering.

A single agent run is exploratory evidence only.

## Raw observation record

Each run MUST preserve:

```text
RUN_ID:
PROTOCOL_VERSION: github-orchestration-cost-v1
PLACEMENT:
SUBJECT_REPOSITORY:
SUBJECT_PIN:
FIXTURE_ID:
TARGET_REPOSITORY:
TARGET_SHA:
MODEL_PROVIDER_VERSION:
PROMPT_OR_INPUT_DIGEST:
CONTEXT_BOUNDARY:
TOOL_BOUNDARY:
RETRY_POLICY:
TIMEOUT_POLICY:
CONCURRENCY:
CACHE_STATE:
START_TIMESTAMP:
END_TIMESTAMP:
LLM_INPUT_TOKENS:
LLM_OUTPUT_TOKENS:
MODEL_CALLS:
WRAPPER_TOOL_CALLS:
UNDERLYING_GITHUB_CALLS:
RETRIES:
FAILED_ATTEMPTS:
WALL_TIME_SECONDS:
COMPUTE_MEASUREMENT:
HUMAN_CORRECTIONS:
MUTATIONS_OBSERVED:
CORRECTNESS_RESULT:
RAW_ARTIFACT_POINTERS:
DEVIATIONS:
BLOCKERS:
```

Use `NOT_TESTED` or `NOT_APPLICABLE` explicitly where appropriate.

## Analysis rules

1. Reject correctness failures before cost ranking.
2. Never rank a candidate on a metric not observed comparably across the candidates being ranked.
3. Report the cost vector before any scalar score.
4. A Pareto result is allowed: one placement may use fewer model tokens but more API calls or more maintenance surface.
5. If a scalar cost is later required, publish conversion factors and sensitivity analysis first.
6. Separate deterministic mechanics from semantic reasoning wherever fixtures permit; this is necessary to test the hybrid hypothesis rather than assume it.
7. No architecture decision follows from one fixture family alone.

## Maintenance proxy

Maintenance cost is not inferred from repository size, language, stars, or popularity.

A maintenance proxy may be measured only through predeclared equivalent change tasks, such as:
- add one GitHub field to the observation record;
- add one retry classification;
- change one label mapping;
- add one GitHub write operation with idempotency protection.

Record files changed, changed LOC, test changes, and validation effort. Do not translate this proxy to currency without an explicit model.

## Authority invariants

Every placement must preserve:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
RUNTIME_SELF_REPORT != GOVERNANCE_AUTHORITY
SECOND_METAO_CORE = NO
SECOND_POLICY_AUTHORITY = NO
SECOND_DURABLE_WORKFLOW_AUTHORITY = NO
SECOND_EVIDENCE_AUTHORITY = NO
SECOND_ACCEPTANCE_AUTHORITY = NO
```

A candidate that requires violating these constraints is not a comparable lower-cost substitute for the same semantic task.

## Threats to validity

Known threats include:
- GitHub connector wrappers may hide underlying request counts;
- token telemetry may be unavailable for some agent runtimes;
- model/provider behavior varies over time;
- target-repository cache and GitHub latency can affect wall time;
- Issue-Orchestrator includes broader workflow/guardrail behavior than a direct API call, so task boundaries must prevent charging it for functionality outside the fixture or crediting it for functionality the fixture did not require;
- current metaO has no proven dedicated in-product GitHub module at the pinned baseline, so P1 initially represents deterministic/direct placement rather than a proven existing product implementation.

## Blocker policy

External service or runtime failures are recorded per run with:
- blocker_id;
- type;
- blocked operation;
- observed evidence;
- impact;
- independent work that can continue;
- objective unblock condition.

A blocker does not erase successful observations from other fixtures or placements.

## Frozen disposition before execution

```text
METAO_DETERMINISTIC_IS_CHEAPER = NOT_TESTED
EXTERNAL_AGENT_IS_CHEAPER = NOT_TESTED
HYBRID_IS_CHEAPER = NOT_TESTED
TOKEN_COMPARISON = NOT_TESTED
MONETIZED_TOTAL_COST = NOT_TESTED
PRODUCT_PLACEMENT_DECISION = NOT_AUTHORIZED
```

This state may change only from recorded comparable observations under this protocol or a versioned successor.