# Roadmap 6 WU05 — Three Runtime Declarative Regression

Date: 2026-08-24

Status: IMPLEMENTATION PREPARED / EXECUTION PENDING / MERGE GATE PENDING

## Goal

Prove the metaO control plane can compose and govern three heterogeneous real runtimes without changing Core:

- OpenAI Agents SDK `0.21.1`
- CrewAI `1.15.16`
- LangGraph `1.2.11`

The work reuses the existing declarative runtime factory, conformance/admission pipeline, certification lifecycle, deterministic router, quarantine overlay, evidence normalization, and bounded failover behavior.

No third-runtime special case is added to Core.

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

The framework SDKs remain confined to integration/plugin composition. Production adapters retain framework-neutral metaO types at their public boundary.

## Prepared real regression

`tests/integration/test_r6_wu05_three_real_runtimes.py`

The test creates one manifest containing all three real runtimes and prepares these scenarios:

1. exact pinned versions are installed;
2. first declarative load actively certifies all three runtimes;
3. restart inside the certificate TTL reuses all three exact PASS generations without SDK execution;
4. TTL expiry recertifies all three and writes new append-only generations;
5. revoking only the OpenAI Agents certificate recertifies only that runtime while CrewAI/LangGraph reuse their latest reusable generations;
6. deterministic routing selects OpenAI Agents when its declared routing metrics are best;
7. a real OpenAI Agents runtime failure causes bounded heterogeneous failover to CrewAI;
8. durable quarantine of OpenAI Agents overrides its better routing score and makes CrewAI the selected runtime.

The OpenAI Agents sandbox uses first-party `ScriptedModel`; CrewAI uses the existing local deterministic `BaseLLM`; LangGraph uses a deterministic local graph node. No paid model provider is required.

## Certification lifecycle coverage

The three-runtime regression deliberately exercises the Roadmap 5 authority model rather than creating new lifecycle semantics.

Exact binding remains:

```text
orchestrator_id
+ runtime_version
+ probe_execution_id
+ persisted evidence identity/provenance/digest
```

Freshness remains optional but, when configured, an expired latest generation is not reusable.

Revocation remains generation-specific and immutable. Revoking one runtime certificate does not quarantine that runtime and does not invalidate unrelated runtime certificates.

Latest-verdict authority remains implemented in the existing generic certification code. WU05 does not alter it. The dedicated Roadmap 5 latest-verdict unit regression remains part of the full unit-suite gate.

## Routing and failover coverage

The manifest declares intentionally ordered routing metrics:

```text
OpenAI Agents > CrewAI > LangGraph
```

This is test data, not a permanent product ranking.

The selection test proves the existing deterministic scorer works with three heterogeneous runtimes without knowing any framework type.

The failover test intentionally makes the preferred OpenAI Agents mission execution fail after successful certification. The existing bounded failover loop must then exclude the attempted runtime and choose CrewAI on the next attempt.

No framework-specific failover logic is introduced.

## Quarantine authority

The quarantine scenario uses the existing `RuntimeControlStorePort` overlay.

Expected authority order remains:

```text
QUARANTINED / live health
  > deterministic routing metrics
  > historical feedback overlay
```

A quarantined preferred runtime must be absent from routing candidates even when its score is highest.

## CI gate

`.github/workflows/roadmap6-three-runtime-regression.yml`

Prepared gate:

1. install metaO;
2. install exact real runtime pins;
3. verify installed versions;
4. execute WU05 three-runtime regression;
5. execute WU04 real OpenAI Agents conformance regression;
6. execute Roadmap 5 two-runtime lifecycle regression;
7. execute Roadmap 4 real declarative runtime regression;
8. execute the complete unit regression suite, including latest-verdict authority;
9. enforce framework SDK boundaries.

## Core preservation

WU05 adds no production code.

Its branch should differ from WU04 only by:

- the WU05 real integration regression;
- the WU05 workflow;
- this document.

Therefore:

```text
CORE_CHANGED_BY_WU05 = NO
ORCHESTRATOR_CONTRACT_CHANGED_BY_WU05 = NO
RUNTIME_FACTORY_CHANGED_BY_WU05 = NO
```

The only production addition in Roadmap 6 third-runtime work is the WU04 adapter, itself outside Core.

## Execution status

At creation time:

```text
WU05_IMPLEMENTATION = PREPARED
WU05_LOCAL_EXECUTION = BLOCKED_BY_CURRENT_CHAT_NETWORK
WU05_GITHUB_ACTIONS_EXECUTION = PENDING
WU05_TEST_PASS = NOT CLAIMED
WU05_MERGE_GATE = PENDING
```

The first WU04 workflow run again failed before any step was materialized (`steps = null`). That is evidence of the already-known hosted runner blocker, not evidence that WU04 or WU05 functional assertions failed.

## Roadmap 6 completion condition

Roadmap 6 may be called functionally assembled when WU03-WU05 are documented and prepared, but it may not be called validated or merge-ready until executable evidence exists.

The correct future order is:

1. get GitHub-hosted or another trusted execution environment running steps;
2. execute the canonical integration candidate PR #56 first as required by the existing consolidation plan;
3. execute stacked Roadmap 6 WU03/WU04/WU05 gates against their exact heads;
4. fix concrete regressions if any;
5. merge only green work in dependency order or consolidate it into a new canonical candidate;
6. never back-merge historical stacks independently if the canonical candidate already contains them.
