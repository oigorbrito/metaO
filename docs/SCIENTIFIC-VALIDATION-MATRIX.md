# Scientific validation matrix registry (#168)

The canonical machine-readable registry is:

`docs/scientific-validation-matrix.json`

It maps T1 through T15 to the owning implementation issues documented in #168 and defines the minimum receipt envelope needed for composed validation evidence.

Validate the registry:

```console
python scripts/validate_scientific_validation_matrix.py
```

Validate a produced gate receipt:

```console
python scripts/validate_scientific_validation_matrix.py --receipt path/to/receipt.json
```

## Evidence discipline

The registry does not mark any family PASS. Execution evidence remains separate.

Every receipt must carry:

- exact repository and commit;
- gate family and L0-L7 evidence level;
- runtime identities;
- mission/execution lineage;
- executed commands and environment;
- start/end/duration;
- explicit result;
- failure reason when FAIL/BLOCKED;
- evidence identifiers;
- explicit external substrate mode: `REAL`, `SIMULATED`, or `NONE`.

```text
SIMULATED != REAL
BLOCKED != FAIL
BLOCKED != PASS
SKIPPED != PASS
NOT_REQUESTED != PASS
ONE_GATE_PASS != COMPOSED_SYSTEM_PASS
```

This registry is validation metadata only and has no product, routing, policy, or Acceptance authority.

## Integration baseline

This branch has been synchronized with current `main@663ad81b4e53665d573487226689a4a48fbd1a1b` without force-push. Exact-head CI evidence must be taken from the post-synchronization PR head.
