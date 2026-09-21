# Empirical Evidence and Reproducibility Protocol

Status: CANONICAL DOCUMENTATION PROTOCOL
Applies to: empirical, benchmarking, validation, qualification, release-evidence, and comparative claims made by metaO
Issue: #431

## 1. Purpose

This document defines the minimum documentation expected when metaO makes an empirical claim about software behavior, capability, performance, reliability, compatibility, recovery, acceptance, or operational evidence.

It does not create a score, maturity index, weighting system, or substitute for the existing capability/evidence taxonomy. Its purpose is narrower: make claims traceable to observations and make the conditions under which those observations were produced sufficiently explicit for independent scrutiny and, where practical, reproduction or replication.

The protocol is grounded in empirical software engineering guidance, principally the ACM SIGSOFT Empirical Standards for Software Engineering, including the General, Engineering Research, Benchmarking, and Replication standards, together with the Open Science supplement and ACM artifact-evaluation concepts.

## 2. Governing principles

### 2.1 Grow by empirical selection, not feature accumulation

metaO must grow by **empirical selection** rather than by feature accumulation, architectural preference, donor popularity, or speculative inclusion.

A capability, abstraction, dependency, strategy, optimization, or architectural mechanism is a candidate hypothesis until comparative evidence justifies its promotion.

The default progression is:

```text
BASELINE
-> ISOLATED_CANDIDATE_CHANGE
-> PREDECLARED_COMPARABLE_EVALUATION
-> RAW_EVIDENCE
-> BOUNDED_INTERPRETATION
-> PROMOTE_OR_REJECT
```

The following rules apply:

- preserve the smallest executable baseline that can answer the research question;
- introduce candidate capabilities in a removable or replaceable form whenever practical;
- define the relevant workload, measurements, acceptance criteria, and decision rule before observing the deciding result;
- compare the candidate against the baseline under a common measurement boundary;
- measure gains together with regressions, resource cost, complexity, and operational overhead when they are material;
- retain negative, neutral, blocked, and contradictory outcomes;
- promote a candidate into the permanent core only when the evidence supports that promotion;
- reject, remove, or keep optional a candidate whose benefit is not demonstrated strongly enough for the declared decision rule;
- do not preserve complexity merely because implementation effort has already been spent.

The governing invariants are:

```text
COMPLEXITY_MUST_EARN_THE_RIGHT_TO_REMAIN
FEATURE_EXISTS != FEATURE_SHOULD_BE_CORE
POPULAR_DONOR != EMPIRICALLY_SELECTED_DONOR
PROMISING_DESIGN != MEASURED_IMPROVEMENT
ABSENCE_OF_REGRESSION != DEMONSTRATED_BENEFIT
EMPIRICAL_SELECTION > FEATURE_ACCUMULATION
```

This principle applies equally to chassis selection, donor adoption, supervisor/executor strategies, decomposition/composition mechanisms, context-management policies, verifiers, adapters, runtimes, and optimizations.

The objective is not the system with the most capabilities. The objective is the **smallest maintainable system that retains the capabilities whose value is supported by traceable empirical evidence for the intended workload**.

### 2.2 Evidence must be bound to a claim

Every empirical PASS, FAIL, BLOCKED, NOT_TESTED, or equivalent conclusion must identify the claim being evaluated and the evidence used to support that conclusion.

A result must not be promoted merely because implementation exists, a test file exists, or a command completed.

Existing metaO invariants remain authoritative:

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

### 2.3 Observations, analysis, and interpretation are distinct

Documentation should distinguish, where applicable:

1. **raw observations** — emitted measurements, logs, exit codes, traces, artifacts, test results, timestamps, or provider responses;
2. **derived analysis** — transformations, aggregations, comparisons, classifications, or statistical calculations applied to observations;
3. **interpretation** — the engineering conclusion drawn from those observations and analyses.

A conclusion must not obscure the underlying evidence from which it was derived.

### 2.4 Exact identity matters

Empirical evidence should identify the exact evaluated artifact or candidate whenever practical. For repository-based evaluation this normally includes:

- repository identity;
- branch or ref when relevant;
- exact commit SHA;
- package/runtime/tool versions relevant to the claim;
- test, benchmark, script, or protocol identity;
- configuration that can materially affect the result.

Evidence from an older candidate must not be silently represented as evidence for current HEAD.

### 2.5 Reproducibility is conditional on disclosed context

A result cannot be meaningfully reproduced if material execution conditions are hidden. Therefore, the environment relevant to the claim should be documented, including applicable items such as:

- operating system and version;
- architecture;
- language/runtime version;
- dependency versions or lockfile identity;
- external service/provider identity and version where observable;
- hardware characteristics when they can affect the result;
- environment variables or configuration classes, excluding secrets;
- network or infrastructure conditions when they are material;
- clock/time constraints when they are material.

Only context variables that may influence the result need to be recorded; irrelevant inventory is not required.

## 3. Required empirical record

For an empirical claim, record the following fields when applicable.

### 3.1 Objective or claim

State what is being evaluated in falsifiable or observable terms.

Preferred form:

```text
CLAIM: <observable proposition>
```

Avoid replacing an observable claim with a broad label such as "ready", "good", or "robust" unless those labels have an explicit operational definition elsewhere.

### 3.2 Unit of analysis or evaluated subject

Identify the object to which the result applies, for example:

- exact build or commit;
- runtime adapter;
- orchestrator/runtime/version tuple;
- workflow;
- release artifact;
- benchmark subject;
- external provider interaction.

### 3.3 Protocol or procedure

Document enough of the procedure to understand how the evidence was produced. This may be a direct command, executable script, benchmark specification, CI workflow, test selector, or versioned protocol document.

The procedure should make clear:

- inputs;
- setup/preconditions;
- execution steps;
- termination conditions;
- acceptance/failure conditions;
- relevant cleanup/reset steps where state could affect later runs.

### 3.4 Environment and dependencies

Record material environment information as defined in Section 2.4.

### 3.5 Raw evidence location

Where practical, preserve non-aggregated evidence rather than only a summary.

Examples include:

- machine-readable JSON results;
- test result files;
- benchmark samples;
- logs;
- traces;
- generated manifests;
- provider response classifications;
- CI artifacts.

If raw evidence cannot be retained or released, state why.

### 3.6 Derived analysis

If the conclusion depends on transformation or aggregation, identify the analysis method or script and preserve enough information to recompute it when practical.

Avoid retaining only averages or final summaries when individual observations are necessary to evaluate variability or stability.

### 3.7 Result

Record the observed outcome without expanding the scope beyond what the protocol measured.

### 3.8 Limitations and threats to validity

Document known conditions that constrain interpretation, including applicable threats to:

- construct validity — whether the measurement actually represents the intended property;
- internal validity — whether another factor may explain an observed effect;
- external validity — whether the result generalizes beyond the evaluated subjects/context;
- conclusion validity — whether the analysis supports the conclusion;
- reliability/reproducibility — whether repeated execution may yield materially different observations.

The presence of a limitation does not automatically invalidate a result. It limits the scope of the supported claim.

## 4. Stochasticity and repetitions

When the evaluated system, workload, runtime, provider, scheduler, algorithm, network, or environment contains a material source of stochasticity or nondeterminism:

1. identify known or plausible sources of stochasticity;
2. state whether random seeds or equivalent controls exist and how they were handled;
3. execute multiple repetitions when needed to assess stability;
4. retain per-run observations where practical;
5. report the number of repetitions;
6. justify a single-run design when multiple repetitions are impractical or unnecessary for the claim.

The protocol does not prescribe a universal repetition count. The appropriate number depends on the phenomenon, variability, cost, and prior evidence. Arbitrary fixed counts must not be presented as a general scientific rule.

For deterministic checks whose outcome is defined by exact input and exact software state, repetition may add little information. That rationale should be apparent from the protocol.

## 5. Benchmarking-specific documentation

When a metaO claim is based on benchmarking, additionally document:

- why the benchmark represents the property under study;
- benchmark/workload identity and version;
- subject selection and any inclusion/exclusion criteria;
- configuration and warm-up behavior where material;
- repetitions or duration sufficient to examine stability where required;
- raw measurements rather than only aggregated summaries where practical;
- any known benchmark tailoring that could favor one candidate.

A benchmark should not be presented as broadly representative if its workload or subjects only cover a narrower domain.

## 6. Comparative evaluation

When comparing metaO, a runtime, adapter, donor, implementation, or candidate against an alternative:

- identify the alternative and exact version/state;
- use the same measurement definitions across candidates unless a difference is justified;
- document materially different configurations;
- avoid tuning the evaluation solely to favor one candidate;
- preserve per-candidate evidence;
- distinguish observed differences from explanations for those differences.

If direct comparison is impractical, document the reason rather than implying that a comparison was performed.

## 7. Reproduction and replication terminology

This repository adopts the ACM SIGSOFT Replication standard terminology for formal empirical claims:

- **reproduction** means repeating the original study's data analysis on the original study's data;
- **replication** means repeating a study by collecting new data and repeating the original study's analysis on the new data.

When a metaO engineering evaluation re-runs the same executable procedure on the same software/artifact state but does not satisfy the definition above, describe it more precisely as a **repeat execution**, **re-execution**, or **artifact re-run** rather than calling it a formal reproduction.

When a document uses reproduction or replication as a formal evidence claim, it must identify the original study/evaluation and state what data, analysis, protocol, subjects, and context were held constant or changed.

Do not use `reproducible`, `replicated`, or equivalent terms merely to mean that code compiled or tests once passed.

## 8. Minimum reproducibility package

For empirical claims that are intended to be independently checked, the repository should preserve or reference, where applicable:

- exact source revision or release artifact;
- protocol/commands/scripts;
- relevant configuration;
- dependency/runtime identity;
- material environment description;
- raw observations;
- analysis scripts or transformation description;
- expected output or acceptance criteria;
- known limitations;
- license/access information for releasable supporting artifacts.

A package need not contain items that are irrelevant to the claim.

If an artifact cannot be preserved or disclosed for legal, security, privacy, provider, cost, size, or other practical reasons, record the omission and its reason. Missing evidence must not be silently substituted with a stronger claim.

## 9. Mapping to metaO evidence levels

This protocol does not redefine the canonical L0-L7 taxonomy in `POST-MVP-OPERATIONAL-BASELINE-V1.md` and `CAPABILITY-MAP.md`.

Instead, it constrains how claims at evidence-bearing levels are documented.

```text
L0 CONCEPT_ONLY       -> no empirical claim implied
L1 SPECIFIED          -> protocol/expected behavior may exist; execution not implied
L2 IMPLEMENTED        -> implementation exists; empirical execution not implied
L3 WIRED              -> integration path exists; empirical success not implied
L4 FOCUSED_TESTED     -> focused executed evidence must identify candidate/procedure/result
L5 REGRESSION_TESTED  -> regression evidence must identify candidate/suite/result
L6 INTEGRATION_TESTED -> integration evidence must identify participating components and context
L7 OPERATIONAL_EVIDENCE -> operational claim must identify the real execution context and its limitations
```

Operational dimensions such as `MULTIPROCESS`, `REAL_RUNTIME`, `REAL_EXTERNAL_SYSTEM`, `FAULT_INJECTION`, `ADVERSARIAL`, and `HOSTED_CI` must be treated as descriptions of the evidence context, not as interchangeable claims.

For example:

```text
SIMULATED_PROVIDER_PASS != REAL_EXTERNAL_SYSTEM_PASS
LOCAL_PASS != HOSTED_CI_PASS
UNIT_PASS != INTEGRATION_PASS
OLD_SHA_PASS != CURRENT_HEAD_PASS
```

## 10. Evidence status vocabulary

Use status words conservatively.

### PASS

The defined acceptance condition was observed under the documented protocol and context.

### FAIL

The defined acceptance condition was executed and not satisfied.

### BLOCKED

The intended evaluation could not reach the required observation because a documented blocking condition prevented it.

### NOT_TESTED

No qualifying execution evidence exists for the stated claim.

### NOT_APPLICABLE

The criterion does not apply to the evaluated subject, with rationale documented.

A blocker outside metaO may be valid evidence about the environment while remaining neither PASS nor FAIL evidence about metaO product behavior.

## 11. Claim-boundary rule

The supported claim must not exceed the evaluated scope.

Examples:

```text
one provider authentication failure observed
!=
provider failover proven

local release gate PASS
!=
hosted CI PASS

single workload benchmark PASS
!=
general scalability established

unit/regression suite PASS
!=
production readiness
```

Broader conclusions require broader evidence or an explicit statement that they remain untested.

## 12. Evidence preservation and openness

Where legally and practically possible, empirical artifacts should be preserved in a stable, accessible form. For repository-internal engineering evidence, version control plus durable CI/release artifacts may be sufficient when they retain the material required to inspect or re-run the claim.

For externally published research packages, prefer preserved repositories/archives appropriate to open-science practice and include clear reuse licensing where possible.

Private, secret, proprietary, unsafe, excessively large, or externally controlled material need not be published merely to satisfy this protocol. The omission and its consequence for reproducibility should be documented.

## 13. Documentation checklist

Before presenting an empirical claim as accepted evidence, verify:

- [ ] claim is observable and bounded;
- [ ] evaluated subject is identified;
- [ ] exact candidate/version is recorded where applicable;
- [ ] protocol or executable procedure is identified;
- [ ] material environment/context is recorded;
- [ ] known stochasticity is identified;
- [ ] repetitions are reported or their absence justified when applicable;
- [ ] raw observations are preserved or omission is explained;
- [ ] analysis is distinguishable from raw observations;
- [ ] acceptance/failure criteria are explicit;
- [ ] limitations/threats to validity are stated where material;
- [ ] result status is one of PASS / FAIL / BLOCKED / NOT_TESTED / NOT_APPLICABLE or an explicitly defined equivalent;
- [ ] conclusion does not exceed the evaluated scope;
- [ ] evidence is bound to the exact authoritative repository/artifact state where applicable.

This checklist is a documentation aid, not a numerical score. Items marked not applicable should have a reason when the omission could otherwise affect interpretation.

## 13.1 Architecture incorporation strategy

Architecture and donor-incorporation decisions that depend on this protocol must also follow:

- `docs/ADR-2026-09-21-CONTROLLED-FORK-PARTIAL-DONOR-MIGRATION.md` — controlled fork of the empirically selected chassis, preservation of upstream traceability, partial migration of donor capabilities, redundancy/divergence classification, removability, and local promotion by comparative evidence.

This reference does not authorize a chassis winner or product migration. It defines how externally validated capabilities are incorporated once the applicable architecture gate authorizes that work.

## 14. References

Primary methodological basis:

1. ACM SIGSOFT Empirical Standards for Software Engineering.
   https://www2.sigsoft.org/EmpiricalStandards/
2. ACM SIGSOFT Empirical Standards — Standards, including General, Engineering Research, Benchmarking, and Replication.
   https://www2.sigsoft.org/EmpiricalStandards/docs/standards
3. ACM SIGSOFT Empirical Standards — Open Science supplement.
   https://www2.sigsoft.org/EmpiricalStandards/docs/supplements
4. ACM Artifact Review and Badging policy.
   https://www.acm.org/publications/policies/artifact-review-and-badging-current

## 15. Non-goals

This document intentionally does not:

- define arbitrary numeric evidence scores;
- assign weights to quality dimensions;
- claim that every engineering test is a scientific experiment;
- require statistical analysis for deterministic properties where it is not methodologically justified;
- require public disclosure of secrets, credentials, proprietary data, or unsafe artifacts;
- turn passing tests into claims of production readiness;
- replace architecture, requirements, capability, verification/validation, release, or security documentation.

Its role is to make empirical claims auditable, bounded, and reproducible to the extent supported by the evaluated phenomenon and available artifacts.
