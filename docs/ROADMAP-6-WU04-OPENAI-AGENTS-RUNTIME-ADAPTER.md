# Roadmap 6 WU04 — OpenAI Agents Runtime Adapter

Date: 2026-08-24

Status: IMPLEMENTATION PREPARED / COMPATIBILITY CORRECTED / EXECUTION PENDING / MERGE GATE PENDING

## Goal

Implement the third runtime selected by Roadmap 6 WU03 without changing metaO Core or the existing `OrchestratorContract`.

Selected runtime:

- OpenAI Agents SDK;
- active executable version: `openai-agents==0.20.0`.

The originally prepared 0.21.1 pin was superseded after the real joint pip resolver proved it incompatible with CrewAI 1.15.16. See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

## Architecture

```text
Mission
  -> metaO Core / OrchestratorContract
  -> OpenAIAgentsOrchestratorAdapter
  -> injected Runner + configured Agent
  -> OpenAI Agents SDK runtime
```

Production boundary:

```text
src/metao/adapters/openai_agents.py
```

uses duck typing for:

- `runner.run_sync(agent, input)`;
- result `final_output`.

It does **not** import `agents`, `openai`, Responses API types or provider-specific model types.

## Contract mapping

| metaO contract | Adapter behavior |
| --- | --- |
| `descriptor` | adapter-owned immutable descriptor, capabilities `workflow` + `agent` |
| `health()` | healthy only when `run_sync` is callable and an agent is configured |
| `execute()` | deterministic neutral mission/context JSON -> `run_sync` -> normalized `ExecutionResult` |
| runtime exception | normalized to `ExecutionStatus.FAILED`; exception does not escape adapter |
| `cancel()` | preserves metaO pre-dispatch cancellation semantics |
| evidence | deterministic digest + runtime/execution provenance binding |

## Why pre-dispatch cancellation remains the boundary

The current Core contract exposes:

```python
cancel(execution_id: str) -> None
```

and does not expose a framework execution handle. Changing Core only for one SDK would violate the central architecture test. WU04 therefore keeps the same pre-dispatch cancellation semantics used by the existing adapters.

## Deterministic real SDK sandbox

OpenAI Agents 0.20.0 preserves the public provider-neutral `Model` interface and synchronous `Runner.run_sync` path required by the adapter.

The later packaged `agents.testing.ScriptedModel` used by the original 0.21.1 preparation is not used by the corrected candidate. Provider-free tests instead use:

```text
tests/integration/_openai_agents_model.py
```

This small test-only model implements the SDK public `Model` boundary, queues deterministic success/error steps and performs no provider call.

The real SDK sandbox therefore exercises:

```text
real Agent
+ real Runner.run_sync
+ real runner loop
+ public Model provider boundary
+ metaO adapter
+ existing Runtime Conformance Harness
```

Tracing is explicitly disabled in the real test.

## Prepared tests

### SDK-neutral unit suite

`tests/unit/test_roadmap_6_work_unit_04.py`

Prepared assertions include:

1. adapter structurally satisfies `OrchestratorContract`;
2. descriptor/version/capabilities remain metaO-owned;
3. health checks synchronous runner + configured agent;
4. mission/context serialization is deterministic;
5. scalar/mapping final output normalization;
6. runtime exceptions become `FAILED` results;
7. pre-dispatch cancellation prevents SDK dispatch;
8. evidence normalization is deterministic and correctly bound;
9. production adapter source contains no SDK import.

### Real SDK integration suite

`tests/integration/test_r6_wu04_openai_agents_real.py`

Prepared assertions:

1. installed package is exactly `openai-agents==0.20.0`;
2. real `Runner.run_sync` executes against the deterministic test-only `Model` without a provider;
3. the existing SDK-neutral Runtime Conformance Harness accepts the real runtime boundary;
4. cancellation-before-dispatch does not consume a model step.

These remain prepared assertions until execution.

## CI gate

`.github/workflows/roadmap6-openai-agents-runtime.yml` now installs and verifies `openai-agents==0.20.0`, runs the WU04 unit/integration regressions, runtime-conformance regression, full unit suite and SDK-neutral production boundary guard.

## Compatibility evidence

```text
openai-agents 0.20.0 -> openai >=2.45,<3
crewai 1.15.16       -> openai >=2.30,<3
shared range          -> openai >=2.45,<3
CORE_CHANGED          -> NO
ORCHESTRATOR_CONTRACT_CHANGED -> NO
```

## Execution status

```text
WU04_IMPLEMENTATION = PREPARED
WU04_COMPATIBILITY_CORRECTION = APPLIED
WU04_LOCAL_EXECUTION_AFTER_FIX = PENDING
WU04_TEST_PASS = NOT CLAIMED
WU04_MERGE_GATE = PENDING
CORE_CHANGED = NO
SDK_IN_CORE = NO
```

The next legitimate step is executable evidence from the full canonical local release gate, not further feature expansion.
