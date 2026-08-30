# Formal model evidence boundary

This directory contains bounded specification models used as scientific/test evidence for metaO control-plane invariants.

## AcceptanceRetryAuthority

Owner: #302, parent #161.

The model intentionally excludes runtime SDKs, provider topology, agents, tools and transport details. It models only authority-relevant state for one critical slice:

- execution generation/lineage;
- runtime DONE observation;
- evidence generation/freshness;
- independent verifier result;
- recovery/retry eligibility;
- failover generation change;
- terminal metaO decision.

### Invariants

- `OrchestratorDoneIsNotAcceptance`
- `AcceptedRequiresIndependentFreshPass`
- `BlockedRequiresIndependentFreshFail`
- `StaleEvidenceCannotAcceptCurrentGeneration`
- `IncompleteRecoveryCannotEnableRetry`
- `UnknownNeverAccepts`
- `OldGenerationDoneCannotAcceptCurrent`
- `AcceptedGenerationMatchesCurrent`

Both terminal decisions are bound to fresh evidence for the current execution generation. A stale/old-generation verifier result cannot mint either `ACCEPTED` or `BLOCKED` for the current generation.

### Claim boundary

```text
MODEL_VERSIONED != MODEL_CHECKED
TLC_PASS != IMPLEMENTATION_PROOF
MODEL_INVARIANT != RUNTIME_ENFORCEMENT
```

`AcceptanceRetryAuthority.cfg` bounds `MaxGeneration = 3`. A real TLC execution must be recorded before any MODEL_CHECKED claim. Any counterexample must be retained as evidence and translated into a deterministic implementation regression test when it exposes a real implementation/specification defect.

Current executable status: `TLC = NOT_RUN`.
