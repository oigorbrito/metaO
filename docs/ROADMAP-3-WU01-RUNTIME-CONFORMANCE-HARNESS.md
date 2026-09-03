# Roadmap 3 WU01 — Runtime Conformance Harness V1

## Objective

Make runtime plugability testable before adding more orchestrator frameworks.

Roadmap 2 proved two real runtime SDK paths and a declarative catalog. Roadmap 3 starts by defining a reusable certification harness for the neutral boundary so future runtime integrations do not require bespoke architectural reasoning every time.

## Principle

The harness certifies boundary correctness, not business quality and not current service availability.

A runtime may be temporarily `UNHEALTHY` and still conform to the metaO contract. Conversely, a runtime that returns successful-looking output with broken mission/execution/orchestrator evidence binding is non-conformant.

The harness is an empirical instrument. A claim produced from it is decision-grade only when another engineer can identify the exact subject, protocol, environment, observations, and analysis rule used to obtain that claim.

## Empirical-method constraint

Harness changes and conclusions MUST follow a predeclared comparison protocol. The protocol is frozen before candidate outcomes are inspected. Post-hoc changes are permitted only when recorded as a new protocol version; prior observations remain attached to the protocol under which they were produced.

Required study record:

| Field | Required content |
|---|---|
| Research question | Specific property or comparison being tested. |
| Subject | Runtime/candidate name and immutable commit, tag, digest, or equivalent pin. |
| Baseline | Exact baseline pin and known deviations. |
| Independent variable | Candidate/configuration intentionally varied. |
| Response variables | Exact observed outcomes/metrics and units. |
| Controlled variables | Fixture, workload, policy, timeout, dependency/configuration values held constant. |
| Environment | OS, architecture, runtime/compiler versions, relevant hardware and dependency lock state. |
| Procedure | Executable command(s), ordering, setup, teardown, and repetition count. |
| Raw evidence | Machine-readable output/log/artifact location; summaries are not substitutes. |
| Analysis rule | Predeclared mapping from observations to PASS/FAIL/score. |
| Deviations | Any departure from protocol, including failed or aborted runs. |
| Threats/limitations | Known construct, internal, external, and conclusion-validity limitations where applicable. |

A missing required field does not imply failure of the candidate. It limits the strength of the claim and MUST be represented as `NOT_PROVEN`, `UNKNOWN`, or `BLOCKED` as appropriate.

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

## Reproducibility contract

For every decision-bearing harness execution, preserve enough information to rerun the same protocol without reconstructing hidden context:

```text
PROTOCOL_VERSION = REQUIRED
SUBJECT_PIN = REQUIRED
BASELINE_PIN = REQUIRED_WHEN_COMPARATIVE
FIXTURE_ID_OR_DIGEST = REQUIRED
COMMAND = REQUIRED
ENVIRONMENT_RECORD = REQUIRED
RAW_OUTPUT = REQUIRED
EXIT_STATUS = REQUIRED
START_END_TIMESTAMP = REQUIRED
ANALYSIS_RULE = REQUIRED
DEVIATIONS = REQUIRED_EVEN_IF_NONE
```

Randomized or nondeterministic components, if introduced later, MUST record seeds and all material parameters. Network-backed or mutable external dependencies MUST be pinned, snapshotted, or explicitly classified as a reproducibility limitation.

A rerun that uses a different subject pin, fixture, protocol version, or material environment is a replication/robustness observation, not silently the same run.

## Comparable-candidate rule

Comparative claims require symmetry. Candidate A and candidate B must be evaluated using the same research question, response-variable definitions, fixture semantics, analysis rule, and materially equivalent resource constraints. Candidate-specific setup is allowed only when necessary to exercise the same contracted capability and MUST be disclosed.

Do not infer superiority from:

- README or marketing claims;
- repository popularity, stars, forks, or contributor count;
- presence of a feature not exercised by the protocol;
- a candidate's upstream benchmark when the baseline was not measured under a comparable protocol;
- a single successful run when run-to-run variability is material;
- absence of observed failure when the relevant negative/adversarial condition was not exercised.

## Chain of evidence

Every reported conclusion MUST be traceable in both directions:

```text
CLAIM -> ANALYSIS RULE -> OBSERVATION -> RAW ARTIFACT -> COMMAND/ENVIRONMENT -> SUBJECT PIN
SUBJECT PIN -> COMMAND/ENVIRONMENT -> RAW ARTIFACT -> OBSERVATION -> ANALYSIS RULE -> CLAIM
```

Narrative interpretation may explain evidence but cannot replace it. Failed, inconclusive, and aborted executions are retained rather than removed from the record merely because they weaken a preferred conclusion.

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
- full historical regression remains green when executable CI is available;
- decision-bearing runs include the complete reproducibility record above;
- comparative conclusions identify the raw evidence for every candidate under the same protocol version;
- reruns expose deviations instead of silently overwriting earlier observations.

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
EMPIRICAL_PROTOCOL_REQUIRED = YES
CHAIN_OF_EVIDENCE_REQUIRED = YES
REPRODUCIBILITY_RECORD_REQUIRED = YES
```

## Method basis

This documentation policy is intentionally limited to established empirical-software-engineering and reproducibility principles: predeclared study design and variables, explicit protocol and execution reporting, preservation of a chain of evidence, exact artifact/environment documentation, executable artifacts, and independent rerun/replication where feasible. Project-specific architectural invariants remain metaO requirements; they are not presented as research-community standards.