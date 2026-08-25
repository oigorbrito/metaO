# Roadmap 3 WU01 — Runtime Conformance Harness V1

## Objective

Make runtime plugability testable before adding more orchestrator frameworks.

Roadmap 2 proved two real runtime SDK paths and a declarative catalog. Roadmap 3 starts by defining a reusable certification harness for the neutral boundary so future runtime integrations do not require bespoke architectural reasoning every time.

## Principle

The harness certifies boundary correctness, not business quality and not current service availability.

A runtime may be temporarily `UNHEALTHY` and still conform to the metaO contract. Conversely, a runtime that returns successful-looking output with broken mission/execution/orchestrator evidence binding is non-conformant.

## Active probe

`evaluate_runtime_conformance(...)` executes one explicit caller-supplied probe mission. The caller is responsible for ensuring the probe is safe for that runtime.

V1 validates:

1. structural `OrchestratorContract` compliance;
2. stable descriptor identity/version/capabilities;
3. `HealthReport` boundary shape;
4. `execute()` returns `ExecutionResult`;
5. result execution id binds to the request;
6. result orchestrator id binds to the descriptor;
7. evidence normalizer is callable;
8. normalizer returns `EvidenceEnvelope`;
9. mission/execution/orchestrator/adapter/attempt bindings are exact;
10. required evidence identity/provenance/authority/digest fields are populated.

`assert_runtime_conformant(...)` converts a failed report into `RuntimeConformanceError` while preserving the deterministic report.

## Deliberate non-goals

WU01 does not:

- modify `runtime_factory.py` or runtime admission;
- add a third framework;
- require a runtime to be currently healthy;
- define business-quality benchmarks;
- require immediate hard cancellation semantics from every runtime;
- introduce learned routing or adaptive thresholds;
- import framework SDKs into Core.

Admission gating belongs to a later WU after the WU05 integration line is settled, avoiding unnecessary merge conflicts.

## Required evidence

- conformant fake runtime passes all checks;
- unhealthy-but-contract-correct runtime remains conformant;
- wrong execution binding fails closed;
- wrong orchestrator binding fails closed;
- invalid normalizer output fails closed;
- mis-bound evidence fails closed;
- runtime execution exception becomes a deterministic failed report;
- assert helper preserves failed-check evidence;
- harness remains SDK-neutral;
- full historical regression remains green when executable CI is available.

## Gate

```text
RUNTIME_CONFORMANCE_HARNESS = IMPLEMENTED
ACTIVE_PROBE = YES
EXECUTION_BINDING_CHECK = YES
EVIDENCE_BINDING_CHECK = YES
SDK_NEUTRAL = YES
RUNTIME_FACTORY_CHANGED = NO
THIRD_FRAMEWORK_REQUIRED = NO
CI_EXECUTED = PENDING_HOSTED_RUNNER_AVAILABILITY
```
