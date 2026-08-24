# OpenAI Agents compatibility correction

Status: ACTIVE CORRECTION FOR THE ROADMAP 2-7 CANONICAL CANDIDATE.

## Trigger

The first real Windows dependency-resolution attempt for the canonical Roadmap 2-7 local release gate reached pip and failed before any functional test executed.

Observed resolver conflict:

```text
openai-agents 0.21.1 -> openai >=3.0.0,<4
crewai 1.15.16       -> openai >=2.30.0,<3
result                -> ResolutionImpossible
```

This is integration/bootstrap evidence, not a metaO functional test failure.

## Evidence-based correction

The selected third runtime remains OpenAI Agents SDK. Only the exact adopted version changes:

```text
OpenAI Agents SDK 0.20.0 -> openai >=2.45.0,<3
CrewAI 1.15.16          -> openai >=2.30.0,<3
compatible intersection -> openai >=2.45.0,<3
LangGraph                -> 1.2.11
Python                   -> 3.12.x
```

The upstream OpenAI Agents 0.20.0 package still exposes the synchronous `Runner.run_sync` execution path and the public provider-neutral `Model` interface required by the existing thin adapter boundary.

## Test seam correction

OpenAI Agents 0.21.1 introduced the first-party `agents.testing.ScriptedModel` utility used by the originally prepared tests. Version 0.20.0 does not expose that utility as a public package surface.

The canonical candidate therefore uses a small metaO-owned **test-only** deterministic model in:

```text
tests/integration/_openai_agents_model.py
```

It implements the OpenAI Agents public `Model` boundary, returns normalized SDK output items, records calls, supports deterministic queued success/error steps, and performs no provider request.

This helper is not production code and is not imported by metaO Core or the runtime adapter.

## Architecture impact

```text
THIRD_RUNTIME_SELECTED = OpenAI Agents SDK
THIRD_RUNTIME_PIN = 0.20.0
CREWAI_PIN = 1.15.16
LANGGRAPH_PIN = 1.2.11
CORE_CHANGE_REQUIRED = NO
ORCHESTRATOR_CONTRACT_CHANGE_REQUIRED = NO
PRODUCTION_ADAPTER_SDK_IMPORT_REQUIRED = NO
PAID_PROVIDER_REQUIRED_FOR_GATE = NO
```

The governing invariant remains:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

and the architecture rule remains:

```text
ADOPT > ADAPT > BUILD
```

## Historical documentation rule

Roadmap 6 documents that say `0.21.1` describe the **originally evaluated/prepared selection** and are retained as historical decision evidence. They must not be interpreted as the active executable pin after this correction.

For all executable gates, integration tests, current readiness status and canonical merge decisions, this document supersedes those historical `0.21.1` pin statements.

## Validation status

```text
DEPENDENCY_CONFLICT_0_21_1 = CONFIRMED_BY_REAL_PIP_RESOLVER
COMPATIBLE_0_20_0_RANGE = CONFIRMED_BY_UPSTREAM_PACKAGE_METADATA
CANONICAL_GATE_UPDATED = YES
FUNCTIONAL_TEST_EXECUTION_AFTER_FIX = PENDING
FUNCTIONAL_PASS = NOT CLAIMED
MERGE_GATE = PENDING
```

A new full local release-gate run from the exact canonical candidate SHA is required before any PASS or merge claim.
