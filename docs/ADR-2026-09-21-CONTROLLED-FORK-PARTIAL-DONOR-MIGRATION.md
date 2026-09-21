# ADR — Controlled fork plus partial donor migration

Date: 2026-09-21
Status: ACCEPTED AS INCORPORATION STRATEGY
Repository: `oigorbrito/metaO`

Related:
- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`
- `docs/ADR-2026-08-27-CHASSIS-DECISION.md`
- `docs/ADR-2026-08-27-RUST-A-FINAL-SELECTION.md`
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md` — canonical project names, pins, evidence limits, donor roles, redundancy/divergence boundaries, and required next evidence

## Decision

metaO will use the following strategy when a future external chassis is empirically selected for incorporation:

```text
SELECT_CHASSIS_BY_EMPIRICAL_EVIDENCE
-> CONTROLLED_FORK_OF_SELECTED_CHASSIS
-> PRESERVE_UPSTREAM_TRACEABILITY
-> MIGRATE_ONLY_SELECTED_DONOR_CAPABILITIES
-> KEEP_DONOR_MECHANISMS_REMOVABLE
-> PROMOTE_TO_CORE_ONLY_AFTER_COMPARABLE_EVIDENCE
```

The project will **not** merge complete external frameworks merely to obtain one useful capability.

The default is:

> **Fork the empirically selected chassis; partially migrate only the capabilities from other projects that demonstrate independent value.**

This ADR defines an incorporation strategy only. It does **not** by itself authorize product migration, select Harbor, AOrchestra, BenchFlow, SWE-ReX, or any other candidate as the final metaO chassis, and does not supersede prior chassis decisions or migration gates.

## Governing principle

The governing methodological rule is already canonical:

```text
COMPLEXITY_MUST_EARN_THE_RIGHT_TO_REMAIN
EMPIRICAL_SELECTION > FEATURE_ACCUMULATION
```

The practical objective is:

> Reduce implementation complexity, trusted surface, maintenance burden, execution cost, and unnecessary context **without losing the intended objective, required capability, or empirically supported quality**.

Therefore:

```text
SIMPLER_WITH_EQUIVALENT_QUALITY > MORE_COMPLEX
LOWER_COST_WITH_LOST_OBJECTIVE != OPTIMIZATION
SMALLER_WITH_UNACCEPTABLE_REGRESSION != IMPROVEMENT
FEATURE_EXISTS != FEATURE_SHOULD_BE_CORE
```

## Why controlled fork rather than full framework fusion

A complete fusion of multiple research frameworks would import overlapping abstractions for agents, runtimes, planners, verifiers, results, telemetry, task models, and lifecycle control.

That creates risks including:

- duplicate authorities;
- duplicate runtime or scheduling layers;
- incompatible task/result semantics;
- hidden fallback behavior;
- larger dependency and trusted surfaces;
- harder upstream synchronization;
- higher regression surface;
- mechanisms that cannot be removed independently;
- inability to attribute an observed gain to one capability.

A controlled fork preserves the expensive, already-qualified body of the selected chassis while keeping the donor mechanisms experimentally separable.

## Why partial migration rather than reimplementation from memory

Partial migration means incorporating the smallest useful mechanism from a donor project while preserving:

- source attribution and license obligations;
- exact donor revision or release used for the study;
- the donor's published empirical evidence as upstream evidence;
- local adaptation boundaries;
- a reproducible comparison against the unmodified chassis baseline.

The project should prefer an isolated adaptation of a demonstrated mechanism over an independent rewrite when the rewrite would unnecessarily discard tested behavior.

However:

```text
UPSTREAM_EVIDENCE != LOCAL_PROMOTION
```

External empirical results justify candidacy and reduce duplicated research. They do not automatically prove that the capability improves metaO after transplantation.

## Chassis and donor roles

The selected chassis owns the stable infrastructure that would be most expensive and risky to recreate.

Candidate donor projects may contribute narrower mechanisms.

Current research roles include, without establishing final selection:

| Project | Current research role |
|---|---|
| Harbor | execution/evaluation chassis candidate; adapters, environments, verifier, telemetry, parallel trials, parity methodology |
| BenchFlow | donor/candidate for evidence semantics, provenance, fail-closed behavior, task/oracle/verifier structure, conversion loss reporting |
| AOrchestra | donor/candidate for decomposition, routing, and dynamic executor specification |
| FoldAgent / Context-Folding | donor for branch/return/fold and isolated-context execution |
| OneDayAgent | donor for composition, global verification, repair, and long-horizon execution-memory mechanisms |
| Agentless | domain-specific donor for hierarchical SWE localization and context narrowing |
| mini-SWE-agent | minimal executor and complexity baseline |
| TeamBench | empirical gate/benchmark for deciding when coordination and role separation are beneficial |
| AgentFlow | donor candidate for trainable planning/verification/generation when simpler planning is shown insufficient |
| MASAI | donor/reference for SWE-specialist decomposition where not redundant with selected generic decomposition |

The table is a research map, not a final ranking or authorization.

## Capability-selection rule

For every capability absent from the selected chassis:

1. identify all materially equivalent donor mechanisms;
2. preserve their published empirical results and exact versions;
3. eliminate only mechanisms that are genuinely redundant for the same role, not merely similar in name;
4. compare transplant difficulty, new dependencies, core modifications, maintenance cost, runtime overhead, and evidence quality;
5. choose the smallest mechanism that can satisfy the declared objective;
6. integrate behind a replaceable boundary;
7. evaluate against the unmodified chassis baseline;
8. retain only mechanisms whose measured value satisfies the predeclared promotion rule.

## Required classification for candidate capabilities

Each proposed donor capability must be classified as one of:

```text
TRANSPLANT_CANDIDATE
REDUNDANT_WITH_SELECTED_MECHANISM
DIVERGENT_ALTERNATIVE
BENCHMARK_OR_GATE_ONLY
DOMAIN_SPECIFIC_PLUGIN
REJECTED_BY_EVIDENCE
PROMOTED
```

Definitions:

- **TRANSPLANT_CANDIDATE** — materially distinct capability with enough upstream evidence to justify local evaluation.
- **REDUNDANT_WITH_SELECTED_MECHANISM** — same practical role already covered by a selected mechanism; do not keep two permanent implementations without evidence that diversity itself is valuable.
- **DIVERGENT_ALTERNATIVE** — competing design that should remain an experimental treatment, not be combined silently with the selected mechanism.
- **BENCHMARK_OR_GATE_ONLY** — valuable as an evaluation instrument rather than production code.
- **DOMAIN_SPECIFIC_PLUGIN** — useful only for a bounded workload; must stay outside the universal core.
- **REJECTED_BY_EVIDENCE** — tested and failed the predeclared promotion rule.
- **PROMOTED** — demonstrated sufficient local value to remain.

## Default transplantation boundaries

The preferred architecture is:

```text
SELECTED CHASSIS
|
+-- core infrastructure retained from chassis
|
+-- orchestration/
|   +-- decomposition strategy
|   +-- executor specification/routing
|   +-- context policy
|   +-- composition
|   +-- selective repair
|
+-- evidence/
|   +-- provenance
|   +-- fail-closed semantics
|   +-- conversion/loss reporting
|
+-- strategies/
    +-- domain-specific optional mechanisms
```

The names above describe responsibilities, not mandatory permanent modules.

The selected chassis should not need to know which donor project originally supplied a mechanism.

## Core-change rule

Prefer, in order:

```text
PLUGIN_OR_EXTENSION
> ADAPTER
> OPTIONAL_MODULE
> NEW_CORE_INTERFACE
> CORE_REWRITE
```

A core rewrite requires evidence that the less invasive options cannot preserve the required objective or quality.

A donor mechanism must not receive permanent core authority merely because it was expensive to integrate.

## Removal must remain possible

Every transplanted mechanism should have a clear disable/remove path.

Where practical, the system must retain the ability to execute:

```text
BASELINE_CHASSIS
vs
BASELINE + ONE_DONOR_CAPABILITY
```

This supports attribution, ablation, rollback, and independent verification.

A capability whose implementation becomes inseparable from unrelated behavior has violated the preferred experimental design unless that coupling is itself justified and documented.

## Upstream policy

For the selected chassis:

- preserve the original upstream remote or equivalent immutable source reference;
- record the exact fork point;
- keep local changes reviewable against upstream;
- avoid rewriting upstream history merely to make the fork appear native;
- periodically assess upstream changes independently from local feature promotion;
- do not merge upstream changes and donor migrations in the same evidence-bearing experiment when doing so would confound attribution.

For donors:

- record exact repository, commit/tag, license, and imported/adapted files or concepts;
- preserve required notices and attribution;
- distinguish copied code from independently reimplemented concepts;
- document material departures from the donor implementation.

## Empirical promotion contract

A transplant must not be promoted merely because:

- the upstream paper reports a gain;
- upstream benchmark results are strong;
- the code integrates successfully;
- tests pass;
- the mechanism is popular;
- the mechanism appears architecturally elegant.

Promotion requires a local comparable evaluation appropriate to the claim.

Where applicable measure:

- objective/task success;
- verifier-confirmed success;
- quality criteria specific to the workload;
- input, cached-input, and output tokens;
- cost;
- wall-clock time;
- retries;
- planner/supervisor overhead;
- dependency/trusted-surface growth;
- new core LOC and changed core LOC;
- interfaces changed;
- failure and recovery behavior.

The supported claim must remain bounded to the tested workload.

## Redundancy policy

The final project does **not** aim to contain every implementation from every candidate.

It aims to retain every **distinct capability** that earns promotion.

Examples of likely overlap requiring empirical choice rather than accumulation:

- AOrchestra decomposition vs OneDayAgent decomposition vs AgentFlow planning vs MASAI specialist decomposition;
- OneDayAgent context/memory mechanisms vs FoldAgent folding;
- OneDayAgent verifier/repair vs AgentFlow verifier/generator;
- generic decomposition vs SWE-specific hierarchical localization.

When two mechanisms perform substantially the same role:

```text
KEEP_BOTH_BY_DEFAULT = NO
COMPARE_AS_TREATMENTS = YES
PROMOTE_WINNER_OR_KEEP_BOUNDED_SPECIALISTS = YES
```

If two mechanisms are complementary rather than redundant, test the incremental combination:

```text
BASELINE
A
B
A+B
```

rather than assuming composition is beneficial.

## Divergence policy

Some capabilities may be mutually divergent rather than composable.

Examples include:

- competing ownership of orchestration lifecycle;
- two durable workflow engines;
- two independent acceptance authorities;
- overlapping retry/recovery coordinators;
- competing provenance authorities.

Such systems must not be merged merely for feature completeness.

Where divergence affects existing metaO architecture invariants, the existing canonical authority rules continue to apply.

## Validation strategy

The minimum progression for a donor mechanism is:

```text
UPSTREAM_DOCUMENTED_OR_MEASURED
-> CODE_CONFIRMED_AT_PIN
-> INTEGRATED_BEHIND_BOUNDARY
-> FOCUSED_LOCAL_EXECUTION
-> COMPARABLE_BASELINE_EXPERIMENT
-> REGRESSION/INTEGRATION_EVIDENCE
-> PROMOTE_OR_REMOVE
```

A failed or neutral experiment is a valid result.

The project must not continue adding mechanisms until a desired positive result appears.

## Decision consequences

### Positive

- preserves the most expensive validated infrastructure of the selected chassis;
- minimizes duplicated implementation;
- makes upstream advances easier to consume;
- enables ablation and causal attribution;
- keeps the project smaller than a framework fusion;
- allows donor capabilities to compete empirically;
- supports rollback when a capability fails to justify itself;
- keeps domain-specific mechanisms outside the universal core.

### Costs

- requires explicit adapter/plugin boundaries;
- requires attribution and license tracking;
- may require maintaining a fork against upstream;
- local evidence must still be collected after transplantation;
- some donor mechanisms will need adaptation rather than direct copying;
- incompatibilities may require rejecting an otherwise strong donor mechanism.

These costs are accepted because they are lower and more controllable than permanent multi-framework fusion.

## Explicit non-decisions

This ADR does not decide:

- the final chassis winner;
- that Harbor must be the chassis;
- that AOrchestra must be the supervisor;
- that every listed donor capability should be implemented;
- that upstream benchmark gains will transfer to metaO;
- that a fork is authorized for production migration now;
- that current product migration gates are bypassed.

Those decisions remain evidence-gated.

## Final invariants

```text
SELECT_CHASSIS_EMPIRICALLY
FORK_ONE_CHASSIS_NOT_MANY_FRAMEWORKS
MIGRATE_CAPABILITIES_NOT_WHOLE_DONORS
PRESERVE_UPSTREAM_TRACEABILITY
UPSTREAM_EVIDENCE != LOCAL_PROMOTION
REDUNDANCY_REQUIRES_SELECTION_NOT_ACCUMULATION
DIVERGENT_AUTHORITIES_MUST_NOT_SILENTLY_COEXIST
DOMAIN_SPECIFIC_CAPABILITY != UNIVERSAL_CORE
PLUGIN_BEFORE_CORE_REWRITE
REMOVABILITY_IS_A_DESIGN_REQUIREMENT
COMPLEXITY_MUST_EARN_THE_RIGHT_TO_REMAIN
EMPIRICAL_SELECTION > FEATURE_ACCUMULATION
