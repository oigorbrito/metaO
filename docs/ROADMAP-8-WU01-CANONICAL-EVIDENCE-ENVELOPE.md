# Roadmap 8 — Work Unit 01 — Canonical EvidenceEnvelope Boundary

Status: IMPLEMENTED / EXECUTABLE VALIDATION PENDING.

Issue: #90

## Objective

Converge the two divergent framework-neutral `EvidenceEnvelope` dataclasses that existed in `main` into one canonical evidence contract shared by public API, Core typing, runtime normalization and final acceptance.

## Architectural reason

The frozen boundary is:

```text
orchestrator result
-> thin runtime adapter
-> one metaO EvidenceEnvelope
-> independent acceptance
```

Before this WU:

```text
metao.core.EvidenceEnvelope       != metao.acceptance.EvidenceEnvelope
```

The package public API re-exported the Core class, while LangGraph, CrewAI, OpenAI Agents, runtime conformance and control-plane acceptance used the Acceptance class.

That split allowed the public contract and the executed acceptance contract to drift independently.

## Implementation

Canonical implementation:

```text
src/metao/evidence.py
```

Compatibility exports:

```text
metao.EvidenceEnvelope
metao.core.EvidenceEnvelope
metao.acceptance.EvidenceEnvelope
```

All three resolve to the same class object.

No orchestrator SDK is imported by `evidence.py`, `core.py` or `acceptance.py`.

## Canonical operational fields

The canonical constructor preserves the field set already exercised by the real multi-orchestrator acceptance path:

- evidence identity and obligation identity;
- mission/execution/orchestrator/adapter-version/attempt bindings;
- subject and authoritative state binding;
- verification context and policy binding;
- verifier, payload digest, provenance root and authority;
- pass/fail result;
- freshness/expiration;
- approval and confidence.

An explicit framework-neutral `adapter_id` field is added. Existing normalizers that do not supply it receive the deterministic fallback:

```text
adapter_id = orchestrator_id
```

This preserves current behavior without importing framework SDK types or changing acceptance authority.

## Legacy read aliases

The former Core envelope exposed several equivalent names. The canonical model preserves deterministic read aliases:

```text
obligation_ids          -> frozenset({obligation_id})
evidence_payload_digest -> payload_digest
provenance              -> provenance_root
approval_evidence       -> approval_id or ""
```

`verification_cost_units` remains an opaque non-negative compatibility field. This WU deliberately does not reinterpret it as money/tokens/time.

The former Core constructor cannot be safely recreated in full because it did not carry acceptance-critical fields such as `evidence_id`, `authority_id` and `passed`. Rather than fabricate those values, ambiguous legacy construction must fail explicitly. This is preferable to silently manufacturing acceptance authority.

## Acceptance semantics

Unchanged:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

No change was made to:

- binding gates;
- freshness;
- provenance trust;
- authority checks;
- policy binding;
- required-evidence aggregation;
- conflict handling;
- deterministic acceptance proof.

## Test surface

Focused regression:

```text
tests/unit/test_roadmap_8_work_unit_01.py
```

It locks:

1. public/Core/acceptance class identity;
2. deterministic legacy read aliases;
3. LangGraph, CrewAI and OpenAI Agents normalizers returning the canonical class;
4. `ExecutionResult.evidence` carrying canonical values;
5. no orchestrator-specific SDK import in evidence/Core/acceptance.

Existing Block J and Block L tests remain required regressions before merge.

## Composition / measurement

```text
EXTERNAL_DONOR_CODE_COPIED = NO
NEW_RUNTIME_DEPENDENCY = NO
ORCHESTRATOR_SDK_IN_CORE = NO
NEW_METAO_SPECIFIC_MODULE = src/metao/evidence.py
DUPLICATE_EVIDENCE_DATACLASS_DEFINITIONS_TARGET = 0
```

This is consolidation of an already-approved metaO-specific BUILD boundary, not a new capability.

## Next work unit

After this boundary is executable-green:

```text
Roadmap 8 WU02 — AcceptanceBudget final-path accounting
```

WU02 must compose the existing `AcceptanceBudget` into the final acceptance path for:

- money;
- tokens;
- verification wall-clock time;
- verifier/escalation attempts.

The approved donor pattern is Inspect AI at the frozen pin:

```text
UKGovernmentBEIS/inspect_ai
eb f4815ee260afcc8c34ad9d66e6f8d98a89e905
src/inspect_ai/util/_limit.py
```

(Commit shown without spaces in repository metadata: `ebf4815ee260afcc8c34ad9d66e6f8d98a89e905`.)

## Current evidence status

```text
IMPLEMENTATION = COMPLETE
FOCUSED_TESTS = NOT_EXECUTED_IN_THIS_CONNECTED_ENVIRONMENT
FULL_REGRESSION = NOT_EXECUTED_IN_THIS_CONNECTED_ENVIRONMENT
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
MERGE = NOT_AUTHORIZED
```
