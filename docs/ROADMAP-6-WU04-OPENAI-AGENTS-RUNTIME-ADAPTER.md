# Roadmap 6 WU04 — OpenAI Agents Runtime Adapter

Date: 2026-08-24

Status: IMPLEMENTATION PREPARED / EXECUTION PENDING / MERGE GATE PENDING

## Goal

Implement the third runtime selected by Roadmap 6 WU03 without changing metaO Core or the existing `OrchestratorContract`.

Selected runtime:

- OpenAI Agents SDK
- pinned real sandbox version: `openai-agents==0.21.1`

## Architecture

```text
Mission
  -> metaO Core / OrchestratorContract
  -> OpenAIAgentsOrchestratorAdapter
  -> injected Runner + configured Agent
  -> OpenAI Agents SDK runtime
```

Production boundary rule:

```text
src/metao/adapters/openai_agents.py
```

uses only duck typing for:

- `runner.run_sync(agent, input)`;
- result `final_output`.

It does **not** import:

- `agents`;
- `openai`;
- Responses API types;
- provider-specific model types.

The SDK is imported only by the real integration sandbox/test.

## Contract mapping

| metaO contract | Adapter behavior |
| --- | --- |
| `descriptor` | adapter-owned immutable descriptor, capabilities `workflow` + `agent` |
| `health()` | healthy only when `run_sync` is callable and an agent is configured |
| `execute()` | deterministic neutral mission/context JSON -> `run_sync` -> normalized `ExecutionResult` |
| runtime exception | normalized to `ExecutionStatus.FAILED`; exception does not escape the adapter |
| `cancel()` | preserves existing metaO pre-dispatch cancellation semantics |
| evidence | deterministic digest + runtime/execution provenance binding |

## Why pre-dispatch cancellation remains the boundary

OpenAI Agents supports active cancellation for streamed results, but the current metaO Core contract exposes:

```python
cancel(execution_id: str) -> None
```

and does not expose a runtime execution handle.

Changing the Core contract only to expose one framework's streaming result would violate the central architecture test. Therefore WU04 deliberately preserves the same pre-dispatch cancellation semantics used by the LangGraph and CrewAI adapters.

A future generic execution-handle evolution is only valid if independently justified for all runtimes.

## Deterministic real SDK sandbox

The integration test uses first-party OpenAI Agents testing utilities:

```text
agents.testing.ScriptedModel
agents.testing.assistant_message
```

The upstream SDK documents these utilities as provider-neutral, in-memory test doubles that make no model API requests.

The real SDK sandbox therefore exercises:

```text
real Agent
+ real Runner.run_sync
+ real runner loop
+ ScriptedModel provider boundary
+ metaO adapter
+ existing Runtime Conformance Harness
```

without requiring an OpenAI API key or paid provider call.

Tracing is explicitly disabled in the real test.

## Prepared tests

### SDK-neutral unit suite

`tests/unit/test_roadmap_6_work_unit_04.py`

Prepared assertions:

1. adapter structurally satisfies `OrchestratorContract`;
2. descriptor/version/capabilities remain metaO-owned;
3. health checks synchronous runner + configured agent;
4. mission/context input serialization is deterministic;
5. scalar final output is normalized;
6. mapping final output is preserved;
7. runtime exceptions become `FAILED` results;
8. pre-dispatch cancellation prevents SDK dispatch;
9. evidence normalization is deterministic and correctly bound;
10. production adapter source contains no `agents` / `openai` SDK import.

### Real SDK integration suite

`tests/integration/test_r6_wu04_openai_agents_real.py`

Prepared assertions:

1. installed package is exactly `openai-agents==0.21.1`;
2. real `Runner.run_sync` executes against `ScriptedModel` without a provider;
3. the existing SDK-neutral Runtime Conformance Harness passes the real runtime boundary when executed;
4. cancellation-before-dispatch does not consume the SDK model script.

Important: these are **prepared assertions**, not claimed PASS results.

## CI gate

`.github/workflows/roadmap6-openai-agents-runtime.yml`

Prepared gate:

1. install metaO;
2. install `openai-agents==0.21.1`;
3. verify exact installed version;
4. run WU04 unit suite;
5. run WU04 real deterministic integration suite;
6. run existing runtime-conformance regression;
7. run full unit regression;
8. enforce no `agents` / `openai` imports anywhere under `src/metao`.

## Execution status

At WU04 creation time:

```text
WU04_IMPLEMENTATION = PREPARED
WU04_LOCAL_EXECUTION = BLOCKED_BY_CURRENT_CHAT_NETWORK
WU04_GITHUB_ACTIONS_EXECUTION = PENDING
WU04_TEST_PASS = NOT CLAIMED
WU04_MERGE_GATE = PENDING
CORE_CHANGED = NO
SDK_IN_CORE = NO
```

The current chat sandbox cannot resolve `github.com`, so it cannot clone/install the repository for local execution. The project also carries the known GitHub-hosted Actions pre-step failure blocker. Neither condition is treated as a functional code failure, and neither permits a PASS claim.

## Next work unit after executable WU04 evidence exists

Roadmap 6 WU05 — Three Runtime Declarative Certification / Selection should:

1. compose LangGraph 1.2.11, CrewAI 1.15.16, and OpenAI Agents 0.21.1 in one manifest;
2. actively certify all three using the existing admission/conformance pipeline;
3. prove exact certificate reuse on restart;
4. prove deterministic selection across three heterogeneous runtimes;
5. prove failover when the preferred runtime fails or becomes ineligible;
6. prove quarantine/live health remain authoritative over feedback;
7. preserve freshness/revocation/latest-verdict authority;
8. assert Core source remains unchanged.

WU05 must not be called PASS until those real runtimes execute.
