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
- terminal acceptance authority for this bounded slice.

Hard policy/trust/binding `BLOCK` causes are intentionally outside this model. The canonical Rust acceptance contract distinguishes ordinary verifier/obligation failure from a hard block: failed obligation evidence remains `NotDone`, while policy/trust/binding violations may produce `Block`. The model therefore must not promote `verifierState = "FAIL"` into a generic terminal `BLOCKED` state.

### Invariants

- `OrchestratorDoneIsNotAcceptance`
- `AcceptedRequiresIndependentFreshPass`
- `StaleEvidenceCannotAcceptCurrentGeneration`
- `IncompleteRecoveryCannotEnableRetry`
- `UnknownNeverAccepts`
- `VerifierFailNeverAccepts`
- `OldGenerationDoneCannotAcceptCurrent`
- `AcceptedGenerationMatchesCurrent`

### Claim boundary

```text
MODEL_VERSIONED != MODEL_CHECKED
TLC_PASS != IMPLEMENTATION_PROOF
MODEL_INVARIANT != RUNTIME_ENFORCEMENT
VERIFIER_FAIL != HARD_POLICY_BLOCK
```

`AcceptanceRetryAuthority.cfg` bounds `MaxGeneration = 3`. A real TLC execution must be recorded before any MODEL_CHECKED claim. Any counterexample must be retained as evidence and translated into a deterministic implementation regression test when it exposes a real implementation/specification defect.

Current executable status: `TLC = NOT_RUN`.
