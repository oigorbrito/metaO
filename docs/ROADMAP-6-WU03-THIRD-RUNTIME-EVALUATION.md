# Roadmap 6 WU03 — Third Runtime Evaluation / Selection

Date: 2026-08-24

Status: DECISION DOCUMENTED / IMPLEMENTATION NOT PART OF THIS WU / EXECUTION NOT CLAIMED

## Goal

Select a third real orchestrator/runtime for metaO without changing the Core or the existing `OrchestratorContract`.

The decision optimizes for:

1. architectural diversity;
2. a thin adapter boundary;
3. deterministic zero-provider-cost conformance testing;
4. zero Core changes;
5. active upstream maintenance;
6. low operational and maintenance cost.

The candidates audited are:

- OpenAI Agents SDK — `openai/openai-agents-python`
- Microsoft Agent Framework — `microsoft/agent-framework`
- Google Agent Development Kit — `google/adk-python`

## Evidence classification

- **DOCUMENTED** — directly supported by current upstream documentation, package metadata, or repository source.
- **EXECUTED** — observed by executing the candidate in the metaO evaluation environment.
- **INFERRED** — engineering conclusion derived from documented public API shape and the current metaO contract.

No candidate was executed in this WU because the current chat execution environment cannot resolve `github.com`, and GitHub-hosted Actions are already tracked as an external execution blocker. Therefore this WU makes no runtime PASS claim.

## Current upstream snapshot

| Candidate | Current package observed | License | Python | Upstream status | Evidence |
| --- | --- | --- | --- | --- | --- |
| OpenAI Agents SDK | `openai-agents==0.21.1` — 2026-08-16 | MIT | >=3.10 | active, non-archived | DOCUMENTED |
| Microsoft Agent Framework | `agent-framework==1.14.0` — 2026-08-14 | MIT | >=3.10 | active, non-archived; production/stable | DOCUMENTED |
| Google ADK Python | `google-adk==2.7.1` — 2026-08-17 | Apache-2.0 | >=3.10 | active, non-archived | DOCUMENTED |

Sources:

- https://pypi.org/project/openai-agents/0.21.1/
- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/running_agents/
- https://openai.github.io/openai-agents-python/models/
- https://openai.github.io/openai-agents-python/testing/
- https://github.com/openai/openai-agents-python/blob/v0.21.1/src/agents/testing/model.py
- https://pypi.org/project/agent-framework/1.14.0/
- https://learn.microsoft.com/en-us/agent-framework/workflows/
- https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/run-agent
- https://github.com/microsoft/agent-framework/blob/main/python/samples/02-agents/chat_client/custom_chat_client.py
- https://pypi.org/project/google-adk/2.7.1/
- https://github.com/google/adk-python/blob/main/src/google/adk/models/base_llm.py

## Technical matrix

| Criterion | OpenAI Agents SDK | Microsoft Agent Framework | Google ADK Python |
| --- | --- | --- | --- |
| Primary execution API | `Runner.run`, `Runner.run_sync`, `Runner.run_streamed` | Python `await agent.run(...)`; workflow APIs are async | Runner/event-oriented async execution | 
| Sync fit with current metaO contract | **Strong** — `Runner.run_sync` maps directly to synchronous `execute()` | Medium — adapter must bridge async into synchronous metaO Core boundary | Medium — adapter must consume async/event APIs inside sync boundary |
| Deterministic local model seam | **Strong** — provider-neutral `Model`; first-party `agents.testing.ScriptedModel` | **Strong** — custom `BaseChatClient`; upstream echo client sample | **Strong** — subclassable `BaseLlm.generate_content_async()` |
| Paid provider required for conformance | No | No | No |
| Agent/workflow support | agents, tools, handoffs, guardrails, sessions, HITL | agents plus graph/functional workflows and multi-agent patterns | agents, workflow agents, sessions and state |
| Session/memory | first-party sessions | agent sessions/history providers | session service/state architecture |
| Observability | built-in tracing; replaceable processors | telemetry / instrumentation and workflow events | telemetry/plugins; broader Google Cloud integrations available |
| Error semantics | typed SDK exceptions including max turns/model/tool timeout/guardrail failures | typed Python framework errors plus response/workflow results | Python exceptions/events around runner/model/session layers |
| Cancellation | explicit cancellation on streamed result (`immediate` / `after_turn`); metaO can preserve current pre-cancel semantics for sync adapter | async response/task patterns; background continuation exists for supported agents | runner/live/event model gives cancellation possibilities but adapter bridge is less direct |
| Evidence normalization | simple: final output + usage/run metadata exposed on result | simple to moderate: response objects and workflow events | moderate: event stream must be reduced to one metaO result |
| Thin adapter potential | **Very high** — duck-type `Runner.run_sync` + `result.final_output` | high, but async bridge becomes adapter-owned runtime machinery | high, but event/async reduction increases adapter surface |
| SDK leakage risk into Core | **Low** if runner/agent are injected behind `Any`/duck typing | low if all async/client types stay inside adapter/plugin | low if `BaseLlm`/Runner types stay inside adapter/plugin |
| Dependency / operational weight | moderate, OS-independent wheel; optional integrations are extras | moderate; umbrella package composes core/provider packages | higher surface and stronger surrounding Google ecosystem integrations |
| Windows/Linux viability | OS-independent package metadata | pure Python/core packages, Python 3.10+ | OS-independent package metadata, Python 3.10+ |
| Conformance probe difficulty | **Low** using first-party `ScriptedModel` | low using custom `BaseChatClient` | low-medium using custom `BaseLlm` plus runner event collection |
| Health probe shape | verify runner callable + configured agent | verify agent/client callable shape | verify runner/agent/model callable shape |
| Lock-in risk | medium: vendor SDK, but custom/non-OpenAI `Model` supported | medium: broad Microsoft ecosystem but multi-provider | medium: broad Google ecosystem, custom model seam exists |
| Overlap with LangGraph | low-medium | medium-high because graph workflows overlap LangGraph | medium |
| Overlap with CrewAI | medium | medium because agent/multi-agent layer overlaps CrewAI | medium |
| Architectural diversity value | **High** — runner/handoff/guardrail-oriented runtime distinct from graph and crew abstractions | high — workflow + enterprise agent substrate, but overlaps both existing shapes | high — runner/session/event architecture |
| Maintenance signal | very active; latest package within 8 days of evaluation | very active; stable 1.x and latest within 10 days | very active; latest within 7 days |

Unless otherwise stated, rows above are DOCUMENTED or INFERRED. None is EXECUTED in metaO by this WU.

## Scored decision

Scoring: 1 (weak) to 5 (strong).

| Weighted criterion | Weight | OpenAI | Microsoft | Google |
| --- | ---: | ---: | ---: | ---: |
| Architectural diversity | 25 | 4.5 | 4.5 | 4.5 |
| Thin adapter / current sync contract fit | 20 | **5.0** | 3.5 | 3.5 |
| Deterministic zero-cost testing | 20 | **5.0** | 5.0 | 4.5 |
| Zero Core change | 15 | **5.0** | 4.5 | 4.5 |
| Upstream maintenance / maturity | 10 | 4.5 | **5.0** | 4.5 |
| Operational / maintenance cost | 10 | **4.5** | 4.0 | 3.5 |
| **Weighted result / 100** | 100 | **95.0** | **87.5** | **84.5** |

These scores are INFERRED engineering judgments grounded in the documented API surfaces above; they are not runtime benchmark results.

## Decision

**SELECTED THIRD RUNTIME: OpenAI Agents SDK 0.21.1.**

The decisive factor is not brand or feature count. It is boundary fit.

metaO currently exposes synchronous:

```text
health()
execute(request) -> ExecutionResult
cancel(execution_id)
```

OpenAI Agents provides a first-party synchronous `Runner.run_sync(...)` path. That allows the third adapter to remain the same kind of thin translation layer already used for LangGraph (`invoke`) and CrewAI (`kickoff`) instead of adding an event-loop bridge or workflow-event reducer to satisfy the current Core contract.

The SDK also ships provider-neutral deterministic testing utilities under `agents.testing`, including `ScriptedModel`, specifically documented to run in memory without model API requests. That gives metaO a real SDK conformance sandbox with no paid provider and no fake PASS.

## Boundary decision

The implementation MUST preserve:

```text
metaO Core
  -> OrchestratorContract
  -> OpenAIAgentsOrchestratorAdapter   # SDK-neutral duck typing
  -> agents.Runner / Agent             # SDK confined to plugin/test composition
```

The production adapter MUST NOT import `agents`, OpenAI response types, or any provider SDK type.

The real sandbox/plugin composition MAY import `agents` because adapters/plugins are the allowed framework boundary.

## Planned conformance mapping

| metaO contract surface | OpenAI Agents mapping |
| --- | --- |
| descriptor | adapter-owned immutable metaO descriptor |
| health | injected runner exposes callable `run_sync`; agent is configured |
| execute | `Runner.run_sync(agent, normalized_input)`; normalize `final_output` into metaO output |
| cancel | preserve metaO pre-dispatch cancellation immediately; streamed SDK cancellation remains a future adapter capability, not a Core change |
| evidence | hash normalized output and bind provenance to runtime + execution id |

## Explicit non-goals

- no `agents` imports in metaO Core;
- no change to `OrchestratorContract`;
- no Responses API key requirement;
- no learned routing;
- no provider-specific policy in Core;
- no Kubernetes/cloud hosting work;
- no merge of PR #56;
- no PASS claim until real execution exists.

## Next work unit

Roadmap 6 WU04 should:

1. add `src/metao/adapters/openai_agents.py` using duck typing only;
2. add SDK-free adapter unit tests;
3. add a real `openai-agents==0.21.1` deterministic sandbox using `agents.testing.ScriptedModel`;
4. run the existing Runtime Conformance Harness against the adapter;
5. prove cancellation-before-dispatch, execution success/failure normalization, and evidence normalization;
6. add a dedicated CI workflow that installs only the needed third-runtime dependency plus metaO;
7. keep the PR draft until executable evidence exists.
