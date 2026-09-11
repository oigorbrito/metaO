# MetaO Operational Pilot Execution Packet V1

Status: PREPARED_NOT_EXECUTED
Owner: #360
Related maturity owner: #357
Related runtime-health work: #160, #168/T6, #461/#462, #464/#465, #468/#469

This packet prepares a bounded real-provider pilot. It does not claim that the pilot has executed or passed.

## Purpose

Exercise the already-qualified local composed supervision path with real external execution while preserving MetaO authority over planning, policy/risk/budget, retry/recovery/failover causality, evidence, verification, and independent acceptance.

The pilot must not be used to promote any capability beyond the evidence actually produced.

## Evidence rule

```text
PREPARED != EXECUTED
EXECUTED != PASSED
UNIT_PASS != PILOT_PASS
SIMULATED != REAL_PROVIDER
HOSTED_PRE_STEP_FAILURE != PRODUCT_FAILURE
EXACT_HEAD_GATE_PASS = qualifying evidence
```

## Pilot identity

Before execution fill all fields exactly:

```text
PILOT_ID = METAO-PILOT-001
REPOSITORY = oigorbrito/metaO
COMMIT_SHA = <exact detached HEAD>
BRANCH_OR_DETACHED = <value>
WORKTREE_CLEAN_BEFORE = YES/NO
WORKTREE_CLEAN_AFTER = YES/NO
MISSION_ID = <value>
EXECUTION_ID = <value>
ATTEMPT_IDS = <ordered values>
PRIMARY_RUNTIME = <runtime id/version/config>
SECONDARY_RUNTIME = <runtime id/version/config>
PROVIDER_CREDENTIAL_MODE = <ephemeral env/manual authenticated session/other>
REAL_OR_SIMULATED = REAL
```

Do not store provider secrets, tokens, API keys, or authentication material in the evidence artifact.

## Preconditions

The pilot may start only when all applicable conditions are satisfied:

- exact repository SHA is recorded;
- worktree is clean;
- required local deterministic gates for the candidate SHA pass;
- runtime/provider identities and versions are recorded;
- credentials are available through an explicitly authorized non-persistent mechanism;
- policy, risk and budget bounds are explicit;
- external side effects are disabled, sandboxed, reversible, or protected by existing idempotency authority;
- #462/#465/#469 evidence is not silently transferred from other SHAs;
- hosted Actions blocker #71 is recorded separately if still present.

## Pilot workload

Use a low-risk engineering objective with deterministic verification. The first pilot must not require production deployment, financial transactions, privileged infrastructure mutation, destructive data changes, or irreversible external effects.

The objective should require more than one work unit and permit independent verification of the resulting artifact.

## Required flow

```text
one bounded project objective
-> MetaO derives plan/work units
-> Policy/Risk/Budget authorize execution
-> primary real runtime/provider executes permitted work
-> factual execution/evidence recorded
-> inject or observe one controlled runtime/provider failure where safe
-> failure causality remains factual
-> bounded retry/reselection rules apply
-> alternate eligible runtime/provider may execute new controlled attempt
-> repository/work state handoff is preserved
-> verification runs independently
-> if verification fails, MetaO creates corrective work
-> corrective execution runs under the same constraints
-> independent Acceptance evaluates final evidence
-> terminal result is recorded with exact lineage
```

## Runtime-health and recovery invariants

If the candidate includes the relevant qualified runtime-health slices, the pilot must verify these invariants without bypassing their authority boundaries:

- runtime self-report does not override factual outcomes;
- one isolated failure does not permanently quarantine a runtime;
- repeated factual failures cross configured thresholds deterministically;
- ordinary retry/reselection is bounded;
- `UNKNOWN`, `UNHEALTHY`, `QUARANTINED`, and `RECOVERING` are not treated as ordinary healthy retry targets according to the qualified contracts;
- failover does not erase authoritative retry/history evidence;
- recovery probe authorization, when present, is explicit and does not itself dispatch work or mint `HEALTHY`;
- return to normal health requires canonical fresh factual evidence.

If a required slice is still unmerged/unqualified, mark the corresponding invariant `NOT_IN_CANDIDATE` rather than simulating a PASS.

## Pilot scenarios

### P0 — real healthy baseline

A real provider/runtime completes a bounded work unit, evidence is generated, verification is independent, and Acceptance issues the terminal verdict.

### P1 — controlled provider/runtime failure and alternate execution

A controlled factual failure occurs on the primary path. The failure classification is preserved and a new authorized attempt may select the alternate eligible runtime/provider. The original execution is never relabeled as success.

### P2 — retry pressure bound

Where #465 semantics are present and qualified, repeated/alternating failure must not create unbounded attempts or reselection. Attempt lineage must remain consistent with the existing authoritative retry history.

### P3 — controlled recovery

Where #469 semantics are present and qualified, an unhealthy/quarantined/recovering runtime may enter only an explicitly authorized recovery-probe path. Probe authorization alone must not restore ordinary eligibility.

### P4 — verification failure and corrective work

Verification deliberately detects a bounded defect. MetaO creates corrective work, executes it under policy/budget constraints, re-verifies, and Acceptance remains separate from execution.

### P5 — restart/handoff durability

At a safe checkpoint, stop and resume the execution environment. Authoritative lineage/evidence required by the candidate must survive or replay according to the existing qualified durability mechanism.

## Success criteria

The pilot is PASS only if every required scenario for the candidate completes and all of the following are true:

```text
EXACT_HEAD_MATCH = YES
WORKTREE_CLEAN_BEFORE = YES
WORKTREE_CLEAN_AFTER = YES
REAL_PROVIDER_EXECUTION = YES
POLICY_RISK_BUDGET_ENFORCED = YES
FAILURE_CAUSALITY_PRESERVED = YES
ATTEMPT_LINEAGE_PRESERVED = YES
INDEPENDENT_VERIFICATION = YES
INDEPENDENT_ACCEPTANCE = YES
NO_UNAUTHORIZED_EXTERNAL_EFFECT = YES
MACHINE_READABLE_EVIDENCE = COMPLETE
```

A scenario not present in the candidate must be marked `NOT_IN_CANDIDATE`, not PASS.

## Abort criteria

Abort the pilot and preserve evidence if any of these occur:

- unexpected repository SHA or dirty worktree;
- credential leakage to files/logs/output;
- policy/risk/budget denial;
- ambiguous causal classification;
- uncontrolled or irreversible external side effect;
- retry/reselection exceeds configured bound;
- stale/forged/truncated authoritative history is accepted;
- runtime-health state is manually rewritten to force eligibility;
- Acceptance is bypassed or execution self-accepts;
- dependency/runtime version mismatch invalidates the candidate assumptions.

Classify the abort before modifying tests or code:

```text
PRODUCT_REGRESSION
TEST_HARNESS_REGRESSION
DEPENDENCY_RUNTIME_MISMATCH
ENVIRONMENT_RESOURCE_BLOCKER
EXTERNAL_INFRASTRUCTURE
CREDENTIAL_AUTHORIZATION_BLOCKER
```

## Machine-readable evidence minimum

Persist using existing canonical evidence structures wherever possible. Do not create a competing evidence authority.

At minimum the recovered artifact/report must contain:

```text
pilot_id
repository
commit_sha
worktree_clean_before
worktree_clean_after
mission_id
execution_id
attempt_ids
runtime_id
runtime_version
config_id
provider_identity_non_secret
provider_credential_mode_non_secret
commands
start_time
end_time
real_or_simulated
policy_result
risk_result
budget_result
strategy_selection
failure_classification
health_before
health_after
verification_result
acceptance_result
evidence_ids
external_effects_summary
result
blocker_or_failure_classification
```

## Current blockers as of packet preparation

```text
GITHUB_HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP (#71)
HOSTED_CI_REQUIRED_FOR_LOCAL_FUNCTIONAL_VALIDITY = NO
HOSTED_CI_REQUIRED_FOR_FULL_#360_CLOSURE = YES

REAL_PROVIDER_CREDENTIAL = EXTERNAL_AUTHORIZATION_OR_MANUAL_LOGIN_REQUIRED
#462 = FROZEN / NOT YET EXACT-HEAD REAL-RUNTIME QUALIFIED
#465 = DRAFT / NOT YET EXACT-HEAD LOCALLY QUALIFIED
#469 = DRAFT / NOT YET EXACT-HEAD LOCALLY QUALIFIED
```

These blockers do not authorize weakening the pilot. They determine which evidence level can currently be reached.

## Promotion sequence

1. qualify #462 exact frozen head independently;
2. qualify #465 exact head and merge only if its gate passes;
3. qualify #469 exact head and merge only if its gate passes;
4. construct pilot candidate from an exact `main` that contains only qualified slices;
5. authorize real-provider credential use through an approved non-persistent path;
6. execute P0 first;
7. execute P1/P4;
8. execute P2/P3 only if the corresponding slices are actually present and qualified;
9. execute P5 where durability semantics are in the candidate;
10. record exact evidence and reconcile #360/#357/#160/#168 without automatic parent closure.

## Non-goals

- no benchmark or performance superiority claim;
- no production-readiness claim from one pilot;
- no automatic closure of #160, #168, #357 or #360;
- no credential persistence;
- no workaround that bypasses Policy, Budget, runtime health, verification, or Acceptance;
- no treating GitHub hosted pre-step failures as MetaO functional failures.
