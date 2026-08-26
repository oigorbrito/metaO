# Chassis Evaluation — metaO

Status: RESEARCH / ARCHITECTURE EVALUATION
Date: 2026-08-26
Parent: #178

## Baseline conclusion

metaO already has a real chassis in `main`:

- Python 3.12 package with no mandatory runtime dependencies;
- framework-neutral `OrchestratorContract` Protocol;
- explicit `OrchestratorRegistry`;
- immutable request/result/evidence value objects;
- runtime/framework adapters isolated under `metao/adapters`;
- independent acceptance/governance/control-plane modules already separated from adapters.

Therefore:

```text
CHASSIS_REPLACEMENT = NOT_ASSUMED
CHASSIS_AUDIT_AND_HARDENING = YES
SECOND_CORE = FORBIDDEN
```

## Chassis invariants

A candidate chassis pattern/donor is useful only if it strengthens these properties:

```text
CORE_SMALL_AND_AUDITABLE = TRUE
FRAMEWORK_TYPES_IN_CORE = FALSE
ORCHESTRATOR_REPLACEMENT_REQUIRES_CORE_CHANGE = FALSE
PLUGIN_CAN_DECLARE_CAPABILITIES = TRUE
PLUGIN_FAILURE_DOES_NOT_REWRITE_ACCEPTANCE = TRUE
POLICY_BUDGET_ACCEPTANCE_AUTHORITY_STAYS_METAO = TRUE
DURABILITY_ENGINE_DUPLICATION = FALSE
OBSERVABILITY_IS_NOT_DECISION_AUTHORITY = TRUE
```

## Candidates

### 1. Crossplane — primary generic-control-plane architecture donor

Why it matters:

- explicitly positions itself as a framework for bespoke control planes;
- core avoids features specific to a particular compute plane;
- provider/extension model keeps external-system specifics outside the core;
- API/conformance-oriented extension model;
- strong separation between control-plane curator and consumer concerns.

Current pin observed during sweep:

```text
crossplane/crossplane
0e4f8c1d78ef7a4b1cb2d95d92cafa9a905c2280
```

Classification hypothesis:

```text
ROLE = ARCHITECTURE / TEST DONOR
WHOLE_RUNTIME_ADOPTION = REJECT
KUBERNETES_TYPES_IN_METAO_CORE = FORBIDDEN
```

Most valuable patterns to test:

- core-specificity avoidance;
- provider contract / conformance;
- declarative desired state vs observed state;
- extension packaging and compatibility lifecycle.

### 2. Kubernetes controller-runtime — reconciliation-loop donor

Useful pattern:

```text
Desired state
  -> observe actual state
  -> reconcile
  -> record status
  -> repeat idempotently
```

Potential metaO use:

- runtime health/admission reconciliation;
- certification freshness/revocation reconciliation;
- mission/execution recovery reconciliation;
- avoid event-handler logic that assumes each event is unique.

Classification:

```text
ROLE = RECONCILIATION SEMANTIC / TEST DONOR
WHOLE_DEPENDENCY = REJECT
KUBERNETES_API_DEPENDENCY = REJECT_FOR_CORE
```

### 3. kcp — multi-tenant API/control-plane reference

Current pin observed during sweep:

```text
kcp-dev/kcp
65875a9b81ce961f5b21ddd89c0c04b15b579343
```

Potential value:

- independent isolated workspaces;
- centrally offered APIs consumed by isolated tenants;
- control-plane API separation beyond container workloads.

Classification:

```text
ROLE = REFERENCE_ONLY unless a concrete workspace/API gap is proven
RISK = Kubernetes API machinery and scale far beyond metaO needs
```

### 4. pytest-dev/pluggy — Python-native plugin chassis donor

Why it matters:

- mature Python hook specification/implementation model;
- host defines hooks; plugins implement only declared surfaces;
- supports loose coupling and plugin registry semantics;
- already proven as the plugin core behind pytest and other mature Python systems.

Potential metaO use:

- discover/register runtime adapter providers;
- optional strategy/policy/evidence enrichers where multiple implementations are intended;
- explicit hookspecs instead of ad-hoc imports.

Critical limitation:

```text
PLUGGY = IN_PROCESS_EXTENSION
PLUGGY != SECURITY_ISOLATION
PLUGIN_EXCEPTION_CONTAINMENT != GUARANTEED
```

Therefore no adoption until a concrete plugin multiplicity/discovery need is proven.

Classification:

```text
ROLE = SELECTIVE ADAPT candidate
CURRENT_NEED = NOT_YET_PROVEN
```

### 5. WebAssembly Component Model — future isolated component boundary

Potential value:

- typed host/component interfaces;
- implementation-language neutrality;
- host defines imports/capabilities rather than granting ambient access;
- useful future shape for out-of-process or sandboxed adapters/plugins.

Classification:

```text
ROLE = FUTURE ARCHITECTURE REFERENCE
ADOPTION_NOW = DEFER
```

### 6. smartcomputer-ai/agent-os — minimal-kernel/effects/receipts reference

Current pin:

```text
smartcomputer-ai/agent-os
ec63cb775306f0728a65a4045b6b0457a025af36
```

Useful ideas:

- minimal trusted base;
- explicit effects;
- durable open-work before external side effects;
- signed receipts and replay;
- adapters outside kernel.

Why not use as chassis:

- it already defines its own world/event-log/AIR/workflow/control-plane model;
- adopting it would replace or duplicate metaO's own Mission/Policy/Orchestrator/Evidence/Acceptance model;
- early-development status.

Classification:

```text
ROLE = REFERENCE / TEST DONOR
WHOLE_CHASSIS = REJECT
```

### 7. agent-hooks / Cycles / APC / Edictum

These remain specialized donors, not chassis replacements:

```text
agent-hooks -> runtime control/interception contract
Cycles -> budget protocol/conformance
APC -> delegated-authority semantics
Edictum -> deterministic runtime/evidence gates
```

They should plug into or inform the metaO chassis, not become it.

## Chassis test battery

### C1 — Core purity

Import/scan generic Core and fail if framework/vendor-specific SDK types appear.

Expected:

```text
LANGGRAPH_TYPE_IN_CORE = FALSE
CREWAI_TYPE_IN_CORE = FALSE
OPENAI_AGENT_TYPE_IN_CORE = FALSE
KUBERNETES_TYPE_IN_CORE = FALSE
CROSSPLANE_TYPE_IN_CORE = FALSE
```

### C2 — Whole-orchestrator hot replacement

Run the same mission through two materially different orchestrator adapters.

Expected:

```text
CORE_DIFF_REQUIRED = FALSE
POLICY_DIFF_REQUIRED = FALSE
EVIDENCE_SCHEMA_DIFF_REQUIRED = FALSE
ACCEPTANCE_DIFF_REQUIRED = FALSE
```

### C3 — Adapter registration lifecycle

Register/unregister/re-register adapters without mutating Core definitions or global policy semantics.

### C4 — Adapter contract versioning

Incompatible adapter-contract versions fail admission explicitly; no silent coercion.

### C5 — Failure containment

Adapter exception/crash/timeout cannot produce SUCCESS/ACCEPTED and cannot corrupt another runtime's registry/certification state.

### C6 — Reconciliation idempotency

Repeated health/admission/certification reconciliation converges to the same state and does not duplicate external effects.

### C7 — Desired vs observed state separation

Declared runtime capability/health/config is not accepted as observed fact without independent observation/certification where required.

### C8 — Extension authority boundary

A plugin/hook/provider may return facts/proposals/verdict inputs but cannot directly mint `METAO_ACCEPTED` unless it is the explicitly configured independent acceptance authority under Core rules.

### C9 — Durable boundary

No chassis/plugin mechanism introduces a second durable workflow engine where Conductor already owns durable execution.

### C10 — Optional dependency discipline

Core imports and baseline tests pass with zero optional runtime/framework dependencies installed.

### C11 — Plugin discovery determinism

If dynamic discovery is introduced, duplicate IDs, version conflicts and load-order ambiguity fail deterministically.

### C12 — Out-of-process future seam

The adapter contract can be represented over a process/RPC/component boundary without changing Mission/Execution/Evidence/Acceptance domain objects.

## Provisional recommendation

```text
KEEP_METAO_CHASSIS = YES
REPLACE_WITH_CROSSPLANE = NO
REPLACE_WITH_AGENT_OS = NO
REPLACE_WITH_KCP = NO

ADAPT_FROM_CROSSPLANE = provider/conformance/core-purity patterns
ADAPT_FROM_CONTROLLER_RUNTIME = reconcile/idempotency semantics
EVALUATE_PLUGGY = only if dynamic Python plugin discovery becomes a real requirement
REFERENCE_WASM_COMPONENT_MODEL = future isolation seam
REFERENCE_AGENT_OS = minimal-kernel/effects/receipts tests
```

The preferred direction is a thin metaO-owned Python chassis, hardened by external conformance and architectural patterns rather than replaced by another platform.
