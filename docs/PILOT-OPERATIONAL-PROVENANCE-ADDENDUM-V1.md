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
FOCAL_SLICE_PASS != COMPOSITION_PASS
REBASE_RESOLUTION != AUTHORITY_PRESERVED
PRIOR_AUTHORITY_REGRESSIONS_MUST_PASS_ON_NEW_EXACT_SHA
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

## Cumulative serial regression preservation

The promotion sequence is cumulative. A slice-level PASS after rebase is insufficient if regressions for authorities already promoted into the new base were not also executed on the new exact SHA.

The reason is structural: #465, #469, and #474 all extend the canonical `runtime_health.rs` authority surface, while #472 extends `failure_causality.rs`, which is consumed by #465. A mechanically successful rebase or conflict resolution can silently discard or weaken an earlier authority even when the new slice's focal test still passes.

Conflict resolution must preserve the canonical shared surface and all already-promoted authorities. In particular, the resulting composition must retain:

```text
RuntimeHealthObservation
RuntimeHealthPolicy
derive_runtime_health(...)
#465 evaluate_bounded_retry(...)
#469 evaluate_recovery_probe_authorization(...)
#474 RuntimeExecutionHealthBinding + observation fencing
#472 FailureOrigin attribution + existing retry-causality API consumed by #465
```

Automatic `ours` / `theirs` conflict resolution is not qualification evidence.

Required cumulative gates after each serial promotion are:

### After #462 merge -> updated #465

The new #465 exact head must preserve the merged Python runtime-health authority and execute its Rust focal/cumulative regressions:

```text
#462 Python runtime-health qualification subset remains green on the integration base
retry_pressure_tests
runtime_health_tests
failure_causality_tests
metao-kernel retry_history
full locked Rust workspace
clean worktree before/after
```

### After #465 merge -> updated #469

The new #469 exact head must execute the already-promoted retry/runtime-health regressions plus its recovery focal regression:

```text
retry_pressure_tests
recovery_probe_tests
runtime_health_tests
failure_causality_tests
metao-kernel retry_history
full locked Rust workspace
clean worktree before/after
```

The merged #462 Python runtime-health qualification subset must also remain green on the resulting integration base.

### After #469 merge -> updated #472

The new #472 exact head must execute all previously promoted runtime-health/retry/recovery regressions plus failure-origin regressions:

```text
retry_pressure_tests
recovery_probe_tests
runtime_health_tests
failure_origin_tests
failure_causality_tests
metao-kernel retry_history
full locked Rust workspace
clean worktree before/after
```

The merged #462 Python runtime-health qualification subset must remain green.

### After #472 merge -> updated #474

The new #474 exact head must execute all previously promoted runtime-health/retry/recovery/failure-origin regressions plus fencing regressions:

```text
retry_pressure_tests
recovery_probe_tests
runtime_health_tests
failure_origin_tests
failure_causality_tests
runtime_health_fencing_tests
execution_lease_tests
metao-kernel retry_history
full locked Rust workspace
clean worktree before/after
```

The merged #462 Python runtime-health qualification subset must remain green.

### Final resulting `main`

Before T6/T7 can be called closed, the exact resulting `main` must execute:

```text
#462 Python runtime-health qualification subset
all cumulative Rust regressions above
full locked Rust workspace
one deterministic composed producer-wiring T6/T7 scenario
clean worktree before/after
```

Any new SHA invalidates prior qualification evidence for that branch. Passing only the focal test for the current slice is insufficient for promotion.

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
- failure-origin classification is accepted from untrusted caller data as authoritative factual evidence;
- a rebase drops an already-promoted authority or its regression coverage;
- a focal slice passes while a prior-authority regression fails on the same exact SHA.

Classify before changing implementation:

```text
PRODUCT_REGRESSION
TEST_HARNESS_REGRESSION
PROVENANCE_WIRING_GAP
SERIAL_COMPOSITION_REGRESSION
DEPENDENCY_RUNTIME_MISMATCH
ENVIRONMENT_RESOURCE_BLOCKER
EXTERNAL_INFRASTRUCTURE
```

## Qualification boundary

This addendum is documentation/design evidence only.

```text
ADDENDUM = PREPARED
CUMULATIVE_SERIAL_REGRESSION_MATRIX = PREPARED
COMPOSED_PRODUCER_WIRING_GATE = NOT_RUN
PILOT = NOT_EXECUTED
FUNCTIONAL_PASS = NO
MERGE_READY = NO
```

No evidence from #462/#465/#469/#472/#474 transfers across SHAs. Serial promotion and exact-head requalification rules from the parent packet remain unchanged.
