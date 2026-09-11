# Empirical Evidence Audit

Status: AUDIT_RECORD
Scope: current evidence-bearing architecture and donor documentation
Governing method: `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`
Product code change: NO
Architecture decision change: NO

## Purpose

This audit records documentary evidence-strength and reproducibility gaps without rewriting historical results or changing architecture decisions.

The audit distinguishes:

```text
OBSERVED_DOCUMENTED_FACT
MEASURED_RESULT
INTERPRETATION
UNRESOLVED_REPRODUCIBILITY_GAP
```

A missing evidence pointer in a summary document does not mean the underlying evidence does not exist. It means the summary alone is insufficient to reproduce or independently verify that claim.

## Audited documents

- `docs/ADR-2026-08-27-CHASSIS-DECISION.md`
- `docs/ADR-2026-08-27-CHASSIS-SELECTION-RUST-A.md`
- `docs/ADR-2026-08-27-RUST-A-FINAL-SELECTION.md`
- `docs/CHASSIS-SCORECARD-SCHEMA-2026-08-26.md`
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md`
- `docs/ROADMAP-3-WU01-RUNTIME-CONFORMANCE-HARNESS.md`

## Finding A1 — frozen criteria are explicitly preserved

Observed:

- the scorecard records frozen hard gates, weights, evidence grades, and sensitivity behavior;
- the ADR sequence records that blocked toolchain states are not converted into semantic failure;
- popularity, stars, language preference, and README claims are explicitly excluded from scoring authority.

Classification:

```text
ANTI_POST_HOC_CRITERION_CHANGE = DOCUMENTED
BLOCKED_NOT_FAIL = DOCUMENTED
POPULARITY_NOT_EVIDENCE = DOCUMENTED
```

No corrective action required beyond continued use of the canonical empirical-method contract.

## Finding A2 — candidate pins are generally present

Observed examples:

- Rust A qualification head is recorded as `ce6d2790ac5a5118f144a16788bfc68045602ce9` in the chassis-selection ADR;
- C# qualification head is recorded as `ef641e94b1ad1cfb137d69a7a8c0648804f58033` in the same ADR;
- donor matrix entries generally use immutable commit pins when repository artifacts exist.

Classification:

```text
SUBJECT_IDENTITY = GENERALLY_STRONG
FLOATING_REFERENCE_RISK = LOW_FOR_RECORDED_PINNED_ROWS
```

Caveat: paper/standard/reference-only rows may have a different identity mechanism such as DOI/version/publication reference.

## Finding A3 — summary metrics are not always self-reproducing

Observed:

The selection ADRs contain decision-bearing numeric summaries including:

- wall-clock, CPU, and peak working-set measurements;
- clean/incremental build medians;
- artifact footprints;
- changed-LOC maintenance proxies;
- mutation counts and mutation score;
- fault-injection counts;
- weighted score totals and sensitivity results.

The ADR text records many results and some candidate heads, but the summary document itself does not consistently include all of:

- exact execution command;
- exact environment metadata;
- raw artifact/run pointer;
- per-observation dataset;
- exclusion rule;
- instrumentation version/identity.

Classification:

```text
SUMMARY_RESULT = PRESENT
SELF_CONTAINED_REPRODUCTION_PACKAGE = PARTIAL
UNDERLYING_EVIDENCE_EXISTENCE = NOT_INFERRED_FROM_SUMMARY_GAP
```

Required handling:

- do not delete or rewrite the historical measurements;
- do not upgrade their reproducibility label based on the summary alone;
- when reused for a new decision, resolve the corresponding issue/PR/run/raw artifact and create a claim-to-evidence record under the canonical empirical contract.

## Finding A4 — instrumentation correction is correctly retained

Observed:

The Rust-A selection ADR records an original C# `PackageReference=7` probe as an instrumentation defect and explicitly retains the corrected XPath-based result of zero explicit PackageReferences.

Classification:

```text
INSTRUMENTATION_DEFECT_RECORDED = YES
ORIGINAL_RESULT_SILENTLY_ERASED = NO
```

This is consistent with the project rule that post-observation protocol/instrumentation corrections preserve the correction history.

## Finding A5 — non-comparable measurements are explicitly bounded in several places

Observed:

- an earlier Rust-vs-C# compile/test timing comparison is explicitly described as not perfectly apples-to-apples because test scopes differed;
- C# mutation tooling failure is classified `NOT_COMPARABLE_TOOLING` rather than converted into a synthetic penalty;
- timeout/hang and malformed protocol fault classes are explicitly recorded as not proven/not implemented in the relevant harness state.

Classification:

```text
KNOWN_CONFOUNDERS_REPORTED = YES
MISSING_MEASUREMENT_SYNTHETIC_SCORE = NO
```

No methodological correction required. Future reuse of those observations must preserve the same bounds.

## Finding A6 — ADR chronology can be misread without supersession awareness

Observed chronology:

1. `ADR-2026-08-27-CHASSIS-DECISION.md` records `DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS`;
2. `ADR-2026-08-27-CHASSIS-SELECTION-RUST-A.md` explicitly supersedes that deferred state after later evidence;
3. `ADR-2026-08-27-RUST-A-FINAL-SELECTION.md` records the final Rust-A selection rationale and additional comparable evidence.

Classification:

```text
DECISION_EVOLUTION = DOCUMENTED
EARLIER_ADR_AS_CURRENT_AUTHORITY = INVALID_INTERPRETATION
HISTORICAL_ADR_REWRITE_REQUIRED = NO
```

Required handling:

Any current summary of chassis state must identify the later accepted selection as the current decision and treat the deferred ADR as historical evidence state, not current architecture status.

## Finding A7 — donor matrix evidence grades need claim-level pointers when promoted

Observed:

The donor matrix records immutable pins and dispositions, but the table rows are concise research summaries. The matrix itself does not contain full command/environment/raw-artifact metadata for every row.

This is acceptable for reference-only and code-inspection summaries, provided their wording remains bounded by the recorded evidence grade.

For any donor promoted into product-affecting adaptation, the canonical empirical contract now requires a claim-to-evidence record containing the applicable execution/reproduction metadata.

Classification:

```text
REFERENCE_MATRIX = SUFFICIENT_AS_INDEX
PRODUCT_PROMOTION_WITHOUT_CLAIM_RECORD = NOT_AUTHORIZED
```

## Finding A8 — harness scope is correctly narrower than product quality

Observed:

The runtime conformance harness explicitly certifies boundary correctness rather than business quality or current service availability, and it includes negative cases for binding, normalization, evidence shape, and execution exceptions.

Classification:

```text
HARNESS_SCOPE = BOUNDED
CONFORMANCE_PASS != GENERAL_PRODUCT_QUALITY
```

This boundary must be retained in future benchmark or runtime claims.

## Finding A9 — harness documentary suggestions are now applicability-bound

Observed before correction:

- the harness documentation treated several controlled-experiment fields (`baseline`, independent variable, controlled variables) as universally required;
- it described some changed-subject/material-context reruns as “replication/robustness observations”, broader than the formal reproduction/replication terminology adopted by the canonical protocol;
- the method-basis section did not require every documentary suggestion to name an applicable empirical/reproducibility criterion.

Methodological correction:

- universal claim records now contain only generally applicable traceability/reproducibility information;
- experiment/benchmark/comparative fields are conditional on the claim and study design;
- repetition, seeds, statistical analysis, resource measurement, and timestamps are required when material rather than as arbitrary universal inventory;
- formal reproduction/replication terminology is delegated to the canonical protocol;
- harness-generated documentary suggestions now require a named applicable criterion, methodological basis, applicability rationale, bounded documentary change, and explicit claim effect;
- engineering preferences, architecture choices, product requirements, arbitrary thresholds, and generic “best practices” are excluded from the empirical-documentation suggestion channel unless an applicable methodological source actually supports them.

Classification:

```text
EMPIRICAL_SUGGESTION_SCOPE = METHODOLOGY_ONLY
CRITERION_APPLICABILITY_REQUIRED = YES
UNSUPPORTED_BEST_PRACTICE_SUGGESTION = FORBIDDEN
EXPERIMENT_FIELDS_UNIVERSAL = NO
FORMAL_REPRODUCTION_TERMINOLOGY = CANONICAL_PROTOCOL_OWNED
PRODUCT_OR_ARCHITECTURE_REQUIREMENT_CREATED = NO
```

This is a documentary-method correction only. It does not weaken existing metaO architecture/security/authority requirements; it prevents those project-specific requirements from being misrepresented as empirical-research standards.

## Required evidence-reuse procedure

When an existing historical result is reused in a new architecture, donor, cost, token, or performance decision:

1. identify the exact claim being reused;
2. resolve the immutable subject pin/version when applicable;
3. resolve the original issue/PR/run/raw artifact when available;
4. record command/procedure, material environment, fixture, and measurement boundary;
5. preserve known confounders and instrumentation corrections;
6. classify the reproducibility status using the canonical terminology;
7. rerun under a comparable fixture when the new decision requires a stronger evidence grade;
8. do not generalize beyond the tested scope.

## Current audit disposition

```text
ARCHITECTURE_DECISION_CHANGED = NO
HISTORICAL_RESULT_REWRITTEN = NO
NEW_PRODUCT_REQUIREMENT = NO
CANONICAL_EMPIRICAL_METHOD = ESTABLISHED
CLAIM_TRACEABILITY_GAPS = PRESENT_BUT_MANAGEABLE
RAW_EVIDENCE_RECONSTRUCTION_REQUIRED_ON_REUSE = YES
HARNESS_DOCUMENTARY_SUGGESTIONS = APPLICABILITY_BOUND
```

The next empirical action is not to create additional criteria. It is to reconstruct claim-to-evidence records only for claims that materially enter the next active engineering decision, and to propose documentary improvements only when an applicable empirical/reproducibility criterion supports them.
