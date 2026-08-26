# Donor Sweep 2 — 2026-08-26

Status: RESEARCH SNAPSHOT / NO ADOPTION AUTHORITY

Parent: #178
Related: #181, #182, #186, #187, #188

## Purpose

Record the second search sweep for projects and research that may fit metaO more closely than the initial donor set.

Rules remain:

```text
NEW_PROJECT != BETTER_DONOR
PAPER_RESULT != METAO_RESULT
CONFORMANCE != SECURITY_CERTIFICATION
RUNTIME_POLICY != INDEPENDENT_ACCEPTANCE
GATEWAY != CORE
```

## Strongest new findings

### 1. responsibleai/agent-hooks

Pin:

```text
0821ebbae252c45cd225304a464d1130963b82a8
```

Why it is unusually relevant:

- explicitly framework-neutral control contract;
- normative RFC-2119 specification;
- fixed lifecycle interception points;
- normalized context and verdict contract;
- machine-readable schemas;
- multi-language conformance vectors and harness;
- explicitly separates control from telemetry;
- explicitly states conformance is not security certification.

Provisional fit:

```text
ROLE = STRONG ADAPT / TEST_DONOR
TAKE = lifecycle interception semantics + conformance vector patterns
DO_NOT_TAKE = assumption that cooperative host mediation is a security boundary
```

Owner: #188.

### 2. xmuruaga/bounded-agents / Agentic Principal Chain (APC)

Pin:

```text
d31a1ea115a3e97ab972ac8d03f23ef36cf9b653
```

Paper: arXiv:2608.15888

Key relevance:

- delegated authority attenuates monotonically;
- authorization is stateful across session history;
- individually permitted actions may be rejected when their composition is forbidden;
- six deterministic conjunctive checks operate outside the model;
- evaluation artifact covers 3,154 instances including AgentDojo compromised-model suites.

Provisional fit:

```text
ROLE = STRONG SEMANTIC / TEST DONOR
TAKE = delegation attenuation + composition-aware authorization invariants
DO_NOT_TAKE = claim that APC alone solves metaO governance or acceptance
```

Owner: #187.

### 3. runcycles/cycles-protocol

Pin:

```text
9899d0474ecb50247e3fa46d23a7f1b825048122
```

Current conformance target recorded by donor: v0.1.25.

Relevant semantics:

- protocol-first budget/action authority;
- RFC-2119 MUST/SHOULD/MAY conformance;
- atomic multi-scope reservations;
- concurrency-safe budget enforcement;
- idempotent commit/release;
- explicit recovery-conformance profile;
- deterministic error semantics;
- tracing and event invariants.

Provisional fit:

```text
ROLE = ADAPT / TEST_DONOR
TAKE = reservation/settlement/concurrency/recovery test semantics
DO_NOT_TAKE = donor admin API as metaO Core contract
```

Owner: #187.

### 4. edictum-ai/edictum

Pin:

```text
8ef51664fc8dbc136044771ee2c9ec67ca4ba04e
```

Relevant properties:

- deterministic runtime enforcement;
- fail-closed policy failures;
- framework adapters;
- workflow stages requiring evidence and approvals;
- principal-aware enforcement;
- clear measurement boundary: behavioral runtime conformance != output correctness.

Related research: arXiv:2602.16943 (GAP benchmark), which reports that text-level refusal/safety does not reliably imply safe tool-call behavior.

Provisional fit:

```text
ROLE = ADAPT / TEST_DONOR
TAKE = evidence-aware runtime gate fixtures + text/action divergence tests
FINAL_ACCEPTANCE_AUTHORITY = NO
```

Owner: #188.

### 5. preloop/preloop

Pin:

```text
765a4f835e4e5706af913cfef56bc738432d78ae
```

Relevant operational capabilities:

- MCP firewall;
- policy-as-code;
- async human approvals;
- model gateway;
- budget/accounting;
- runtime session audit/observability;
- secret custody.

Provisional fit:

```text
ROLE = ENFORCEMENT / GATEWAY REFERENCE
CORE_DONOR = NO
```

Owner: #187/#186.

### 6. clearideas/agent-runtime

Pin:

```text
c8a4856863405c817315bbd8ff89a07fea6b24a5
```

Relevant properties:

- portable versioned manifests;
- explicit contract packages;
- host-controlled models/credentials/tools/persistence/compute/sandboxes/telemetry;
- durable checkpoints/resume/cancellation;
- provider-neutral adapters;
- explicit boundary checks in contributor validation.

Important limitation:

```text
PORTABLE_AGENT_RUNTIME != WHOLE_THIRD_PARTY_ORCHESTRATOR_REPLACEMENT
```

It is a useful contract/boundary reference, but it is itself an agent runtime rather than proof that metaO can swap arbitrary orchestrators.

Provisional fit:

```text
ROLE = REFERENCE / SELECTIVE TEST DONOR
```

Owner: #182.

## Existing donor strengthened, not duplicated

### Agentspan -> Conductor

Agentspan has merged into Conductor. The donor migration documentation states that its durable agent runtime now ships inside Conductor and its SDK support includes framework bridges such as LangGraph, OpenAI Agents, Google ADK and Anthropic/Claude.

Decision:

```text
NEW_AGENTSPAN_DONOR = NO
CONDUCTOR_EVIDENCE_STRENGTHENED = YES
```

This should feed the existing Conductor/durability work rather than create a parallel execution foundation.

## Gateway/protocol references

### agentgateway/agentgateway

Useful as transport/enforcement reference for MCP/A2A/LLM routing, security, observability, spend controls and failover.

```text
ROLE = ENFORCEMENT/TRANSPORT REFERENCE
METAO_CORE = NO
```

### ygmrs/a2a-governance-gateway

Compact fixture containing identity, capability scoping, policy, budget, human approval and tamper-evident audit across A2A calls.

Its own documentation identifies simplified/in-memory storage and production hardening gaps.

```text
ROLE = TEST DONOR / REFERENCE_ONLY
```

### sunilp/aip / AIP

Paper: arXiv:2603.24775.

Potential value:

- invocation-bound capability tokens;
- cryptographic delegation chains;
- capability attenuation;
- MCP/A2A transport bindings;
- provenance-oriented completion records.

Must be compared with existing SPIFFE/SPIRE identity work before any adoption.

## Research/reference architecture additions

### arXiv:2606.12320 — Five-Plane Runtime Governance

Proposes:

- one stateful reasoning/adjudication plane;
- separate network/identity/endpoint/data enforcement planes;
- stop-anywhere mediation;
- composite principals and capability attenuation;
- structured audit evidence.

The paper is a preprint and explicitly leaves live full-system benchmark evaluation as future work.

Potential metaO test implication:

```text
DECISION_AUTHORITY != ENFORCEMENT_PLANE
ENFORCEMENT_FAILURE -> FAIL_CLOSED
```

### arXiv:2605.05440 — Authorization Propagation

Useful taxonomy:

- transitive delegation;
- aggregation inference;
- temporal validity.

Potential metaO test implication:

```text
AUTHORIZATION_IS_WORKFLOW_STATEFUL
AUTHORITY_MUST_NOT_EXPAND_ACROSS_DELEGATION
STALE_AUTHORITY != VALID_AUTHORITY
```

### arXiv:2606.03518 — Overlaying Governance

Potential donor for formal scope/delegation composition and attenuation semantics.

### arXiv:2608.03214 — Agent Operating System reference architecture

Vendor-neutral two-plane conceptual architecture:

- Control & Governance Plane;
- Runtime & Coordination Plane.

Useful as architectural comparison only. It is not evidence that metaO implementation is correct.

## Updated provisional ranking

| Need | Strongest candidate after sweep 2 | Provisional role |
|---|---|---|
| Discovery clarification | GitHub Spec Kit | ADAPT/COMPOSE semantics |
| Spec evolution | OpenSpec | ADAPT semantics |
| Framework-neutral control hooks | agent-hooks | STRONG ADAPT/TEST DONOR |
| Runtime governance adapters | Microsoft Agent Governance Toolkit | COMPOSE/ADAPT |
| Evidence-aware tool/workflow gates | Edictum | ADAPT/TEST DONOR |
| Budget reservation/concurrency | Cycles Protocol | ADAPT/TEST DONOR |
| Delegation attenuation/composition | Bounded Agents/APC | STRONG TEST/SEMANTIC DONOR |
| Operational MCP/model gateway | Preloop / agentgateway | ENFORCEMENT REFERENCE |
| Durable execution | Conductor (Agentspan now merged) | existing foundation strengthened |
| Portable agent runtime contracts | clearideas/agent-runtime | REFERENCE/TEST DONOR |
| Requirement clarification measurement | ClarifyCodeBench | TEST DONOR |
| Repository-level clarification/planning | SWE-RPG | TEST DONOR |
| Adversarial tool-use | AgentDojo + GAP/APC deltas | TEST DONOR |

## New required tests from this sweep

### P1 — Atomic budget reservation

Concurrent work units sharing one budget cannot oversubscribe it.

### P2 — Idempotent settlement

Retrying settlement/release cannot double-charge or double-release.

### A1 — Delegation monotonicity

A child runtime/sub-agent cannot receive broader authority or budget than its delegated parent scope.

### A2 — Composition-aware authorization

Two individually allowed actions whose combination violates policy must be rejectable from session/workflow history.

### A3 — Temporal validity

Expired/revoked policy/identity/delegation facts cannot remain valid via stale cache or resumed execution.

### H1 — Framework control conformance

Equivalent framework adapters must emit normalized lifecycle facts and obey deny/transform/fail-closed obligations.

### H2 — Missing mediation point

If a host framework cannot mediate a required side-effect point, it cannot claim full metaO runtime eligibility for that mission.

### T1 — Text/action divergence

A runtime response that verbally refuses an unsafe action while attempting the forbidden tool call must fail the action-governance test.

```text
SAFE_TEXT + FORBIDDEN_ACTION_ATTEMPT != SAFE_EXECUTION
```

### E1 — Enforcement plane failure

A transport/gateway/enforcement failure during a mandatory directive must not silently become allow/success.

## Current conclusion

```text
SEARCH_SWEEP_2 = COMPLETE
NEW_HIGH_VALUE_DONORS = YES
BEST_NEW_CONTRACT_DONOR = responsibleai/agent-hooks
BEST_NEW_DELEGATION_TEST_DONOR = Bounded Agents/APC
BEST_NEW_BUDGET_PROTOCOL_DONOR = Cycles Protocol
BEST_NEW_EVIDENCE_GATE_DONOR = Edictum
CONDUCTOR_FOUNDATION_STRENGTHENED = YES
WHOLE_DONOR_ADOPTION_AUTHORIZED = NO
```

Next evaluation should inspect exact relevant paths and execute L1/L2 fit tests under #187 and #188 before any production-code integration.
