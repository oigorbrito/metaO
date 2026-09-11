# MetaO Operational Pilot Provenance Addendum V1

Status: PREPARED_NOT_EXECUTED
Owner: #360
Parent packet: `docs/PILOT-OPERATIONAL-EXECUTION-PACKET-V1.md`
Related authority slices: #465, #469, #472, #474; parent runtime-health work: #160; scientific matrix: #168/T6-T7.

This addendum is normative for the pilot packet. It closes evidence-shape gaps discovered during static composition review: an `evidence_ref` alone does not prove that an execution-to-runtime binding, runtime-health observation, failure-origin classification, bounded-retry control input, or recovery-probe control input came from the canonical authority.

## Evidence rule

```text
EVIDENCE_REF_PRESENT != PRODUCER_PROVENANCE_PROVED
ENUM_BASIS_VALUE != CRYPTOGRAPHIC_OR_CALLER_IDENTITY_PROOF
CALLER_DECLARATION != FACTUAL_AUTHORITY
CALLER_BOOLEAN != POLICY_OR_EXECUTION_AUTHORITY
CALLER_ATTEMPT_COUNTER != RETRY_HISTORY_AUTHORITY
COMPOSED_GATE_PASS_REQUIRES_CANONICAL_PRODUCER_PATH
ZERO_EXECUTION_FACTS -> UNKNOWN_BASIS_ONLY
ZERO_ATTEMPT_EXECUTION_BOUND_ADMISSION -> REJECT
```

The pure contracts in #465/#469/#472/#474 validate local eligibility/evidence conditions. The composed integration must additionally prove that those inputs are emitted by canonical execution/admission/adapter-normalization/retry-history/policy/risk/budget authorities rather than accepted from arbitrary application input.

Runtime-health provenance has two related but distinct invariants inherited from #462/#465/#474 composition:

- zero execution observations cannot carry `AdapterVerified` or `IndependentObservation` factual execution provenance; empty history is `UNKNOWN` with `Unknown` basis only;
- an empty/zero-attempt `UNKNOWN` projection is bootstrap state only and must not be admitted as an execution-bound factual health observation for an `execution_id`, even when lease and runtime-binding identifiers otherwise match.

Bounded ordinary retry has an additional wiring boundary inherited from #465 and its declared reuse of #140/#141/A11:

- `FailureCausalityFacts.current_attempt` / `max_attempts` are projection inputs, not proof that the authoritative A11 retry-history / canonical retry authority supplied them;
- `policy_blocked`, `risk_blocked`, and `budget_blocked` are pure projection inputs, not proof that canonical policy/risk/budget authorities were consulted;
- factual transient classification requires its own authoritative basis/ref, but that does not authenticate the attempt counters or control booleans;
- actual retry dispatch may occur only when attempt history comes from canonical retry-history authority and policy/risk/budget values come from their canonical authorities; #465 remains eligibility-only.

Recovery-probe authorization has an additional wiring boundary inherited from #469:

- `explicit_probe_intent=true` is a request/input fact, not caller identity or durable authorization;
- `policy_blocked`, `risk_blocked`, and `budget_blocked` are pure projection inputs, not proof that canonical policy/risk/budget authorities were consulted;
- actual probe dispatch may occur only when those values are sourced from canonical authorities and the normal execution/admission path remains authoritative.

## Required machine-readable provenance

In addition to the fields already required by the parent packet, the pilot evidence artifact must contain:

```text
execution_runtime_binding_evidence_basis
execution_runtime_binding_evidence_ref
execution_runtime_binding_producer
execution_runtime_binding_source_execution_id
execution_runtime_binding_source_runtime_id
execution_runtime_binding_source_runtime_version
execution_runtime_binding_source_config_id

runtime_health_observation_evidence_basis
runtime_health_observation_evidence_ref
runtime_health_observation_producer
runtime_health_observation_runtime_id
runtime_health_observation_runtime_version
runtime_health_observation_config_id
runtime_health_observation_attempts
runtime_health_observation_execution_bound_admitted

bounded_retry_current_attempt
bounded_retry_max_attempts
bounded_retry_attempt_history_producer
bounded_retry_attempt_history_ref
bounded_retry_policy_blocked
bounded_retry_policy_producer
bounded_retry_risk_blocked
bounded_retry_risk_producer
bounded_retry_budget_blocked
bounded_retry_budget_producer
bounded_retry_failure_class_basis
bounded_retry_failure_class_evidence_ref
bounded_retry_failure_class_producer
bounded_retry_dispatch_authority_ref

failure_origin_evidence_basis
failure_origin_evidence_ref
failure_origin_producer

recovery_probe_intent
recovery_probe_intent_producer
recovery_probe_policy_blocked
recovery_probe_policy_producer
recovery_probe_risk_blocked
recovery_probe_risk_producer
recovery_probe_budget_blocked
recovery_probe_budget_producer
recovery_probe_execution_authority_ref
```

Producer fields must identify a non-secret canonical component/path, not a user-controlled free-form assertion. Evidence refs may be opaque identifiers, but they must be traceable to the canonical source used by the candidate. Bounded-retry attempt provenance must trace to the authoritative retry-history/canonical retry authority rather than a caller-provided counter. Bounded-retry and recovery-probe control producer fields must identify the canonical policy, risk, budget, request/execution authorities that supplied the values used by the projections.

## Cumulative serial regression rule

Serial promotion is cumulative, not focal-only:

```text
FOCAL_SLICE_PASS != COMPOSITION_PASS
REBASE_RESOLUTION != AUTHORITY_PRESERVED
PRIOR_AUTHORITY_REGRESSIONS_MUST_PASS_ON_NEW_EXACT_SHA
```

After each merge, the next overlapping branch must be rebased/updated onto the resulting `main`, obtain a new exact SHA, and run its focal tests **plus** regressions for every authority already promoted. Automatic `ours`/`theirs` resolution is not qualification evidence.

Required cumulative shape:

```text
#462 merge
 -> updated #465: #462 runtime-health regression subset + retry-pressure/failure-causality/retry-history + canonical bounded-retry control-provenance wiring + workspace
#465 merge
 -> updated #469: all prior regressions + recovery-probe + canonical recovery-probe control-provenance wiring
#469 merge
 -> updated #472: all prior regressions + failure-origin
#472 merge
 -> updated #474: all prior regressions + fencing/execution-lease + explicit zero-attempt execution-bound admission rejection
final main
 -> all cumulative regressions + #462 Python qualification subset + composed producer-wiring T6/T7 scenario
```

The #465 zero-observation provenance rule is part of the cumulative authority surface and must be preserved by #469/#474 rebases. The #474 admission-specific rule is stronger: a valid bootstrap `UNKNOWN` projection with zero attempts remains representable, but it is never admissible as an execution-bound factual observation.

## Composed T6/T7 gate

Before the real pilot, the exact resulting `main` must demonstrate all of the following in one deterministic composed scenario:

1. a factual execution is admitted under current execution authority;
2. the canonical execution/admission path produces the execution -> `(runtime_id, runtime_version, config_id)` binding;
3. the binding carries an allowed factual evidence basis and nonblank evidence ref;
4. the runtime-health observation is produced by the canonical adapter/observation path with an allowed factual basis and nonblank evidence ref;
5. zero execution observations carry `Unknown` basis and cannot claim adapter/independent factual execution provenance;
6. zero-attempt `UNKNOWN` bootstrap health is rejected by execution-bound health-observation admission even when lease/binding identifiers otherwise match;
7. bounded-retry `current_attempt` / `max_attempts` are sourced from canonical retry-history/retry authority and survive restart/failover according to A11 semantics;
8. policy/risk/budget values used by bounded-retry eligibility are sourced from their canonical authorities;
9. a caller that supplies lower attempt counters or false `policy_blocked|risk_blocked|budget_blocked` values cannot bypass canonical retry-history/policy/risk/budget authority or cause retry dispatch;
10. lease `execution_id`, binding `execution_id`, and the observed runtime/version/config agree;
11. stale holder/generation/fence is rejected;
12. recovery-probe intent is sourced from the canonical request/execution-control path rather than an arbitrary caller boolean;
13. policy/risk/budget values used by recovery-probe authorization are sourced from their canonical authorities;
14. a caller that supplies `explicit_probe_intent=true` or false `policy_blocked|risk_blocked|budget_blocked` values cannot bypass those canonical authorities or cause probe dispatch;
15. a caller-constructed binding with copied identifiers but caller/self-reported provenance is rejected or cannot enter the canonical admission path;
16. a caller-constructed health observation with copied identifiers but invalid provenance is rejected or cannot enter the canonical admission path;
17. provider/network failure-origin evidence is not rewritten as runtime-local health evidence;
18. capacity/policy pre-execution conditions do not mint execution failure outcomes;
19. rejection never mutates runtime health, execution outcome, retry dispatch, probe dispatch, or Acceptance authority.

## Pilot P6 extension

Scenario P6 from the parent packet is PASS only if stale-owner rejection, producer provenance, zero-attempt execution-bound admission rejection, bounded-retry authority provenance, and recovery-probe control provenance are demonstrated.

Required P6 evidence:

```text
P6_CURRENT_LEASE_FENCE_MATCH = YES
P6_EXECUTION_RUNTIME_BINDING_MATCH = YES
P6_BINDING_PRODUCER_CANONICAL = YES
P6_HEALTH_OBSERVATION_PRODUCER_CANONICAL = YES
P6_ZERO_ATTEMPT_FACTUAL_PROVENANCE_ACCEPTED = NO
P6_ZERO_ATTEMPT_EXECUTION_BOUND_ADMISSION_ACCEPTED = NO
P6_BOUNDED_RETRY_ATTEMPT_HISTORY_PRODUCER_CANONICAL = YES
P6_BOUNDED_RETRY_POLICY_PRODUCER_CANONICAL = YES
P6_BOUNDED_RETRY_RISK_PRODUCER_CANONICAL = YES
P6_BOUNDED_RETRY_BUDGET_PRODUCER_CANONICAL = YES
P6_CALLER_FORGED_RETRY_CONTROLS_ACCEPTED = NO
P6_RECOVERY_PROBE_INTENT_PRODUCER_CANONICAL = YES
P6_RECOVERY_PROBE_POLICY_PRODUCER_CANONICAL = YES
P6_RECOVERY_PROBE_RISK_PRODUCER_CANONICAL = YES
P6_RECOVERY_PROBE_BUDGET_PRODUCER_CANONICAL = YES
P6_CALLER_FORGED_PROBE_CONTROLS_ACCEPTED = NO
P6_CALLER_FORGED_BINDING_ACCEPTED = NO
P6_CALLER_FORGED_HEALTH_OBSERVATION_ACCEPTED = NO
P6_STALE_OWNER_HEALTH_CONTAMINATION = NO
```

A test that only constructs `RuntimeExecutionHealthBinding { evidence_basis: AdapterVerified, ... }` directly and receives authorization is contract-unit evidence, not composed producer-provenance evidence. Likewise, proving only that zero attempts use `Unknown` basis is insufficient: the composed gate must also prove that this bootstrap projection cannot be admitted as factual execution-bound health evidence. For bounded retry, constructing `FailureCausalityFacts` with favorable attempt counters and false block flags proves projection semantics only; it is not evidence that A11/#140/#141 supplied the authoritative retry decision inputs. For recovery probes, setting `explicit_probe_intent=true` and all block flags to `false` directly in a unit fixture proves projection semantics only; it is not evidence that canonical request/policy/risk/budget authorities authorized a real probe path.

## Abort criteria extension

Abort and preserve evidence if any of these occur:

- execution-runtime binding provenance cannot be traced to the canonical producer;
- runtime-health observation provenance cannot be traced to the canonical producer;
- zero-attempt runtime health carries adapter/independent factual execution provenance;
- zero-attempt bootstrap `UNKNOWN` is admitted as execution-bound factual health evidence;
- bounded-retry attempt counters cannot be traced to canonical retry-history/retry authority;
- bounded-retry policy/risk/budget values cannot be traced to canonical authorities;
- caller-controlled retry counters or booleans can authorize/dispatch a retry without crossing A11/#140/#141 authority;
- recovery-probe intent or policy/risk/budget control values cannot be traced to canonical authorities;
- caller-controlled booleans can authorize or dispatch a recovery probe without crossing canonical request/policy/risk/budget/execution authorities;
- caller-controlled input can mint an allowed factual evidence basis without crossing canonical authority;
- evidence basis/ref values disagree with the recorded producer path;
- copied identifiers are sufficient to bypass producer provenance;
- failure-origin classification is accepted from untrusted caller data as authoritative factual evidence.

Classify before changing implementation:

```text
PRODUCT_REGRESSION
TEST_HARNESS_REGRESSION
PROVENANCE_WIRING_GAP
DEPENDENCY_RUNTIME_MISMATCH
ENVIRONMENT_RESOURCE_BLOCKER
EXTERNAL_INFRASTRUCTURE
```

## Qualification boundary

This addendum is documentation/design evidence only.

```text
ADDENDUM = PREPARED
CUMULATIVE_SERIAL_REGRESSION_MATRIX = PREPARED
BOUNDED_RETRY_CONTROL_PROVENANCE_RULE = PREPARED
RECOVERY_PROBE_CONTROL_PROVENANCE_RULE = PREPARED
ZERO_ATTEMPT_EXECUTION_BOUND_ADMISSION_RULE = PREPARED
COMPOSED_PRODUCER_WIRING_GATE = NOT_RUN
PILOT = NOT EXECUTED
FUNCTIONAL_PASS = NO
MERGE_READY = NO
```

No evidence from #462/#465/#469/#472/#474 transfers across SHAs. Serial promotion and exact-head requalification rules from the parent packet remain unchanged.
