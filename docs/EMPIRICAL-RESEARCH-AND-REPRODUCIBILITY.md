# Empirical Research and Reproducibility Contract

Status: SUPPLEMENTAL_METHOD_GUIDANCE — FORMAL REPRODUCTION/REPLICATION TERMINOLOGY SUPERSEDED
Applies to: evidence-bearing research, comparison, benchmark, donor evaluation, chassis evaluation, conformance harnesses, and architecture claims in `oigorbrito/metaO`
Issue: #433

## Authority notice

The current normative protocol for empirical evidence documentation and formal reproduction/replication terminology is:

- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`

This document remains as supplemental methodological guidance for decision traceability, comparative measurement, anti-selective-reporting controls, and predeclaration/frozen-criterion discipline where those rules do not conflict with the normative protocol or a stricter domain-specific contract.

The historical definitions of `reproduced` and `replicated` formerly contained here are superseded. Formal claims must use the ACM SIGSOFT Replication terminology adopted by `EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`:

- **reproduction**: repeat the original study's data analysis on the original study's data;
- **replication**: collect new data and repeat the original study's analysis on the new data.

Engineering re-runs that do not meet those definitions should be described as repeat execution, re-execution, or artifact re-run.

This reconciliation does not rewrite historical observations, dispositions, architecture decisions, score weights, hard gates, or acceptance authority.

## Purpose

This supplemental document governs how metaO records, compares, interprets, and promotes empirical evidence used in engineering decisions, subject to the normative protocol above.

It does not define product architecture, architecture weights, language preference, donor preference, or acceptance authority. Those remain owned by their existing canonical contracts and ADRs.

```text
ENGINEERING_DECISION_REQUIRES_TRACEABLE_EVIDENCE
METHODOLOGY_DOES_NOT_PREDETERMINE_ARCHITECTURE
```

## Scope of supplemental methodological guidance

Rules here may be applied when they improve one or more of:

- traceability from claim to observation;
- reproducibility or repeat-execution documentation;
- comparability between candidates;
- transparency of uncertainty, limitations, exclusions, and deviations;
- resistance to selective reporting or post-hoc criterion changes.

A methodological rule must not silently alter a frozen product criterion, hard gate, score weight, architecture invariant, or previously recorded result.

## Historical evidence ladder

The following historical evidence progression remains a useful local research classification but is not a replacement for the canonical L0-L7 capability/evidence taxonomy:

```text
DOCUMENTED
< CODE_CONFIRMED
< TEST_CONFIRMED_UPSTREAM
< EXECUTED_IN_METAO_FIXTURE
< MEASURED_IN_COMPARABLE_METAO_FIXTURE
```

The following implications remain invalid:

```text
DOCUMENTED == EXECUTED
CODE_CONFIRMED == TEST_CONFIRMED
TEST_CONFIRMED == MEASURED
PAPER_RESULT == METAO_RESULT
BENCHMARK_PASS == METAO_ACCEPTED
ABSENCE_OF_EVIDENCE == EVIDENCE_OF_ABSENCE
```

## Supplemental claim-to-evidence fields

For material claims used to justify selection, rejection, adaptation, promotion, comparative superiority, or architecture change, preserve the applicable fields below in addition to the normative empirical record required by `EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`:

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

`REPRODUCIBILITY_STATUS` must not use formal reproduction/replication labels contrary to the normative terminology. Prefer precise engineering statuses such as `REPEAT_EXECUTION_PASS`, `REPEAT_EXECUTION_FAIL`, `ARTIFACT_RERUN_BLOCKED`, or another explicitly defined non-scoring status when appropriate.

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

No universal repetition count is defined here. Repetition design must be justified by the phenomenon, variability, cost, and claim, consistent with the normative protocol.

LLM token/cost measurements should additionally record model/provider/version where available, prompt/context boundary, tool-call boundary, cache assumptions, and whether deterministic GitHub/API work was performed inside or outside the model-mediated path.

## Negative and contradictory evidence

Negative, failed, blocked, and contradictory results are part of the evidence record.

```text
BLOCKED != FAIL
UNKNOWN != PASS
NOT_PROVEN != PASS
FAILED_REPEAT_EXECUTION != AUTOMATIC_DONOR_INVALIDATION
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
- freeze hard gates and weights before candidate outcomes are interpreted when the governing comparison contract uses such gates or weights;
- record any post-observation change explicitly;
- do not silently backfit a metric to favor a candidate;
- use sensitivity analysis when the governing comparison contract requires it.

This document does not create or endorse any score, weight, or hard gate. It only requires that existing decision criteria not be silently changed after observing results.

## Claim-strength rule

The wording of a conclusion must not exceed the evidence.

```text
ONE_FIXTURE_PASS -> "passed this fixture"
MULTIPLE_COMPARABLE_RUNS -> may support a bounded comparative statement
UPSTREAM_TEST_EXISTS -> "upstream test-confirmed at pin"
CODE_INSPECTION_ONLY -> "code-confirmed", not "proven in execution"
TOOLCHAIN_BLOCKER -> "blocked", not "failed"
```

Architecture decisions may combine multiple bounded observations, but the rationale must distinguish observed facts, measurements, inferences, and unresolved hypotheses.

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

A summary without recoverable underlying evidence is weaker than the same summary with traceable raw artifacts.

## Relationship to current metaO documents

Authority is partitioned as follows:

- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md` — normative empirical evidence documentation and formal reproduction/replication terminology;
- `docs/ACCEPTANCE-CONTRACT.md` — acceptance authority and semantics;
- `docs/CHASSIS-SCORECARD-SCHEMA-2026-08-26.md` — frozen chassis hard gates, weights, status vocabulary, and scoring contract;
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md` — donor research outcomes and dispositions;
- `docs/ROADMAP-3-WU01-RUNTIME-CONFORMANCE-HARNESS.md` — runtime conformance harness scope and evidence requirements;
- ADRs — recorded architecture decisions and their historical evidence state.

If a domain-specific document contains a stricter evidence requirement that does not conflict with the normative empirical protocol, the stricter requirement applies.

## Final methodological invariants

```text
CLAIM_WITHOUT_TRACEABLE_EVIDENCE = WEAK_CLAIM
PINNED_EVIDENCE > FLOATING_REFERENCE
RAW_ARTIFACT > SUMMARY_ONLY
COMPARABLE_MEASUREMENT > CROSS_CONTEXT_NUMBER_COMPARISON
NEGATIVE_RESULT = EVIDENCE
BLOCKED != FAIL
FORMAL_REPRODUCTION_REPLICATION_TERMS = OWNED_BY_EMPIRICAL_EVIDENCE_PROTOCOL
METHODOLOGY_DOES_NOT_MINT_ARCHITECTURE_AUTHORITY
```
