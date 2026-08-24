# Roadmap 2 WU01 — Second Real Runtime Sandbox V1

## Objective

Prove the central metaO architectural claim with two different real orchestrator runtimes behind the existing `OrchestratorContract`, while keeping the metaO Core unchanged.

Real runtimes pinned for reproducible evidence:

- LangGraph `1.2.11`
- CrewAI `1.15.16`

CrewAI uses a deterministic custom `BaseLLM` only inside the integration sandbox. This exercises the real CrewAI `Agent` / `Task` / `Crew.kickoff()` runtime without requiring a paid model API or leaking an SDK dependency into metaO Core.

## Architectural gate

```text
REAL_RUNTIME_COUNT >= 2
AND
CORE_CHANGED_FOR_SECOND_RUNTIME = NO
```

The Roadmap 2 CI gate compares the PR against `origin/main` and fails if any file under `src/metao` outside `src/metao/adapters/` changes.

If CrewAI requires a Core-specific path, this work unit must stop and the abstraction must be reviewed instead of adding framework conditionals to Core.

## Required evidence

The integration suite proves:

1. real CrewAI executes through `OrchestratorContract`;
2. CrewAI output becomes a normalized `EvidenceEnvelope`;
3. the same Mission can execute on real LangGraph or real CrewAI;
4. strategy selection can choose between both real runtimes;
5. LangGraph failure can fail over to CrewAI;
6. CrewAI failure can fail over to LangGraph;
7. Policy gates both runtimes before execution;
8. Budget gates both runtimes before execution;
9. independent acceptance can reject successful output from either runtime;
10. observability event shape is runtime-neutral;
11. attempt telemetry shape is runtime-neutral;
12. CrewAI in-flight cancellation remains fail-closed if the runtime completes late;
13. complete runtime swap uses the same Core contract.

## Cancellation semantics

The CrewAI adapter exposes the same cooperative cancellation boundary as the contract. CrewAI `kickoff()` is synchronous and does not provide metaO with a guaranteed hard interrupt for an already-running execution.

Therefore the required invariant remains:

```text
cancel_requested + CrewAI late success != METAO_ACCEPTED
```

The integration test intentionally blocks a real CrewAI execution, requests mission cancellation through `MissionOperator`, lets CrewAI finish, and requires the final metaO mission to be `BLOCKED` with `cancel_requested_runtime_completed`.

No adapter may claim hard cancellation that the underlying runtime did not actually perform.

## CI evidence path

Workflow:

```text
.github/workflows/roadmap2-second-runtime-sandbox.yml
```

It runs, in order:

1. pinned LangGraph/CrewAI installation and version verification;
2. Core-freeze diff gate;
3. the 13 Roadmap 2 WU01 integration tests;
4. the complete Roadmap 1 unit/architecture suite;
5. Block O O1–O5 sandbox regression.

A PASS is valid only when the GitHub Actions run is green.
