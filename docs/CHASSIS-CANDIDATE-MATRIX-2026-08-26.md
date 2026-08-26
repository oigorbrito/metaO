# Chassis Candidate Matrix — 2026-08-26

This file is a compact decision table for #189.

| Candidate | Chassis fit | Reuse mode | Main value | Main rejection risk |
|---|---|---|---|---|
| Existing metaO Python Core | VERY HIGH | KEEP/HARDEN | already framework-neutral, dependency-light, explicit OrchestratorContract | insufficient future plugin/process isolation if left static |
| Crossplane | HIGH semantic / LOW literal | ADAPT/REFERENCE | generic control-plane core vs providers, conformance, composition | Kubernetes/Go control plane becomes second platform |
| controller-runtime | HIGH semantic / LOW literal | ADAPT/TEST | reconcile desired vs observed state, idempotent convergence | Kubernetes coupling |
| kcp | MEDIUM | REFERENCE | isolated workspaces, central API providers | excessive Kubernetes/API-machinery scope |
| pytest-dev/pluggy | MEDIUM-HIGH if plugin discovery needed | SELECTIVE ADAPT | Python-native hookspec/plugin registry | in-process plugin failure/security; load-order semantics |
| WebAssembly Component Model | HIGH future seam | DEFER/REFERENCE | typed language-neutral component boundary | premature complexity |
| smartcomputer-ai/agent-os | MEDIUM semantic / LOW literal | REFERENCE/TEST | minimal kernel, effects, receipts, replay | duplicates metaO world/workflow/control plane |
| agent-hooks | HIGH boundary fit, not full chassis | ADAPT/TEST | framework-neutral control hooks + CTK | host-trust model; not security boundary |
| Cycles Protocol | HIGH budget subsystem fit | ADAPT/TEST | atomic/idempotent budget protocol | wire model leaking into generic Core |
| APC / Bounded Agents | HIGH authority subsystem fit | ADAPT/TEST | delegated authority attenuation + composition checks | research artifact becomes policy authority |
| Edictum | HIGH runtime-gate fit | ADAPT/TEST | deterministic workflow/evidence gates | duplicates metaO policy/acceptance authority |

## Current decision

```text
CHASSIS_WINNER = EXISTING_METAO_CORE
CHASSIS_REPLACEMENT_SEARCH = NO_WINNER_FOUND
CHASSIS_HARDENING_DONORS = CROSSPLANE + CONTROLLER_RUNTIME + AGENT_HOOKS
PYTHON_PLUGIN_DONOR = PLUGGY (conditional)
FUTURE_ISOLATION_DONOR = WASM_COMPONENT_MODEL
```

This is provisional until #189 executes C1–C12 against the current metaO implementation.