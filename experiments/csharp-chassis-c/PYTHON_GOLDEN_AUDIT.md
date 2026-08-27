# Python Golden Equivalence Audit for Candidate C

Status:

- exact frozen Python #192 fixture is not present in this checkout
- the compiled Python test module references `tests/unit/golden/chassis_v1.json`, but that file is absent locally
- therefore the exact `PYTHON_EXPECTED` values cannot be re-read in this environment

Interpretation rule:

- if the frozen Python expectation cannot be read exactly, equivalence is `NOT_PROVEN`
- `NOT_PROVEN` is not a failure of the C# candidate

Candidate:

- `C = explicit C#/.NET modular chassis`

Direct semantic cases currently executable in the C# spike:

| Case | PYTHON_EXPECTED | CSHARP_ACTUAL | EQUIVALENT |
|---|---|---|---|
| Invalid identities rejected | NOT_PROVEN | PASS | NOT_PROVEN |
| Succeeded without evidence is not accepted | NOT_PROVEN | PASS | NOT_PROVEN |
| Hard DENY overrides runtime success | NOT_PROVEN | PASS | NOT_PROVEN |
| Missing evidence cannot accept | NOT_PROVEN | PASS | NOT_PROVEN |
| Mis-bound evidence cannot accept | NOT_PROVEN | PASS | NOT_PROVEN |
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

Current audit summary:

- `PYTHON_GOLDEN_CASES = 15`
- `EQUIVALENT = 0`
- `NON_EQUIVALENT = 0`
- `NOT_PROVEN = 15`

Known Python L5 defects not copied:

- shared budget oversubscription
- settlement retry idempotency

Related evidence:

- `experiments/csharp-chassis-c/README.md`
- `experiments/csharp-chassis-c/tests/MetaO.TestKit/Program.cs`
