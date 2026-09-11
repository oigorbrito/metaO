# MetaO Operational Pilot Provenance Addendum V1

Status: PREPARED_NOT_EXECUTED
Owner: #360
Parent packet: `docs/PILOT-OPERATIONAL-EXECUTION-PACKET-V1.md`
Related authority slices: #472, #474; parent runtime-health work: #160; scientific matrix: #168/T6-T7.

This addendum is normative for the pilot packet. It closes an evidence-shape gap discovered during static composition review: an `evidence_ref` alone does not prove that an execution-to-runtime binding or runtime-health observation came from the canonical factual producer.

## Evidence rule

```text
EVIDENCE_REF_PRESENT != PRODUCER_PROVENANCE_PROVED
ENUM_BASIS_VALUE != CRYPTOGRAPHIC_OR_CALLER_IDENTITY_PROOF
CALLER_DECLARATION != FACTUAL_AUTHORITY
COMPOSED_GATE_PASS_REQUIRES_CANONICAL_PRODUCER_PATH
```

The pure contracts in #472/#474 validate allowed evidence classifications and fail closed on missing/blank references. The composed integration must additionally prove that those classifications are emitted by the canonical execution/admission/adapter-normalization path rather than accepted from arbitrary application input.

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

failure_origin_evidence_basis
failure_origin_evidence_ref
failure_origin_producer
```

Producer fields must identify a non-secret canonical component/path, not a user-controlled free-form assertion. Evidence refs may be opaque identifiers, but they must be traceable to the canonical source used by the candidate.

## Composed T6/T7 gate

Before the real pilot, the exact resulting `main` must demonstrate all of the following in one deterministic composed scenario:

1. a factual execution is admitted under current execution authority;
2. the canonical execution/admission path produces the execution -> `(runtime_id, runtime_version, config_id)` binding;
3. the binding carries an allowed factual evidence basis and nonblank evidence ref;
4. the runtime-health observation is produced by the canonical adapter/observation path with an allowed factual basis and nonblank evidence ref;
5. lease `execution_id`, binding `execution_id`, and the observed runtime/version/config agree;
6. stale holder/generation/fence is rejected;
7. a caller-constructed binding with copied identifiers but caller/self-reported provenance is rejected or cannot enter the canonical admission path;
8. a caller-constructed health observation with copied identifiers but invalid provenance is rejected or cannot enter the canonical admission path;
9. provider/network failure-origin evidence is not rewritten as runtime-local health evidence;
10. capacity/policy pre-execution conditions do not mint execution failure outcomes;
11. rejection never mutates runtime health, execution outcome, retry dispatch, or Acceptance authority.

## Pilot P6 extension

Scenario P6 from the parent packet is PASS only if stale-owner rejection and producer provenance are both demonstrated.

Required P6 evidence:

```text
P6_CURRENT_LEASE_FENCE_MATCH = YES
P6_EXECUTION_RUNTIME_BINDING_MATCH = YES
P6_BINDING_PRODUCER_CANONICAL = YES
P6_HEALTH_OBSERVATION_PRODUCER_CANONICAL = YES
P6_CALLER_FORGED_BINDING_ACCEPTED = NO
P6_CALLER_FORGED_HEALTH_OBSERVATION_ACCEPTED = NO
P6_STALE_OWNER_HEALTH_CONTAMINATION = NO
```

A test that only constructs `RuntimeExecutionHealthBinding { evidence_basis: AdapterVerified, ... }` directly and receives authorization is contract-unit evidence, not composed producer-provenance evidence.

## Abort criteria extension

Abort and preserve evidence if any of these occur:

- execution-runtime binding provenance cannot be traced to the canonical producer;
- runtime-health observation provenance cannot be traced to the canonical producer;
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
COMPOSED_PRODUCER_WIRING_GATE = NOT_RUN
PILOT = NOT_EXECUTED
FUNCTIONAL_PASS = NO
MERGE_READY = NO
```

No evidence from #462/#465/#469/#472/#474 transfers across SHAs. Serial promotion and exact-head requalification rules from the parent packet remain unchanged.
