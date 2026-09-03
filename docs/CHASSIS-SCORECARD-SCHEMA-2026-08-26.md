# Chassis Scorecard Schema

Status: FROZEN for pre-implementation chassis qualification (#199)
Date: 2026-08-26

## Authority

This scorecard is the fixed comparison contract for #195 after the Python golden baseline from #192.

It is governed by:

- `docs/ACCEPTANCE-CONTRACT.md`
- `docs/COMPOSITION-MAP.md`
- GitHub Issue #199
- Python baseline Issue #192 and PR #201
- C# candidate admission Issue #207

The scorecard must not be changed after observing candidate outcomes unless a new Issue records the reason, affected cells and regression impact before any decision claim.

## Candidates

```text
P = current Python baseline
A = explicit Rust Cargo workspace
B = Nidus-based modular Rust host
C = explicit C#/.NET modular chassis
```

Candidate C was admitted later by #207 under the already frozen scorecard. Its addition does not change hard gates, weights, evidence grades, status vocabulary, or award any language/framework-preference bonus.

Product migration remains unauthorized during this comparison.

```text
PRODUCT_MIGRATION = NOT_AUTHORIZED
BASELINE_REPRODUCIBLE != BASELINE_ALL_GREEN
```

## Hard Gates

Hard gates are non-compensable. Any candidate with `FAIL` in a hard gate is eliminated unless the owning Issue explicitly reclassifies that requirement before final scoring.

| Gate | Requirement | Failure condition |
|---|---|---|
| H1 | Core purity / no runtime SDK leakage | Framework, runtime, HTTP, DB, Kubernetes, Nidus or orchestrator SDK types enter `metao-kernel` or metaO Core contracts. |
| H2 | Whole-orchestrator replacement | Swapping materially different orchestrators requires Core, policy, evidence or acceptance contract changes. |
| H3 | `SUCCEEDED != ACCEPTED` | Runtime success or terminal state directly mints metaO acceptance. |
| H4 | Hard-DENY precedence | Policy, authority, provenance, budget or evidence DENY can be overridden by score, confidence, runtime success or approval text. |
| H5 | Evidence binding before acceptance | Acceptance can occur without required subject, subject-state, policy, verification context, obligation and payload binding. |
| H6 | Runtime self-report cannot mint authority | Runtime/adaptor output is accepted as governance, verifier, authority or policy source of truth. |
| H7 | Failure containment | Panic, exception, timeout or adapter error escapes the control-plane boundary or becomes `ACCEPTED`. |
| H8 | No duplicate durable or acceptance authority | Candidate introduces a second final acceptance authority or second durable workflow engine competing with the chosen foundation boundary. |
| H9 | Deterministic contract/version conflicts | Duplicate IDs, incompatible versions, ambiguous exports/providers or contract conflicts are resolved nondeterministically or silently accepted. |
| H10 | Golden semantic equivalence | Candidate drifts from frozen #192 invariants without explicit approved justification. |

## Weighted Dimensions

Only candidates that pass all hard gates receive weighted scoring.

| Dimension | Weight |
|---|---:|
| Correctness / invariants | 25 |
| Architecture isolation | 20 |
| Robustness / failure behavior | 15 |
| Testability / verification | 15 |
| Dependency / trusted surface | 10 |
| Maintainability / ergonomics | 7 |
| Maturity / ecosystem risk | 5 |
| Build/runtime engineering cost | 3 |
| Total | 100 |

No points may be awarded for language preference, star count, popularity, README claims, or features outside contracted metaO scope.

## Evidence Grades

Each hard-gate and weighted-dimension cell must carry one evidence grade.

| Grade | Name | Meaning |
|---:|---|---|
| 0 | `NOT_PROVEN` | No reliable evidence for the cell. |
| 1 | `DOCUMENTED` | Documented claim only. |
| 2 | `CODE_CONFIRMED` | Code path inspected at exact pin. |
| 3 | `TEST_CONFIRMED_UPSTREAM` | Upstream test exists and is relevant at exact pin. |
| 4 | `EXECUTED_IN_METAO_FIXTURE` | metaO fixture executed locally or in CI with command/evidence recorded. |
| 5 | `MEASURED_IN_COMPARABLE_METAO_FIXTURE` | Comparable metaO measurement exists for all viable candidates. |

A higher evidence grade increases confidence in the score. It does not automatically increase the score.

Grades 4 and 5 additionally require a reproducibility record: exact subject pin, protocol/fixture version, command, material environment/dependency versions, raw output, exit status, and disclosed deviations. Grade 5 requires the same response-variable definitions and analysis rule across candidates. A measurement that cannot be traced to these records cannot be promoted to grade 4 or 5.

## Empirical comparison protocol

Before executing a candidate comparison, record and freeze:

1. research question;
2. candidate and baseline pins;
3. independent variable(s);
4. response variables, units, and scoring transformation;
5. controlled variables and fixture version/digest;
6. run procedure and repetition count;
7. environment and material dependency versions;
8. exclusion/abort rules;
9. analysis rule;
10. known threats or limitations.

Changing these after observing outcomes creates a new protocol version. Results from different protocol versions may be reported together only when the difference is explicit; they must not be pooled as though generated under one design.

For stochastic or materially variable measurements, preserve individual-run observations rather than only aggregates. Record seeds when controllable. Report the aggregation rule and dispersion/uncertainty measure appropriate to the response variable; do not select the best run as the representative result without a predeclared rule.

## Status Values

| Status | Meaning |
|---|---|
| `PASS` | Requirement satisfied by recorded evidence at the stated grade. |
| `FAIL` | Requirement violated by recorded evidence. |
| `BLOCKED` | Evidence could not run because of an external or prerequisite blocker; blocker must be named. |
| `PARTIAL` | Some subrequirements are proven and others remain open. |
| `UNKNOWN` | The cell has not been inspected or executed yet. |
| `NOT_PROVEN` | Claim exists but evidence is insufficient for a decision. |

`BLOCKED`, `UNKNOWN` and `NOT_PROVEN` must not be converted into `PASS`.

## Baseline Facts From #192

Python baseline #192 is reproducible and not all green.

```text
BASELINE_TESTS = 16
PASS = 14
FAIL = 2
BASELINE_REPRODUCIBLE = YES
BASELINE_ALL_GREEN = NO
PINNED_BASELINE_COMMIT = b69a4e502b07ddfa1f5e05399710e335d5edfbc0
```

Remaining Python baseline architectural gaps / L5 requirements:

- shared budget concurrent oversubscription
- settlement retry idempotency

These gaps are future requirements to fix or surpass. Other candidates do not need to reproduce Python defects. Golden semantic equivalence applies to frozen invariants and expected outcomes, not to known Python weaknesses.

## Candidate Row Template

Every candidate report must include this structure before final scoring.

| Gate | Status | Evidence grade | Evidence pointer | Notes |
|---|---|---:|---|---|
| H1 | `UNKNOWN` | 0 | TBD | Core purity. |
| H2 | `UNKNOWN` | 0 | TBD | Whole-orchestrator replacement. |
| H3 | `UNKNOWN` | 0 | TBD | Runtime success is not acceptance. |
| H4 | `UNKNOWN` | 0 | TBD | Hard DENY precedence. |
| H5 | `UNKNOWN` | 0 | TBD | Evidence binding before acceptance. |
| H6 | `UNKNOWN` | 0 | TBD | Runtime self-report not authority. |
| H7 | `UNKNOWN` | 0 | TBD | Failure containment. |
| H8 | `UNKNOWN` | 0 | TBD | No duplicate durable/acceptance authority. |
| H9 | `UNKNOWN` | 0 | TBD | Deterministic conflict handling. |
| H10 | `UNKNOWN` | 0 | TBD | Golden semantic equivalence. |

## Scoring Template

| Dimension | Weight | Score 0-5 | Evidence grade | Evidence pointer | Uncertainty |
|---|---:|---:|---:|---|---|
| Correctness / invariants | 25 | TBD | 0 | TBD | TBD |
| Architecture isolation | 20 | TBD | 0 | TBD | TBD |
| Robustness / failure behavior | 15 | TBD | 0 | TBD | TBD |
| Testability / verification | 15 | TBD | 0 | TBD | TBD |
| Dependency / trusted surface | 10 | TBD | 0 | TBD | TBD |
| Maintainability / ergonomics | 7 | TBD | 0 | TBD | TBD |
| Maturity / ecosystem risk | 5 | TBD | 0 | TBD | TBD |
| Build/runtime engineering cost | 3 | TBD | 0 | TBD | TBD |

Scores are ordinal within the contracted comparison only. They are not claims of general language, framework or ecosystem superiority.

## Evidence-to-claim rule

Every decision-bearing score or gate verdict must support this chain:

```text
CLAIM -> SCORE/GATE RULE -> OBSERVATION -> RAW ARTIFACT -> EXECUTION RECORD -> SUBJECT PIN
```

The evidence pointer must identify the artifact, not merely an issue comment summarizing it. Missing evidence lowers the evidence grade; it must not be imputed from reputation, ecosystem familiarity, expected architecture, or a different candidate's behavior.

Negative and inconclusive results are retained. Candidate-specific failures may justify a candidate-specific rerun only under a recorded protocol rule; rerunning until success and reporting only the successful execution is not admissible evidence.

## Sensitivity Rule

If the top two viable candidates differ by less than five weighted points, the final report must include a sensitivity check that removes any dimension with evidence grade below 4 and recomputes the ranking.

If the winner changes under that check, #195 must classify the decision as:

```text
DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS
```

This sensitivity check addresses evidence weakness only; it is not a substitute for uncertainty analysis of measured response variables or for disclosure of threats to validity.

## Reproducibility classification

Use precise language in reports:

- `RERUN_REPRODUCED`: same pinned artifacts/protocol were independently rerun and the decision-relevant result was obtained again;
- `REPLICATION_CONSISTENT`: materially independent implementation/environment or protocol variation produced a result consistent with the claim;
- `REPLICATION_DIVERGENT`: such a replication produced a materially inconsistent result;
- `NOT_INDEPENDENTLY_CHECKED`: only the original execution is available.

Do not claim independent reproduction when the same author/process merely repeats its own run.

## Freeze Result

```text
HARD_GATES_FROZEN = YES
WEIGHTS_FROZEN = YES
EVIDENCE_GRADES_FROZEN = YES
UNCERTAINTY_VOCABULARY_FROZEN = YES
PYTHON_L5_GAPS_PRESERVED = YES
NO_LANGUAGE_POINTS = YES
NO_POPULARITY_POINTS = YES
NO_OUT_OF_SCOPE_FEATURE_POINTS = YES
EMPIRICAL_PROTOCOL_REQUIRED_FOR_GRADE_4_5 = YES
RAW_ARTIFACT_TRACEABILITY_REQUIRED = YES
POST_HOC_PROTOCOL_MUTATION_FORBIDDEN = YES
```

## Method basis

The added methodological constraints are limited to established empirical-software-engineering and computational-reproducibility practices: explicit study design, variables and protocol; complete execution reporting; comparable treatment of alternatives; preservation of raw artifacts and deviations; chain of evidence; and independently exercisable artifacts. These rules strengthen how metaO evaluates its own architectural requirements; they do not convert project-specific weights or gates into scientific standards.