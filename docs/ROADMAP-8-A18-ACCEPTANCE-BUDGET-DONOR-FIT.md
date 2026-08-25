# Roadmap 8 — A18 Acceptance Budget Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

## Objective

Freeze the smallest safe design for acceptance/verification resource accounting in metaO.

A18 governs the resources consumed by independent verification and acceptance work. Runtime completion is not acceptance, and opaque runtime cost is not a substitute for acceptance usage.

## Current metaO state

`src/metao/governance.py` already defines `AcceptanceBudget` with four limit/usage dimensions:

```text
money
 tokens
 wall_time_s
 verifier_attempts
```

It provides immutable consumption and fail-closed `BudgetExhausted` behavior when a post-consumption value exceeds a configured limit.

`src/metao/control_plane.py` already performs a precheck via `_budget_has_capacity(...)` before the mission execution path.

The current final path is incomplete for A18:

```text
execution succeeds
-> budget.consume(verifier_attempts=1)
-> normalize evidence
-> evaluate acceptance
```

Consequences:

- verifier-attempt usage is effectively the only acceptance dimension debited in the final path;
- the attempt is counted only after successful runtime execution;
- failed/cancelled/exceptional work can escape verifier-attempt accounting;
- money, token and wall-clock usage are not bound to the verification request/result path;
- there is no append-only factual usage authority for replay/audit;
- a budget exception does not itself preserve the usage that caused the overrun.

Frozen gap statement:

```text
BUDGET_PRIMITIVE_EXISTS
!= ACCEPTANCE_USAGE_FINAL_PATH_PROVEN
```

## Frozen donor

```text
repo   = UKGovernmentBEIS/inspect_ai
commit = ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
path   = src/inspect_ai/util/_limit.py
```

No donor code is copied in this audit.

## Inspect AI fit

The useful donor pattern is resource-limit accounting with explicit separation between:

```text
limit
usage
remaining
```

The donor also provides explicit limit-exceeded semantics and scopes that preserve which applied limit was exceeded.

Relevant design properties:

- usage is first-class rather than inferred only from a final success state;
- remaining capacity is derived from limit minus observed usage;
- limit violations are explicit errors, not successful results;
- usage snapshots can survive scope completion;
- time/token/cost dimensions are treated as distinct resources rather than collapsed into one opaque unit.

These concepts fit A18.

The Inspect AI runtime, task/sample model, context-tree implementation and concrete model accounting are not metaO Core abstractions and must not be imported as dependencies.

Decision:

```text
Inspect AI limit/usage/remaining pattern = ADAPT
Inspect AI limit-exceeded fail-closed semantics = ADAPT
Inspect AI task/sample runtime = DO NOT TAKE
whole Inspect AI dependency = NO
```

## Composition decision

Reuse `AcceptanceBudget` as the policy/limit object. Do not build a second budget engine.

Add a factual verification-usage record and append-only authority for actual acceptance work.

Preferred V1 shape:

```text
VerificationUsage
AcceptanceUsagePort
```

`AcceptanceUsagePort` is preferred over `VerificationUsagePort` because the budget belongs to the broader independent acceptance plane and may later account for non-verifier acceptance work such as durable human escalation without redefining the port.

The initial record remains verifier-centric because A18's first implementation target is verification accounting.

Decision:

```text
AcceptanceBudget = REUSE / REFINE IN COMPOSED PATH
VerificationUsage = BUILD MINIMAL METAO-SPECIFIC
AcceptanceUsagePort = BUILD MINIMAL METAO-SPECIFIC
new budget engine = NO
new audit database = NO
```

The existing SQLite persistence layer may back the port if it preserves append-only factual records and deterministic retrieval.

## VerificationUsage frozen fields

Minimum V1 record:

```text
usage_id
mission_id
execution_id
attempt_id
verifier_id
verification_request_id
subject_id
subject_state_id
verification_context_id
policy_bundle_id
started_at_epoch
ended_at_epoch
money
tokens
wall_time_s
verifier_attempts
outcome
```

Optional implementation metadata may be added only when required by the concrete verifier boundary, for example verifier version or a result digest.

Binding rule:

```text
USAGE_WITHOUT_REQUEST_BINDING
!= AUTHORITATIVE_ACCEPTANCE_ACCOUNTING
```

The record must identify the exact verification/acceptance work that consumed the resources.

## Required resource semantics

### verifier_attempts

A verifier attempt counts when verification begins, not when it passes.

Frozen rule:

```text
verifier invoked / attempt begins
-> verifier_attempts += 1
```

A failed verifier, timeout, exception, invalid result or rejected evidence still consumed an attempt.

### wall_time_s

Wall clock is measured by metaO around the verification boundary.

Do not trust the verifier/runtime to self-report authoritative wall-clock usage.

Frozen rule:

```text
started = metaO monotonic/controlled clock
run verifier
ended = metaO clock
wall_time_s = ended - started
```

The concrete implementation may inject a clock for deterministic tests.

### money and tokens

Where the verifier/provider returns authoritative usage for money/tokens, bind it to the exact request/result and persist it.

If a configured budget dimension requires usage but the selected verifier cannot provide the required authoritative value, fail closed rather than silently recording zero.

Frozen rule:

```text
missing required usage
!= zero usage
```

A policy may explicitly mark a dimension not applicable/unbounded. That is different from missing required usage.

### verification_cost_units

Existing or future `verification_cost_units` remains an opaque selection/routing metric.

It must not be automatically converted into:

```text
money
tokens
wall_time_s
```

Frozen rule:

```text
OPAQUE_COST_UNITS != ACCOUNTING_FACTS
```

## Precheck semantics

A budget precheck happens before verifier execution.

For discrete known work:

```text
remaining verifier attempts < 1
-> do not invoke verifier
-> BLOCK / budget_exhausted
```

For dimensions whose exact final usage is not knowable in advance, the precheck uses known capacity/declared maximums where available but does not fabricate future usage.

The existence of some positive remaining capacity does not guarantee the eventual operation will stay within budget.

## Post-accounting semantics

Actual usage must be persisted after work executes, including when the observed usage crosses a limit.

Required ordering:

```text
precheck
-> mark/count attempt start
-> execute verifier
-> measure/collect actual usage
-> append factual VerificationUsage
-> apply usage to AcceptanceBudget
-> if over budget: fail closed
-> only then may the result proceed toward terminal acceptance
```

Critical rule:

```text
ACTUAL_OVER_BUDGET
-> PERSIST USAGE
-> BLOCK
```

Do not throw away the factual usage record because the usage itself caused `BudgetExhausted`.

## Exception and failure semantics

Accounting must close even when the verifier does not return a normal passing result.

Examples:

```text
verifier exception
verifier timeout
invalid result
provider error
verification FAIL
candidate BLOCK/STALE
```

All still consume the resources actually used.

A `finally`-style accounting boundary or equivalent deterministic control flow should guarantee closure.

## Relation to A11

A11 and A18 are separate authorities:

```text
A11 = execution/retry facts
A18 = verification/acceptance usage facts
```

They may use the same SQLite database and shared persistence primitives.

Do not duplicate accounting facts across two competing authorities.

Cross-reference by IDs instead.

## Relation to A02

A18 product implementation should compose with A02's future verifier boundary:

```text
VerifierDescriptor
VerificationRequest
VerifierPort
VerifierResult
```

Expected composed path:

```text
VerificationRequest
-> A18 precheck
-> begin/count attempt
-> VerifierPort.verify(...)
-> VerifierResult + provider usage
-> metaO wall-clock closure
-> append VerificationUsage
-> AcceptanceBudget accounting
-> canonical EvidenceEnvelope
-> acceptance hard gates
```

A18 must not embed concrete verifier SDK types in Core.

## Relation to A14

Confidence-triggered extra verification is budgeted work.

```text
confidence requests additional verification
-> A18 precheck
-> run verifier only if permitted
-> account actual usage
```

Confidence cannot bypass budget exhaustion.

## Terminal authority rules

Frozen invariants:

```text
VERIFIER_PASS != METAO_ACCEPTED
BUDGET_AVAILABLE != METAO_ACCEPTED
USAGE_RECORDED != METAO_ACCEPTED
```

A18 is a hard gate. It can block acceptance; it cannot create acceptance by itself.

Over-budget actual work cannot be rescued by a passing verifier, high confidence, executor success or old evidence.

## Persistence semantics

`AcceptanceUsagePort` is append-only for factual usage.

Minimum operations should stay narrow, for example:

```text
append(usage)
for_mission(mission_id)
for_verification_request(verification_request_id)
```

Avoid generalized event-store APIs unless another Roadmap 8 requirement proves them necessary.

The persisted usage record is historical fact and must not be silently rewritten when budget/policy changes.

## Required future tests

Product integration must eventually prove through the composed path:

1. zero remaining verifier attempts blocks before verifier invocation;
2. attempt count increments when verification starts even if the verifier fails;
3. verifier exception still persists the actual usage record;
4. verifier timeout still persists the actual usage record;
5. metaO measures wall-clock rather than trusting verifier-provided wall time;
6. money usage is debited when authoritative provider usage exists;
7. token usage is debited when authoritative provider usage exists;
8. missing required money/token usage fails closed rather than becoming zero;
9. actual over-budget usage is persisted before the terminal BLOCK;
10. a verifier PASS that exceeds budget cannot become ACCEPT;
11. a failed verifier that consumed resources cannot refund its attempt silently;
12. `verification_cost_units` cannot satisfy money/token/time accounting;
13. usage for another request/subject/state/context cannot be rebound to the current verification;
14. duplicate usage IDs fail closed or are rejected by append-only persistence;
15. replay from persisted usage reproduces budget consumption deterministically;
16. A11 retry facts and A18 usage facts can coexist without double accounting;
17. confidence-driven additional verification consumes the same A18 budget;
18. no framework SDK type crosses the metaO Core boundary.

## Ordering

This donor-fit is complete. Product integration remains ordered behind WU01 executable proof and should compose with A02 rather than invent a temporary verifier contract.

```text
A18 donor-fit = COMPLETE

WU01 canonical EvidenceEnvelope -> executable-green
A18 product accounting primitive/port
A02 VerifierPort / Registry
compose A18 around VerifierPort execution
A14 confidence-driven additional verification uses A18
A16 terminal proof records applicable accounting references
```

If WU01 remains blocked, A18 implementation may prepare isolated governance/persistence primitives only when they do not depend on the unresolved EvidenceEnvelope branch. Do not stack blindly on #91.

## Measurement

```text
DONOR_REPO = UKGovernmentBEIS/inspect_ai
DONOR_COMMIT = ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
DONOR_PATH = src/inspect_ai/util/_limit.py
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO
NEW_BUDGET_ENGINE = NO
NEW_DATABASE = NO
```

## Acceptance criteria result

```text
EXACT_DONOR_PIN_PATH = RECORDED
CURRENT_BUDGET_PRIMITIVE_AND_GAP = DOCUMENTED
LIMIT_USAGE_REMAINING_PATTERN = ADAPT
ACCEPTANCE_BUDGET = REUSE
VERIFICATION_USAGE = BUILD_MINIMAL
ACCEPTANCE_USAGE_PORT = BUILD_MINIMAL
ATTEMPT_COUNTS_AT_START = FROZEN
METAO_WALL_CLOCK_AUTHORITY = FROZEN
MISSING_REQUIRED_USAGE_FAILS_CLOSED = FROZEN
OVER_BUDGET_USAGE_PERSISTED_BEFORE_BLOCK = FROZEN
OPAQUE_COST_UNITS_NOT_ACCOUNTING = FROZEN
WHOLE_INSPECT_AI_DEPENDENCY = NO
PRODUCT_CODE_CHANGE = NO
DONOR_DECISION = COMPLETE
```