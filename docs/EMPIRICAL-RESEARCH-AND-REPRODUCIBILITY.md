# Empirical Research and Reproducibility Contract

Status: SUPERSEDED_FOR_FORMAL_REPRODUCTION_AND_REPLICATION_TERMINOLOGY
Applies to: evidence-bearing research, comparison, benchmark, donor evaluation, chassis evaluation, conformance harnesses, and architecture claims in `oigorbrito/metaO`

## Supersession notice

Formal use of **reproduction**, **replication**, **reproduced**, **replicated**, and related terminology is governed exclusively by `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`, which adopts the ACM SIGSOFT Replication standard.

This document remains a reference for non-conflicting historical and domain-specific empirical practices. Existing observations, results, experiment artifacts, decisions, and historical classifications are not rewritten by this supersession.

## Purpose

This document governs how metaO collects, records, compares, interprets, and promotes empirical evidence used in engineering decisions.

It does not define product architecture, architecture weights, language preference, donor preference, or acceptance authority. Those remain owned by their existing canonical contracts and ADRs.

The governing principle is:

```text
ENGINEERING_DECISION_REQUIRES_TRACEABLE_EVIDENCE
METHODOLOGY_DOES_NOT_PREDETERMINE_ARCHITECTURE
```

## Scope of methodological authority

Methodological rules may be introduced only when they improve one or more of:

- traceability from claim to observation;
- reproducibility of an execution or measurement;
- comparability between candidates;
- transparency of uncertainty, limitations, exclusions, and deviations;
- resistance to selective reporting or post-hoc criterion changes.

A methodological rule must not silently alter a frozen product criterion, hard gate, score weight, architecture invariant, or previously recorded result.

## Evidence ladder

Use the following evidence progression consistently:

```text
DOCUMENTED
< CODE_CONFIRMED
< TEST_CONFIRMED_UPSTREAM
< EXECUTED_IN_METAO_FIXTURE
< MEASURED_IN_COMPARABLE_METAO_FIXTURE
```

A higher evidence level increases confidence in a claim. It does not automatically improve the engineering score or disposition of a candidate.

The following implications are invalid:

```text
DOCUMENTED == EXECUTED
CODE_CONFIRMED == TEST_CONFIRMED
TEST_CONFIRMED == MEASURED
PAPER_RESULT == METAO_RESULT
BENCHMARK_PASS == METAO_ACCEPTED
ABSENCE_OF_EVIDENCE == EVIDENCE_OF_ABSENCE
```

## Minimum claim-to-evidence contract

Any material claim used to justify selection, rejection, adaptation, promotion, comparative superiority, or architecture change must preserve the applicable fields below:

```text
CLAIM_ID:
RESEARCH_QUESTION:
SUBJECT:
PIN_OR_VERSION:
UNIT_OF_ANALYSIS:
SELECTION_RATIONALE:
EVIDENCE_GRADE:
CODE_OR_DOC_POINTERS:
EXECUTION_COMMANDS:
FIXTURE_OR_INPUT:
ENVIRONMENT:
RAW_ARTIFACT_POINTERS:
OBSERVED_RESULT:
INTERPRETATION:
LIMITATIONS:
DEVIATIONS:
REPRODUCIBILITY_STATUS:
DECISION_OR_DISPOSITION_IMPACT:
```

Fields that do not apply may be marked `N/A` with a reason. Missing metadata must not be invented.

## Historical reproducibility vocabulary — superseded for formal claims

The vocabulary below is retained only as historical context for existing records. It must not be used as current formal reproduction/replication terminology; current formal claims follow `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.

Use these terms narrowly:

- **repeatable** — the same team can repeat the recorded procedure and obtain a materially equivalent result;
- **reproduced** — an independent execution using the recorded artifacts/procedure obtains a materially equivalent result;
- **replicated** — an independently constructed evaluation of the same claim reaches a materially consistent conclusion;
- **not reproduced** — an attempted reproduction did not obtain a materially equivalent result and requires diagnosis;
- **not reproducible from available artifacts** — the evidence package is insufficient to perform the attempt.

These labels describe evidence status, not intrinsic product quality.

## Reproducible execution requirements

For executed evidence, record where applicable:

1. immutable subject pin or exact artifact version;
2. operating system and architecture;
3. language/runtime/toolchain versions;
4. dependency resolution state or lockfile identity;
5. command lines and configuration;
6. fixture/input identity;
7. seed when stochastic behavior exists;
8. timeout, retry, concurrency, and warm/cold-start policy when material;
9. raw outputs or immutable artifact pointers;
10. expected outcome and observed outcome;
11. deviations from the predeclared procedure.

A PASS without sufficient execution metadata may remain useful operationally, but it must not be promoted to a stronger reproducibility claim.

## Comparable measurement requirements

Comparative claims such as `faster`, `cheaper`, `lower token use`, `smaller`, `more reliable`, `less memory`, or `lower trusted surface` require a common measurement boundary or an explicitly justified normalization.

Keep constant, or explicitly account for, material factors including:

- task/scenario and expected result;
- semantic slice and acceptance criteria;
- input/context size;
- model/provider/version/configuration for LLM-mediated work;
- runtime/toolchain versions;
- retry, timeout, and concurrency policy;
- measurement units and boundary;
- warm/cold state;
- sample count and aggregation rule;
- inclusion/exclusion rule for observations.

When material factors differ, classify the result as a case-specific observation rather than a general candidate ranking.

## Variable and stochastic measurements

For phenomena with material variability:

- do not characterize a single run as a stable estimate;
- predeclare or record the repetition count and aggregation rule;
- retain all valid observations or a declared exclusion rule;
- report dispersion when decision-relevant;
- do not rerun until a favorable result appears and report only that result.

LLM token/cost measurements must additionally record model/provider/version where available, prompt/context boundary, tool-call boundary, cache assumptions, and whether deterministic GitHub/API work was performed inside or outside the model-mediated path.

## Negative and contradictory evidence

Negative, failed, blocked, and contradictory results are part of the evidence record.

```text
BLOCKED != FAIL
UNKNOWN != PASS
NOT_PROVEN != PASS
FAILED_REPRODUCTION != AUTOMATIC_DONOR_INVALIDATION
```

A blocked execution must name the blocker. A failure must preserve enough evidence for causal diagnosis. Contradictory results must not be discarded merely because they weaken the preferred interpretation.

## Anti-bias and anti-selective-reporting rules

Decision-bearing research must satisfy:

```text
CHANGE_CRITERION_AFTER_RESULT_WITHOUT_RECORD = NO
RERUN_UNTIL_PASS_AND_REPORT_ONLY_PASS = NO
DROP_NEGATIVE_RESULT_WITHOUT_DECLARED_REASON = NO
SUBSTITUTE_README_CLAIM_FOR_EXECUTED_EVIDENCE = NO
SUBSTITUTE_STAR_COUNT_FOR_ENGINEERING_EVIDENCE = NO
GENERALIZE_ONE_FIXTURE_TO_ALL_WORKLOADS = NO
INFER_CAUSALITY_FROM_UNCONTROLLED_ASSOCIATION = NO
```

If a criterion, fixture, instrumentation method, or interpretation changes after results are observed, retain the original result and document the change, reason, and effect on prior conclusions.

## Predeclaration and frozen criteria

When a comparison can affect architecture selection or promotion:

- define decision criteria before observing the deciding measurements whenever practical;
- freeze hard gates and weights before candidate outcomes are interpreted;
- record any post-observation change explicitly;
- do not silently backfit a metric to favor a candidate;
- use sensitivity analysis when the governing comparison contract requires it.

Predeclaration reduces researcher degrees of freedom; it does not prevent justified protocol corrections. Corrections must preserve the original observation and record why the protocol changed.

## Claim strength rule

The wording of a conclusion must not exceed the evidence.

Examples:

```text
ONE_FIXTURE_PASS -> "passed this fixture"
MULTIPLE_COMPARABLE_RUNS -> may support a bounded comparative statement
UPSTREAM_TEST_EXISTS -> "upstream test-confirmed at pin"
CODE_INSPECTION_ONLY -> "code-confirmed", not "proven in execution"
TOOLCHAIN_BLOCKER -> "blocked", not "failed"
```

Architecture decisions may combine multiple bounded observations, but the decision rationale must distinguish observed facts, measurements, inferences, and unresolved hypotheses.

## Artifact retention

For decision-bearing experiments, retain where feasible:

- exact source pins;
- scripts or commands;
- fixture definitions;
- raw measurement outputs;
- generated summaries;
- environment metadata;
- issue/PR/run identifiers;
- known instrumentation defects and their corrections.

A summary table without recoverable underlying evidence is weaker than the same table with traceable raw artifacts.

## Relationship to existing metaO documents

This document owns empirical-method and reproducibility rules only, except that formal reproduction/replication terminology is superseded as stated above.

Existing documents retain their domains:

- `docs/ACCEPTANCE-CONTRACT.md` — acceptance authority and semantics;
- `docs/CHASSIS-SCORECARD-SCHEMA-2026-08-26.md` — frozen chassis hard gates, weights, status vocabulary, and scoring contract;
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md` — donor research outcomes and dispositions;
- `docs/ROADMAP-3-WU01-RUNTIME-CONFORMANCE-HARNESS.md` — runtime conformance harness scope and evidence requirements;
- ADRs — recorded architecture decisions and their historical evidence state.

If a local document contains a stricter domain-specific evidence requirement that does not conflict with this contract, the stricter requirement applies.

## Final methodological invariants

```text
CLAIM_WITHOUT_TRACEABLE_EVIDENCE = WEAK_CLAIM
PINNED_EVIDENCE > FLOATING_REFERENCE
RAW_ARTIFACT > SUMMARY_ONLY
COMPARABLE_MEASUREMENT > CROSS_CONTEXT_NUMBER_COMPARISON
NEGATIVE_RESULT = EVIDENCE
BLOCKED != FAIL
REPRODUCIBILITY_STATUS != PRODUCT_QUALITY
METHODOLOGY_DOES_NOT_MINT_ARCHITECTURE_AUTHORITY
```
