# MetaO Operational Pilot Cross-Authority Invariants V1

Status: PREPARED_NOT_EXECUTED
Owner: #360
Parent packet: `docs/PILOT-OPERATIONAL-EXECUTION-PACKET-V1.md`
Normative addendum: `docs/PILOT-OPERATIONAL-PROVENANCE-ADDENDUM-V1.md`
Related slices: #465, #469, #472, #474; scientific matrix: #168/T6-T7.

This document is a normative extension of the pilot packet. It captures cross-slice authority invariants discovered after the provenance addendum was prepared. These invariants must be exercised by the composed deterministic T6/T7 gate before the real pilot. They do not claim executable qualification or pilot PASS.

## Evidence rule

```text
PROBE_EXECUTION_FAILED != RUNTIME_LOCAL_HEALTH_FAILURE
PRE_EXECUTION_DENIAL != RETRYABLE_EXECUTION_FAILURE
PROBE_AUTHORIZED != ORDINARY_RETRY_ELIGIBLE
PROBE_SUCCEEDED != ORDINARY_RETRY_ELIGIBLE
PROBE_ELIGIBLE != HEALTH_OBSERVATION_AUTHORIZED
FENCED_EXECUTION_FAILURE != RUNTIME_LOCAL_HEALTH_FAILURE
```

## I1 — recovery probe failure must pass factual failure-origin gating

A recovery probe is an execution. Its unsuccessful outcome does not by itself prove a runtime-local health failure.

```text
FailureOrigin::RuntimeLocal
  -> may produce canonical runtime-health failure evidence

FailureOrigin::ProviderService | NetworkTransport
  -> preserve external-origin evidence
  -> MUST NOT increment runtime-local failure/quarantine counters

FailureOrigin::Capacity | Policy
  -> pre-execution condition
  -> MUST NOT mint execution failure
  -> MUST NOT mint runtime-health failure

FailureOrigin::Unknown or nonfactual
  -> fail closed
```

Negative case: a controlled recovery probe fails because of provider/network conditions while its runtime binding is otherwise valid. Runtime health must not be degraded/quarantined solely from that failure.

## I2 — retry causality must not manufacture execution failure

Bounded retry consumes factual execution-failure causality. Capacity/policy pre-execution conditions live in a separate authority surface and cannot be converted into `Failed` merely to enter retry eligibility.

```text
Capacity | Policy
  -> original_outcome = None
  -> not a retryable execution failure

ProviderService | NetworkTransport
  -> may be retryable only when canonical #141 causality says so
  -> retry eligibility does not imply runtime-local failure

RuntimeLocal
  -> may participate in retry causality
  -> may also affect runtime health only through canonical health evidence
```

Negative case: a policy/capacity denial is presented as if it were `FactualExecutionOutcome::Failed`; the composed path must reject the fabrication and must not dispatch retry.

## I3 — controlled recovery cannot reopen ordinary retry directly

Recovery-probe authority and ordinary retry authority are separate.

```text
UNHEALTHY | QUARANTINED | RECOVERING
  -> ordinary retry = INELIGIBLE
  -> controlled probe may be eligible

probe authorization
  -> does not reset attempt history
  -> does not mint next_attempt
  -> does not dispatch ordinary retry

probe success
  -> produces fresh factual evidence
  -> canonical health projection runs again

ordinary retry may become eligible only if:
  health == HEALTHY | DEGRADED
  AND #141 causal retry == eligible
  AND #140 policy/risk/budget == allow
  AND A11 retry history is preserved
```

Negative case: a successful probe with preserved `RECOVERING` state or exhausted A11 history must not directly reopen ordinary retry.

## I4 — probe result must cross execution lease/fence and factual binding before health admission

Probe eligibility only decides whether the recovery attempt may be made. It does not authorize the resulting observation to enter runtime-health history.

Required order:

```text
#469 probe eligibility
-> canonical execution authority executes probe
-> current ExecutionLease/fence is checked
-> canonical execution -> runtime/version/config binding is checked
-> factual failure origin is checked
-> #474 health-observation admission decides whether the observation may enter health history
```

Negative stale-result race:

```text
1. probe is authorized
2. execution ownership/fence rotates or is released
3. probe result arrives late
4. observation admission rejects stale authority
5. no health fact is appended
6. retry history is not reset
7. no dispatch/failover/Acceptance authority is minted
```

Positive admission requires current lease/fence, canonical binding, non-zero factual observation, and an origin that is allowed to affect runtime health.

## I5 — fencing proves ownership/binding, not causal blame

A failed execution may be perfectly fenced and correctly bound to a runtime while still having an external failure origin.

```text
current lease/fence
+ canonical execution -> runtime/version/config binding
+ factual failed/timeout outcome
+ factual failure-origin
-> decide whether runtime-health failure admission is allowed

RuntimeLocal
  -> may feed runtime-health failure

ProviderService | NetworkTransport
  -> preserve external failure evidence
  -> MUST NOT increment runtime-local failure/quarantine

Capacity | Policy
  -> pre-execution
  -> no execution failure fact exists to admit
```

Negative case: provider/network failure with valid lease/fence and exact runtime binding must still leave runtime-local failure/quarantine counters unchanged.

## Required composed gate extensions

In addition to the existing provenance addendum gate, the exact resulting `main` must demonstrate:

```text
T6T7_PROBE_FAILURE_ORIGIN_GATED = YES
T6T7_PREEXEC_DENIAL_MINTED_EXECUTION_FAILURE = NO
T6T7_PROBE_REOPENED_ORDINARY_RETRY_DIRECTLY = NO
T6T7_PROBE_RESET_RETRY_HISTORY = NO
T6T7_STALE_PROBE_RESULT_HEALTH_ADMITTED = NO
T6T7_FENCED_EXTERNAL_FAILURE_COUNTED_RUNTIME_LOCAL = NO
T6T7_PROVIDER_NETWORK_FAILURE_RETRYABLE_IMPLIES_RUNTIME_FAILURE = NO
```

Required adversarial scenarios:

1. provider/network recovery-probe failure with valid binding does not alter runtime-local health;
2. capacity/policy pre-execution denial cannot enter retry as a fabricated `Failed` outcome;
3. successful probe does not directly reopen ordinary retry or reset A11 history;
4. probe result arriving after fence rotation is rejected without health mutation;
5. provider/network failure with current fence and exact binding is still excluded from runtime-local failure counters;
6. every rejection leaves execution outcome, retry dispatch, probe dispatch and Acceptance authority unchanged.

## Serial promotion consequence

These invariants are cumulative. Each serial rebase must preserve previously promoted authority behavior. A focal slice PASS cannot substitute for this composed gate.

```text
#465 qualification -> ordinary retry authority only
#469 qualification -> recovery-probe authority only
#472 qualification -> factual failure-origin authority only
#474 qualification -> fenced health-observation admission only
final exact main -> cross-authority invariants above must PASS together
```

## Qualification boundary

```text
CROSS_AUTHORITY_INVARIANTS = PREPARED
COMPOSED_CROSS_AUTHORITY_GATE = NOT_RUN
FUNCTIONAL_PASS = NO
PILOT = NOT_EXECUTED
MERGE_READY = NO
```

This document adds no product authority, does not qualify any current PR head, and does not permit evidence transfer across SHAs.