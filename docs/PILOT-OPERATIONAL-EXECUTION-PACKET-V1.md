# MetaO Operational Pilot Execution Packet V1

Status: PREPARED_NOT_EXECUTED
Owner: #360
Related maturity owner: #357
Related runtime-health work: #160, #168/T6-T7, #461/#462, #464/#465, #468/#469, #471/#472, #473/#474

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
- #462/#465/#469/#472/#474 evidence is not silently transferred from other SHAs;
- a composed T6/T7 gate has passed on the exact resulting `main` after the required slices were promoted serially;
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
-> failure origin remains causally distinct from runtime health
-> bounded retry/reselection rules apply
-> alternate eligible runtime/provider may execute new controlled attempt
-> repository/work state handoff is preserved
-> stale owner cannot rewrite authoritative runtime-health evidence
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
- provider/service, network/transport, runtime-local, capacity and policy causes remain separately attributable where factual evidence supports them;
- provider/network/capacity/policy failures must not be silently rewritten as local-runtime failure;
- only the current authoritative execution owner with matching factual execution-to-runtime binding may authorize runtime-health observation admission;
- stale holder/generation/fence or cross-runtime/version/config observations fail closed;
- return to normal health requires canonical fresh factual evidence.

If a required slice is still unmerged/unqualified, mark the corresponding invariant `NOT_IN_CANDIDATE` rather than simulating a PASS.

## Pilot scenarios

### P0 — real healthy baseline

A real provider/runtime completes a bounded work unit, evidence is generated, verification is independent, and Acceptance issues the terminal verdict.

### P1 — controlled provider/runtime failure and alternate execution

A controlled factual failure occurs on the primary path. Failure class and failure origin are preserved separately. Provider/network/capacity/policy causes must not contaminate local runtime health. A new authorized attempt may select the alternate eligible runtime/provider. The original execution is never relabeled as success.

### P2 — retry pressure bound

Where #465 semantics are present and qualified, repeated/alternating failure must not create unbounded attempts or reselection. Attempt lineage must remain consistent with the existing authoritative retry history.

### P3 — controlled recovery

Where #469 semantics are present and qualified, an unhealthy/quarantined/recovering runtime may enter only an explicitly authorized recovery-probe path. Probe authorization alone must not restore ordinary eligibility.

### P4 — verification failure and corrective work

Verification deliberately detects a bounded defect. MetaO creates corrective work, executes it under policy/budget constraints, re-verifies, and Acceptance remains separate from execution.

### P5 — restart/handoff durability

At a safe checkpoint, stop and resume the execution environment. Authoritative lineage/evidence required by the candidate must survive or replay according to the existing qualified durability mechanism.

### P6 — stale-owner health fencing

Where #474 semantics are present and qualified, transfer or renew execution authority and then present a stale holder/generation/fence observation plus a cross-runtime binding attempt. Neither may contaminate runtime health; the current authoritative lease and factual execution-to-runtime binding must remain required.

## Success criteria

The pilot is PASS only if every required scenario for the candidate completes and all of the following are true:

```text
EXACT_HEAD_MATCH = YES
WORKTREE_CLEAN_BEFORE = YES
WORKTREE_CLEAN_AFTER = YES
REAL_PROVIDER_EXECUTION = YES
POLICY_RISK_BUDGET_ENFORCED = YES
FAILURE_CAUSALITY_PRESERVED = YES
FAILURE_ORIGIN_PRESERVED = YES
ATTEMPT_LINEAGE_PRESERVED = YES
STALE_OWNER_HEALTH_CONTAMINATION = NO
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
- ambiguous causal or failure-origin classification;
- provider/network/capacity/policy evidence is rewritten as local runtime failure without factual support;
- uncontrolled or irreversible external side effect;
- retry/reselection exceeds configured bound;
- stale/forged/truncated authoritative history is accepted;
- stale execution owner or mismatched runtime binding can alter runtime-health evidence;
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
failure_origin
failure_attribution_target
health_before
health_after
execution_lease_holder_non_secret
execution_lease_generation
execution_fencing_token_non_secret
execution_runtime_binding_evidence_ref
verification_result
acceptance_result
evidence_ids
external_effects_summary
result
blocker_or_failure_classification
```

## Current blockers as of packet reconciliation

```text
GITHUB_HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP (#71)
HOSTED_CI_REQUIRED_FOR_LOCAL_FUNCTIONAL_VALIDITY = NO
HOSTED_CI_REQUIRED_FOR_FULL_#360_CLOSURE = YES

REAL_PROVIDER_CREDENTIAL = EXTERNAL_AUTHORIZATION_OR_MANUAL_LOGIN_REQUIRED
#462 = FROZEN / NOT YET EXACT-HEAD REAL-RUNTIME QUALIFIED
#465 = DRAFT / CORRECTED HEAD / NOT YET EXACT-HEAD LOCALLY QUALIFIED
#469 = DRAFT / CORRECTED HEAD / NOT YET EXACT-HEAD LOCALLY QUALIFIED
#472 = DRAFT / CORRECTED HEAD / NOT YET EXACT-HEAD LOCALLY QUALIFIED
#474 = DRAFT / CORRECTED HEAD / NOT YET EXACT-HEAD LOCALLY QUALIFIED
```

Current prepared heads are informational only and are not transferable evidence:

```text
#462 = f6d9fe8d8035479d91a994745afe5b802936d338
#465 = b8e09e585dbfddfbc1251ea4b47a50ced97fb72c
#469 = 13fe27932db8c98459ad56569334cc55626c6b3d
#472 = 32ecb78b7de7677c09c69a933ebf41bd6e92d7a9
#474 = a98d49195e4823bd2e360951a6e61c92122942d4
```

These blockers do not authorize weakening the pilot. They determine which evidence level can currently be reached.

## Serial promotion sequence

Do not qualify all prepared heads and then merge them. Each merge changes `main` and may require a new branch head/requalification for later slices.

1. qualify #462 exact frozen head independently;
2. if PASS, merge #462 and record the resulting `main` SHA;
3. update/rebase #465 onto resulting `main`, obtain a new exact head, qualify that head, and merge only if PASS;
4. update/rebase #469 onto resulting `main`, obtain a new exact head, qualify that head, and merge only if PASS;
5. update/rebase #472 onto resulting `main`, obtain a new exact head, qualify that head, and merge only if PASS;
6. update/rebase #474 onto resulting `main`, obtain a new exact head, qualify that head, and merge only if PASS;
7. run one composed deterministic T6/T7 gate on the resulting exact `main` covering factual health, bounded retry, controlled recovery, failure-origin separation and stale-owner fencing;
8. construct the pilot candidate only from that qualified exact `main`;
9. authorize real-provider credential use through an approved non-persistent path;
10. execute P0 first;
11. execute P1/P4;
12. execute P2/P3/P6 only when the corresponding qualified slices are in the candidate;
13. execute P5 where durability semantics are in the candidate;
14. record exact evidence and reconcile #360/#357/#160/#168 without automatic parent closure.

## Non-goals

- no benchmark or performance superiority claim;
- no production-readiness claim from one pilot;
- no automatic closure of #160, #168, #357 or #360;
- no credential persistence;
- no workaround that bypasses Policy, Budget, runtime health, fencing, verification, or Acceptance;
- no treating GitHub hosted pre-step failures as MetaO functional failures.
