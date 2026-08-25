# Roadmap 8 — A14 Bound Confidence Advisory Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #102

## Objective

Freeze the smallest safe design for confidence in metaO acceptance.

Confidence is advisory evaluator output. It can increase verification or trigger escalation only after hard gates pass. It is never authority and never repairs missing, stale, conflicting or unauthorized evidence.

## Current metaO state

`src/metao/governance.py` already contains `apply_confidence_after_hard_gates(...)`.

Current semantics are sound at the primitive level:

```text
hard-gate decision != ACCEPT
-> return the hard-gate decision unchanged

hard-gate decision == ACCEPT
+ confidence below threshold
-> REQUIRE_HUMAN

hard-gate decision == ACCEPT
+ confidence at/above threshold
-> ACCEPT
```

Block K already proves that high confidence cannot convert `BLOCK` or `STALE` into `ACCEPT`.

The remaining gap is composition and binding:

```text
BARE_CONFIDENCE_FLOAT != TERMINAL_CONFIDENCE_AUTHORITY
CONFIDENCE_HELPER_EXISTS != BOUND_CONFIDENCE_FINAL_PATH
```

The current helper is not invoked by the final acceptance/control-plane path and a bare float does not identify who produced the confidence or what exact evidence/state it assessed.

## Frozen donor

```text
repo   = UKGovernmentBEIS/inspect_ai
commit = ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
paths  = src/inspect_ai/scorer/_scorer.py
         src/inspect_ai/scorer/_score.py
         src/inspect_ai/scorer/_metric.py
```

No donor code is copied in this audit.

## Inspect AI fit

Relevant donor concepts:

- scorer execution is separate from evaluated task/model execution;
- scorer identity can be named/registered;
- scorer output is a structured `Score` rather than a boolean authority decision;
- score carries value plus optional explanation and metadata;
- score edit/history/provenance data can preserve how evaluation output evolved;
- scoring events retain scorer identity/args and usage context.

These are appropriate result-shape and traceability patterns.

They are not final authorization semantics.

Decision:

```text
Inspect AI scorer-result concepts = ADAPT
Inspect AI task runtime = DO NOT TAKE
whole Inspect AI dependency = NO
```

## Composition decision

Reuse the existing metaO hard-gate precedence and confidence helper semantics. Do not create a second confidence subsystem.

Future composition should use A02's verifier boundary:

```text
VerifierPort
-> bound VerifierResult
-> canonical EvidenceEnvelope
-> hard gates
-> confidence advisory policy
-> ACCEPT / additional verification / REQUIRE_HUMAN
```

Decision:

```text
existing hard-gate precedence = REUSE
apply_confidence_after_hard_gates = REUSE / REFINE AT BOUNDARY
A02 VerifierResult = REUSE WHEN AVAILABLE
EvidenceEnvelope.confidence = REUSE
new confidence engine = NO
```

## Binding requirement

Confidence used by terminal acceptance must be attributable to the exact evaluation that produced it.

At minimum, the bound result must identify:

```text
verifier_id
verifier_version
mission_id
execution_id
subject_id
subject_state_id
verification_context_id
policy_bundle_id
evidence_payload_digest
confidence
explanation / reason or verifier-result digest
```

The future A02 verifier implementation should be the authority for verifier identity/selection. The caller or executor cannot simply inject a trusted confidence number.

The canonical `EvidenceEnvelope` already provides most of these bindings plus `confidence`. A14 should therefore compose existing envelope/verifier data rather than introduce a parallel score object into Core unless an implementation fit test proves one is necessary.

## Hard-gate precedence

Frozen rule:

```text
HARD_GATE_DENY -> confidence is irrelevant to authorization
```

Confidence cannot convert any of the following into success:

```text
BLOCK
STALE
missing required evidence
failed required evidence
unauthorized executor/verifier
provenance/authenticity failure
policy deny
retry-history violation
acceptance-budget exhaustion
conflicting/duplicate evidence
```

This precedence is mandatory regardless of confidence value.

## Allowed confidence effects

Only when all applicable hard gates are otherwise satisfied, confidence may deterministically influence:

1. whether another verifier must execute;
2. whether a stronger otherwise-eligible verifier should execute;
3. whether durable human escalation is required;
4. ordering among otherwise eligible verification paths.

Confidence itself does not issue `METAO_ACCEPTED`. It can leave an already-hard-gate-clean candidate eligible for acceptance or make verification stricter.

## Multiple verifier/evidence semantics

Do not introduce best-of-N cherry-picking.

If a mission requires multiple verifier/evidence results, confidence policy must operate over the exact policy-required set.

Forbidden:

```text
pick only the highest confidence
silently discard a contradictory required verifier
average away a hard failure
let optional high-confidence evidence replace missing mandatory evidence
```

Any aggregation rule must be explicit, deterministic and policy-bound.

For V1, prefer the smallest deterministic rule required by the actual verification topology instead of inventing a generalized statistical framework.

## Threshold semantics

Thresholds in Roadmap 8 must be explicit policy inputs.

```text
LEARNED_THRESHOLD = NO
RL_ROUTING = NO
AUTO_TUNED_CONFIDENCE_POLICY = NO
```

A threshold change is a policy/version change and should be visible to audit/terminal proof once A09/A16 are composed.

## Budget interaction

Additional verification and human escalation consume acceptance resources.

Therefore A14 terminal integration should occur only after A18 accounting is available, so low-confidence retries/escalations cannot create unbounded verification work.

```text
confidence asks for more verification
-> check AcceptanceBudget
-> run allowed verification/escalation
-> record usage
```

Budget exhaustion remains authoritative over confidence.

## Human escalation interaction

Low confidence may produce `REQUIRE_HUMAN`, but the human path must still obey A08/A15 binding and authority requirements.

Confidence does not authorize the approver and cannot make stale approval current.

## Terminal proof interaction

Once A16 terminal closure exists, applicable confidence decisions should contribute a deterministic observation root containing at least:

```text
policy/threshold identity
bound verifier result identity/digest
confidence value
resulting advisory action
```

This allows a later audit to explain why a candidate was accepted directly, sent to another verifier or escalated to a human.

## Required future tests

Product integration must eventually prove through the composed path:

1. `BLOCK + confidence=1.0` stays `BLOCK`;
2. `STALE + confidence=1.0` stays `STALE`;
3. missing required evidence cannot be filled by high confidence;
4. low confidence after clean hard gates triggers the policy-defined stricter action;
5. high confidence from an untrusted verifier is blocked before confidence policy;
6. confidence for another subject/state/payload is rejected by binding gates;
7. caller-injected confidence without authorized verifier result cannot become terminal authority;
8. confidence-driven additional verification consumes A18 budget;
9. exhausted budget cannot be bypassed by confidence;
10. conflicting required verifier results cannot be cherry-picked by confidence;
11. threshold/policy change changes the terminal/audit root when A16 is present;
12. same bound inputs/policy produce deterministic output.

## Ordering

This donor-fit is complete, but product integration is intentionally later than its dependencies:

```text
WU01 canonical EvidenceEnvelope -> executable-green
A18 acceptance-budget accounting
A02 VerifierPort / bound VerifierResult
A14 bound confidence advisory integration
A16 terminal-proof closure records confidence decision when applicable
```

No A14 product branch should be stacked blindly on the unexecuted WU01 branch.

## Measurement

```text
DONOR_REPO = UKGovernmentBEIS/inspect_ai
DONOR_COMMIT = ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
DONOR_PATHS = scorer/_scorer.py, scorer/_score.py, scorer/_metric.py
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO
NEW_CONFIDENCE_ENGINE = NO
```

## Acceptance criteria result

```text
EXACT_DONOR_PIN_PATHS = RECORDED
CURRENT_HELPER_STRENGTH_AND_GAP = DOCUMENTED
BOUND_CONFIDENCE_RULE = DOCUMENTED
HARD_GATE_PRECEDENCE = PRESERVED
ALLOWED_ADVISORY_EFFECTS = DOCUMENTED
BEST_OF_N_CHERRY_PICKING = FORBIDDEN
LEARNED_THRESHOLD_SCOPE = FORBIDDEN
WHOLE_INSPECT_AI_DEPENDENCY = NO
PRODUCT_CODE_CHANGE = NO
IMPLEMENTATION = DEFERRED_BY_A18_A02_ORDER
```
