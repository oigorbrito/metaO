# Roadmap 6 WU05 — Three Runtime Declarative Regression

Date: 2026-08-24

Status: IMPLEMENTATION PREPARED / COMPATIBILITY CORRECTED / EXECUTION PENDING / MERGE GATE PENDING

## Goal

Prove the metaO control plane can compose and govern three heterogeneous real runtimes without changing Core:

- OpenAI Agents SDK `0.20.0`;
- CrewAI `1.15.16`;
- LangGraph `1.2.11`.

The originally prepared OpenAI Agents 0.21.1 pin was superseded after real joint dependency resolution proved it incompatible with CrewAI 1.15.16. See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

The work reuses the existing declarative runtime factory, conformance/admission pipeline, certification lifecycle, deterministic router, quarantine overlay, evidence normalization and bounded failover behavior. No third-runtime special case is added to Core.

## Architecture under test

```text
one declarative manifest
  -> trusted runtime plugin factories
  -> existing Runtime Conformance Harness
  -> durable certificate admission
  -> freshness / revocation authority
  -> live health + quarantine authority
  -> deterministic routing
  -> bounded failover
  -> independent evidence acceptance
```

Framework SDKs remain confined to integration/plugin composition. Production adapters retain framework-neutral metaO types at their public boundary.

## Prepared real regression

`tests/integration/test_r6_wu05_three_real_runtimes.py`

The test creates one manifest containing all three real runtimes and prepares these scenarios:

1. exact active versions are installed;
2. first declarative load actively certifies all three runtimes;
3. restart inside certificate TTL reuses all three exact PASS generations without SDK execution;
4. TTL expiry recertifies all three and writes append-only generations;
5. revoking only the OpenAI Agents certificate recertifies only that runtime;
6. deterministic routing selects OpenAI Agents when its test routing metrics are best;
7. deterministic OpenAI Agents runtime failure causes bounded heterogeneous failover to CrewAI;
8. durable quarantine of OpenAI Agents overrides its routing score and routes to CrewAI.

Provider-free seams:

- OpenAI Agents 0.20.0 uses `tests/integration/_openai_agents_model.py`, a test-only implementation of the SDK public `Model` interface;
- CrewAI uses the local deterministic `BaseLLM`;
- LangGraph uses a deterministic local graph node.

No paid model provider is required.

## Certification lifecycle coverage

The regression exercises the Roadmap 5 authority model instead of creating new lifecycle semantics.

Exact binding remains:

```text
orchestrator_id
+ runtime_version
+ probe_execution_id
+ persisted evidence identity/provenance/digest
```

Freshness remains authoritative when configured. Revocation remains generation-specific and immutable. Latest-verdict authority remains generic and unchanged.

## Routing and failover coverage

The manifest deliberately declares test metrics:

```text
OpenAI Agents > CrewAI > LangGraph
```

This is test data, not a permanent product ranking.

The selector and failover loop remain framework-neutral. No framework-specific failover logic is introduced.

## Quarantine authority

Expected authority order remains:

```text
QUARANTINED / live health
  > deterministic routing metrics
  > historical feedback overlay
```

A quarantined preferred runtime is ineligible regardless of score.

## Active dependency set

```text
openai-agents == 0.20.0
crewai        == 1.15.16
langgraph     == 1.2.11
Python        == 3.12.x
```

Known compatible OpenAI client intersection:

```text
openai >=2.45,<3
```

## CI gate

`.github/workflows/roadmap6-three-runtime-regression.yml` installs the active exact pins, verifies versions, executes WU05, WU04 real OpenAI conformance, prior real lifecycle/declarative regressions, full unit suite and SDK-boundary guards.

The canonical integration workflow has also been strengthened to install and exercise all three runtimes, so a future canonical CI PASS cannot omit OpenAI Agents.

## Core preservation

```text
CORE_CHANGED_BY_WU05 = NO
ORCHESTRATOR_CONTRACT_CHANGED_BY_WU05 = NO
RUNTIME_FACTORY_CHANGED_BY_WU05 = NO
```

The compatibility correction after the first real resolver attempt also changes no `src/metao/**` file relative to the prior candidate SHA.

## Execution status

```text
WU05_IMPLEMENTATION = PREPARED
WU05_COMPATIBILITY_CORRECTION = APPLIED
WU05_LOCAL_EXECUTION_AFTER_FIX = PENDING
WU05_GITHUB_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
WU05_TEST_PASS = NOT CLAIMED
WU05_MERGE_GATE = PENDING
```

Roadmap 6 is assembled, not validated. The next legitimate gate is the complete local release-gate execution from PR #68.
