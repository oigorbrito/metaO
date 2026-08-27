# Python Golden Equivalence Audit for Candidate C

Status:

- the canonical frozen Python #192 fixture was recovered from PR #201
- source fixture: `tests/golden/chassis_v1.json`
- baseline commit: `b69a4e502b07ddfa1f5e05399710e335d5edfbc0`
- a pinned copy is materialized under `experiments/csharp-chassis-c/fixtures/python/chassis_v1.json`
- the golden count is fixed at 4 cases

Method:

- compare each frozen Python case against the C# semantic harness result
- treat any case outside the frozen golden as out of scope for equivalence claims
- use `NOT_PROVEN` for claims that are not demonstrated by the frozen golden itself

Interpretation rule:

- the Python fixture has exactly 4 cases
- the 24 direct cases below are the C# harness battery and are not the Python golden count
- if a golden case is not reproduced exactly, equivalence is `NOT_PROVEN`
- `NOT_PROVEN` is not a failure of the C# candidate

Candidate:

- `C = explicit C#/.NET modular chassis`

Exact frozen Python cases:

| Case | PYTHON_EXPECTED | CSHARP_ACTUAL | EQUIVALENT |
|---|---|---|---|
| orchestrator_done_without_evidence | NOT_DONE | NOT_DONE | YES |
| bound_verified_evidence | ACCEPT | ACCEPT | YES |
| untrusted_verifier | BLOCK | BLOCK | YES |
| stale_evidence | STALE | STALE | YES |

C# extra conformance cases:

| Case | PYTHON_EXPECTED | CSHARP_ACTUAL | EQUIVALENT |
|---|---|---|---|
| Invalid identities rejected | NOT_PROVEN | PASS | NOT_PROVEN |
| Succeeded without evidence is not accepted | NOT_PROVEN | PASS | NOT_PROVEN |
| Hard DENY overrides runtime success | NOT_PROVEN | PASS | NOT_PROVEN |
| Missing evidence cannot accept | NOT_PROVEN | PASS | NOT_PROVEN |
| Mis-bound evidence cannot accept | NOT_PROVEN | PASS | NOT_PROVEN |
| Python golden NOT_DONE | NOT_DONE | PASS | NOT_PROVEN |
| Python golden ACCEPT | ACCEPT | PASS | NOT_PROVEN |
| Python golden BLOCK | BLOCK | PASS | NOT_PROVEN |
| Python golden STALE | STALE | PASS | NOT_PROVEN |
| Duplicate runtime IDs fail deterministically | NOT_PROVEN | PASS | NOT_PROVEN |
| Incompatible versions fail deterministically | NOT_PROVEN | PASS | NOT_PROVEN |
| Runtime exception is contained | NOT_PROVEN | PASS | NOT_PROVEN |
| Cancellation cannot mint acceptance | NOT_PROVEN | PASS | NOT_PROVEN |
| Timeout cannot mint acceptance | NOT_PROVEN | PASS | NOT_PROVEN |
| Kernel framework purity | NOT_PROVEN | PASS | NOT_PROVEN |
| Whole orchestrator replacement | NOT_PROVEN | PASS | NOT_PROVEN |
| Runtime failure can fail over to fallback runtime | NOT_PROVEN | PASS | NOT_PROVEN |
| Reconciliation is idempotent | NOT_PROVEN | PASS | NOT_PROVEN |
| Concurrent budget oversubscription + settlement retry idempotency | NOT_PROVEN | PASS | NOT_PROVEN |
| Trusted verifier/provenance/authority accept | NOT_PROVEN | PASS | NOT_PROVEN |
| Unknown verifier blocked | NOT_PROVEN | PASS | NOT_PROVEN |
| Untrusted provenance blocked | NOT_PROVEN | PASS | NOT_PROVEN |
| Unauthorized authority blocked | NOT_PROVEN | PASS | NOT_PROVEN |
| Runtime self-mint blocked | NOT_PROVEN | PASS | NOT_PROVEN |

Current audit summary:

- `PYTHON_GOLDEN_CASES = 4`
- `GOLDEN_EQUIVALENT = 4`
- `GOLDEN_NON_EQUIVALENT = 0`
- `GOLDEN_NOT_PROVEN = 0`
- `CSHARP_EXTRA_CONFORMANCE_CASES = 30`
- `EXTRA_CSHARP_CASES_OUTSIDE_GOLDEN_SCOPE = 30`

Reading:

- `EQUIVALENT = YES` means the C# output matched the frozen Python expectation exactly
- `EQUIVALENT = NO` would mean a direct mismatch on a frozen golden case
- `EQUIVALENT = NOT_PROVEN` means the case is outside the frozen Python equivalence proof or not fully demonstrated by this audit

Known Python L5 defects not copied:

- shared budget oversubscription
- settlement retry idempotency

Related evidence:

- `experiments/csharp-chassis-c/fixtures/python/chassis_v1.json`
- `experiments/csharp-chassis-c/README.md`
- `experiments/csharp-chassis-c/tests/MetaO.TestKit/Program.cs`
