# Roadmap 3 WU01 — Runtime Conformance Harness V1

## Objective

Make runtime plugability testable before adding more orchestrator frameworks.

Roadmap 2 proved two real runtime SDK paths and a declarative catalog. Roadmap 3 starts by defining a reusable certification harness for the neutral boundary so future runtime integrations do not require bespoke architectural reasoning every time.

## Principle

The harness certifies boundary correctness, not business quality and not current service availability.

A runtime may be temporarily `UNHEALTHY` and still conform to the metaO contract. Conversely, a runtime that returns successful-looking output with broken mission/execution/orchestrator evidence binding is non-conformant.

The harness is an empirical instrument. A claim produced from it is decision-grade only when another engineer can identify the exact subject, protocol, material environment, observations, analysis rule, and limitations relevant to that claim.

The canonical documentation authority for empirical claims is `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.

## Empirical-method constraint

Claim-bearing harness executions MUST use an explicit, versioned protocol before their observations are interpreted as evidence. The amount of study-design metadata required depends on the kind of empirical claim being made.

A deterministic conformance check is not automatically an experiment, benchmark, or comparative study. Baselines, independent variables, controlled variables, repetitions, and statistical analysis are required only when the selected empirical design makes them material to the claim.

### Universal claim record

For every decision-bearing harness claim, record when applicable:

| Field | Required content |
|---|---|
| Claim / research question | Specific observable property or proposition being evaluated. |
| Subject | Runtime/candidate name and immutable commit, tag, digest, version, or equivalent identity. |
| Protocol | Versioned procedure, command, script, or test selector used to produce the observation. |
| Fixture/input | Fixture identity, digest, workload, mission, or other material input. |
| Environment | Material OS, architecture, runtime/compiler, dependency, hardware, provider, or infrastructure context. |
| Raw evidence | Machine-readable output/log/artifact location where practical; omission must be explained when material. |
| Analysis rule | Mapping from observations to the reported result. |
| Result | PASS/FAIL/BLOCKED/NOT_TESTED/NOT_APPLICABLE or explicitly defined equivalent. |
| Deviations | Material departure from the documented procedure, if any. |
| Threats/limitations | Known construct, internal, external, conclusion, reliability, or reproducibility limitations where material. |

### Conditional study-design fields

Add these only when the claim/design makes them applicable:

| Field | Applicability |
|---|---|
| Baseline/comparator | Comparative or differential claim. |
| Independent variable | Experiment or controlled comparison with an intentionally varied factor. |
| Response variables / metrics | Benchmark, quantitative comparison, performance, reliability, cost, or other measured outcome. |
| Controlled variables | When confounding by fixture/configuration/environment is material to the inference. |
| Inclusion/exclusion criteria | Sample, workload, repository, subject, or dataset selection can affect interpretation. |
| Repetition count | Stochastic/nondeterministic systems or when run-to-run variability is material. |
| Seed/randomness controls | Randomized procedure or subject. |
| Statistical/aggregation method | The conclusion depends on aggregation, uncertainty, significance, effect size, or other quantitative analysis. |

A missing applicable field does not imply failure of the candidate. It limits the strength of the supported claim and MUST be represented conservatively.

## Documentary-suggestion eligibility

The harness may suggest a documentary improvement only when all of the following are true:

1. a specific empirical or reproducibility criterion is identifiable;
2. that criterion is applicable to the actual claim type or evaluation design;
3. the current documentation materially lacks information needed by that criterion;
4. the proposed change is limited to closing that documentation/evidence gap;
5. the suggestion identifies its methodological basis, preferably through the canonical empirical protocol section and, where useful, the underlying research/artifact-evaluation guidance.

Use this minimum suggestion record:

```text
DOCUMENTARY_SUGGESTION
  target_document: <path/claim>
  observed_gap: <missing or ambiguous evidence information>
  applicable_criterion: <criterion>
  methodological_basis: <canonical section / external guide>
  applicability_rationale: <why this criterion applies here>
  proposed_documentary_change: <bounded change>
  claim_effect: <what stronger wording becomes supportable, or "no claim upgrade">
```

The harness MUST NOT present the following as empirical-method requirements unless a cited, applicable methodological criterion supports them:

- new product features or architecture;
- preferred implementation patterns;
- arbitrary numeric thresholds, scores, or weights;
- mandatory baselines for non-comparative deterministic checks;
- mandatory repetition counts independent of observed/plausible variability;
- mandatory statistical tests for deterministic properties;
- project-specific authority or security invariants masquerading as research-community standards;
- generic “best practice” recommendations without a traceable methodological basis.

If a potentially useful change is only an engineering preference, architecture concern, or product-risk mitigation, classify it outside the empirical-documentation suggestion channel.

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

For every decision-bearing harness execution, preserve enough information to independently inspect or repeat the executable procedure without reconstructing hidden material context:

```text
PROTOCOL_VERSION = REQUIRED
SUBJECT_PIN = REQUIRED_WHEN_PINNABLE
FIXTURE_ID_OR_DIGEST = REQUIRED_WHEN_MATERIAL
COMMAND_OR_PROCEDURE = REQUIRED
MATERIAL_ENVIRONMENT_RECORD = REQUIRED
RAW_OUTPUT_OR_OMISSION_REASON = REQUIRED_WHEN_MATERIAL
EXIT_STATUS_OR_RESULT = REQUIRED
ANALYSIS_RULE = REQUIRED
LIMITATIONS = REQUIRED_WHEN_MATERIAL
```

`BASELINE_PIN` is required for comparative claims, not for every conformance execution. Start/end timestamps, resource measurements, repetition counts, seeds, and per-run observations are required when they are material to interpreting or repeating the claim rather than as unconditional inventory.

Randomized or nondeterministic components MUST disclose material randomness controls and use repetitions when needed to characterize stability. Network-backed or mutable external dependencies must be pinned, snapshotted, identified, or explicitly classified as a reproducibility limitation when their mutability can affect the result.

A repeat execution on the same artifact/procedure is an artifact rerun or repeat execution unless it satisfies the repository's formal reproduction/replication definitions. Do not label a different candidate, new dataset, changed fixture, or changed environment as a formal `replication` merely because it reruns related code. Formal terminology follows `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.

## Comparable-candidate rule

Comparative claims require symmetry. Candidate A and candidate B must be evaluated using the same claim/measurement definitions, materially comparable fixture semantics, analysis rule, and relevant resource constraints, unless a difference is justified and disclosed.

Do not infer superiority from:

- README or marketing claims;
- repository popularity, stars, forks, or contributor count;
- presence of a feature not exercised by the protocol;
- a candidate's upstream benchmark when the baseline was not measured under a comparable protocol;
- a single successful run when run-to-run variability is material;
- absence of observed failure when the relevant negative/adversarial condition was not exercised.

## Chain of evidence

Every reported conclusion SHOULD remain traceable through the material evidence chain applicable to the claim:

```text
CLAIM -> ANALYSIS RULE -> OBSERVATION -> RAW ARTIFACT/RECORD -> PROCEDURE/ENVIRONMENT -> SUBJECT
```

Narrative interpretation may explain evidence but cannot replace it. Failed, inconclusive, and aborted executions that materially affect interpretation are retained or accounted for rather than silently removed.

## Deliberate non-goals

WU01 does not:

- modify `runtime_factory.py` or runtime admission;
- add a third framework;
- require a runtime to be currently healthy;
- define business-quality benchmarks;
- require immediate hard cancellation semantics from every runtime;
- introduce learned routing or adaptive thresholds;
- import framework SDKs into Core;
- convert engineering preferences into empirical-research requirements.

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
- decision-bearing claims include the applicable reproducibility record;
- comparative conclusions identify evidence for every candidate under a materially comparable protocol;
- material deviations are exposed instead of silently overwriting earlier observations;
- documentary suggestions include an applicable methodological criterion and do not create unsupported product/architecture requirements.

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
APPLICABILITY_AWARE_STUDY_RECORD = YES
REPRODUCIBILITY_RECORD_REQUIRED = YES
DOCUMENTARY_SUGGESTION_METHOD_BASIS_REQUIRED = YES
UNSUPPORTED_EMPIRICAL_BEST_PRACTICE_SUGGESTIONS = FORBIDDEN
```

## Method basis

This documentation policy is intentionally limited to established empirical-software-engineering and reproducibility principles and applies them according to study/claim type rather than treating every harness execution as a controlled experiment.

Primary basis:

- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md` (canonical repository protocol);
- ACM SIGSOFT Empirical Standards for Software Engineering and its General, Engineering Research, Benchmarking, Replication, and Open Science guidance;
- ACM Artifact Review and Badging concepts for documented, consistent, complete, exercisable artifacts and evidence of verification/validation;
- established empirical-software-engineering guidance on reporting study design, context, procedure, validity limitations, and reproducibility.

Project-specific architectural, authority, safety, or product invariants remain metaO requirements. They are not presented as research-community standards merely because the harness evaluates them.
