# Roadmap 8 — A02 Independent Verifier Donor/Fit Audit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #94

## Frozen requirement

A02 requires an independent verification boundary:

```text
orchestrator execution/result
-> evidence candidate
-> independently selected/authorized verifier
-> verifier result/evidence
-> metaO hard gates
-> metaO final acceptance authority
```

The verifier is not the final authority. A scorer/evaluator success can never directly produce `METAO_ACCEPTED`.

## Frozen donor pins

```text
OMA
repo   = tihotm/oma
commit = ca43381dc8bce4041da4fc09efbe939642729939
paths  = src/oma/acceptance.py
         src/oma/pipeline.py

Inspect AI
repo   = UKGovernmentBEIS/inspect_ai
commit = ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
paths  = src/inspect_ai/scorer/_scorer.py
         src/inspect_ai/scorer/_score.py
         src/inspect_ai/scorer/_metric.py

in-toto
repo   = in-toto/in-toto
commit = a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b
path   = in_toto/verifylib.py
```

## OMA fit

### What is proven/useful

OMA provides the strongest donor semantics for acceptance closure:

- evidence is evaluated independently of executor terminal claims;
- subject/state/context/policy/obligation bindings are explicit;
- authority, trust, policy bundle, snapshot freshness, provenance, aggregation and retry decisions are separate validation stages;
- final validation observations bind stage decisions to evidence roots;
- acceptance is one stage inside a larger fail-closed validation graph, not an executor-owned status.

`src/oma/pipeline.py` composes authority/trust/policy/snapshot/provenance/obligation/acceptance into observations and a validation graph. This is exactly the invariant metaO must preserve.

### What OMA does not provide at this pin

No reusable first-class `VerifierPort` / verifier registry / independent verifier execution abstraction was identified. OMA accepts evidence into its validation pipeline; it is therefore a donor for **verification authority invariants and closure**, not for the plugin execution interface itself.

### Decision

```text
MODE = ADAPT INVARIANTS / DO NOT ADOPT AS VERIFIER RUNTIME
```

Take:

- hard separation of execution from acceptance;
- exact evidence binding;
- validation-stage evidence roots;
- authoritative trust/authority/provenance rules.

Do not take:

- OMA as the metaO runtime foundation;
- OMA-specific topology as the verifier plugin contract.

## Inspect AI fit

### What is proven/useful

At the frozen pin, `Scorer` is a runtime-checkable protocol whose execution receives evaluation state/target and returns a structured `Score` or no score.

Inspect AI also provides:

- scorer registration and named recreation (`ScorerSpec` / registry);
- separation between task/model execution and scorer execution;
- multiple scorers over one evaluated state;
- structured output (`Score.value`, explanation, metadata, history);
- scorer identity/registry metadata recorded with scoring events;
- model usage accounting around scorer execution.

This maps well to a framework-neutral verifier plugin boundary without giving the evaluator final authority.

### What must not be copied literally

Inspect AI's `TaskState`, `Target`, `Score`, registry internals and async task runtime are evaluator-framework concepts. They must not become metaO Core contracts.

### Decision

```text
MODE = ADAPT EXECUTION / REGISTRY / RESULT-SHAPE PATTERNS
DEPENDENCY = NO WHOLE INSPECT_AI RUNTIME REQUIRED
```

Adapt concepts:

```text
Scorer Protocol      -> VerifierPort Protocol
ScorerSpec/registry  -> VerifierDescriptor + VerifierRegistry
Score                -> VerifierResult
scorer name/metadata -> verifier identity/version/capabilities
```

## in-toto fit

### What is proven/useful

`in_toto/verifylib.py` demonstrates fail-closed verification of independently produced metadata with:

- authorized functionaries;
- threshold checks;
- signature verification;
- metadata loading and verification;
- independent inspection execution;
- explicit exceptions on failed verification.

These are strong hostile/distributed-boundary semantics.

### Why it is not the V1 verifier abstraction

The implementation is intentionally supply-chain-layout specific. Adopting it as the general metaO verifier runtime would leak a domain model unrelated to orchestrator-level evidence verification.

### Decision

```text
MODE = REFERENCE / HOSTILE-BOUNDARY SEMANTICS
```

Use later when the trust profile requires signed attestations/authorized functionaries. Do not make in-toto a mandatory V1 dependency.

## Composition decision

```text
A02_EXECUTION_PATTERN = Inspect AI / ADAPT
A02_VALIDATION_INVARIANTS = OMA / ADAPT
A02_HOSTILE_AUTHENTICITY = in-toto / REFERENCE
METAO_SPECIFIC_BUILD = minimum VerifierPort + VerifierRegistry + VerifierResult
FINAL_ACCEPTANCE_AUTHORITY = metaO only
```

No donor supplies the complete meta-orchestrator abstraction. The minimum BUILD is justified because it is the project-specific boundary that composes donor patterns across orchestrators.

## Proposed minimum contract

This is a design target, not implemented code in this audit:

```text
VerifierDescriptor
  verifier_id
  version
  capabilities
  metadata

VerificationRequest
  mission_id
  execution_id
  subject_id
  subject_state_id
  verification_context_id
  policy_bundle_id
  obligation_id
  evidence_payload_digest
  evidence/provenance reference

VerifierResult
  verifier_id
  passed
  reason
  score?          # advisory only
  confidence?     # advisory only
  output_digest
  usage           # later feeds A18

VerifierPort
  descriptor
  verify(request) -> VerifierResult

VerifierRegistry
  register/unregister/get/eligible
```

## Selection and authority rule

Verifier choice must come from metaO-owned policy/registry state, not from an executor-provided `verifier_id` string.

Required sequence:

```text
1. determine verification requirement from policy/obligation
2. resolve eligible verifier from metaO VerifierRegistry
3. execute verifier through VerifierPort
4. bind result to exact mission/execution/subject state/context/policy/obligation/payload
5. normalize to canonical EvidenceEnvelope
6. evaluate normal hard gates
7. metaO emits final decision
```

Forbidden:

```text
executor chooses its own trusted verifier as terminal authority
verifier PASS bypasses policy/provenance/authority/budget
Inspect AI Score becomes ACCEPT directly
framework-specific scorer types enter metaO Core
in-toto layout becomes generic metaO evidence schema
```

## Dependency order

The donor decision is independent and complete.

Product implementation remains ordered behind the canonical evidence boundary:

```text
#90 / PR #91 canonical EvidenceEnvelope
-> executable-green
-> A18 budget composition may proceed per Roadmap 8 sequence
-> A02 VerifierPort implementation may target the canonical envelope
```

A02 implementation can be designed in parallel, but should not be merged while the evidence contract is structurally divergent.

## Measurement

```text
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO
FIT_DECISION = COMPLETE
```

## Acceptance criteria result

```text
EXACT_DONOR_PINS = RECORDED
ADOPT_ADAPT_REFERENCE_DECISION = COMPLETE
WHOLE_DONOR_DEPENDENCY = NO
MINIMUM_METAO_CONTRACT = DOCUMENTED
FINAL_AUTHORITY = METAO
CALLER_FABRICATED_VERIFIER_AUTHORITY = FORBIDDEN
PRODUCT_IMPLEMENTATION = DEFERRED_PENDING_CANONICAL_EVIDENCE
```
