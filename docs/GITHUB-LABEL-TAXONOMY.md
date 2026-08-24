# GitHub label taxonomy

## Purpose

metaO uses a small, explicit label taxonomy to make Issues and Pull Requests filterable across the GitHub Project without turning labels into a second task tracker.

Labels are metadata only. They never prove functional correctness.

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
```

The GitHub Project remains the primary visual workflow state. Issues remain the operational source of truth.

## Canonical labels

### Status

Use status labels only for portable states that are useful outside the Project view.

```text
status:ready
status:blocked
status:needs-evidence
```

Semantics:

- `status:ready` — bounded and actionable; implementation may start.
- `status:blocked` — progress depends on an unresolved external/internal blocker.
- `status:needs-evidence` — implementation or assembly exists, but required executable acceptance evidence is still missing.

Do not add `status:in-progress` or `status:done` labels. Those are represented by the GitHub Project state and by Issue/PR open/closed/merged state. Avoiding duplicate state reduces drift.

### Type

Use exactly one primary type where practical.

```text
type:architecture
type:infra
type:test
type:docs
type:feature
type:bug
```

- `type:architecture` — architecture boundary, contract, design or authority changes.
- `type:infra` — CI, runners, dependency/bootstrap, repository or operational infrastructure.
- `type:test` — validation harnesses, regressions, gates and evidence tooling.
- `type:docs` — documentation/repository governance with no production behavior change.
- `type:feature` — product/control-plane capability implementation.
- `type:bug` — defect/regression correction.

Research that exists only to support a decision should normally use the type of the decision it feeds rather than creating a permanent `type:research` bucket. If research becomes a substantial independent workflow, add that label through an explicit governance Issue first.

### Priority

Use exactly one priority for active work.

```text
priority:p0
priority:p1
priority:p2
```

- `priority:p0` — blocks release/canonical acceptance, causes unsafe behavior, or prevents critical execution.
- `priority:p1` — important current-cycle work that should follow P0 blockers.
- `priority:p2` — useful maintenance, documentation or non-blocking improvement.

Priority does not imply acceptance or authorization to merge.

### Area

Use one or more areas when they improve filtering.

```text
area:core
area:adapter
area:runtime
area:policy
area:acceptance
area:certification
area:replan
area:release
```

Areas identify the affected authority/boundary, not merely a filename.

- `area:core` — framework-neutral metaO Core contracts/behavior.
- `area:adapter` — runtime adapter/plugin integration boundary.
- `area:runtime` — orchestrator runtime composition, compatibility and runtime-facing behavior.
- `area:policy` — policy, budget, approval and governance authority.
- `area:acceptance` — independent acceptance/evidence decision path.
- `area:certification` — conformance, admission and certification lifecycle.
- `area:replan` — failure classification, replanning, escalation and failover authority.
- `area:release` — release gates, canonical integration, CI/release evidence and merge readiness.

## Status transition rules

Typical transitions:

```text
Project Backlog
  -> Project Ready + status:ready
  -> Project In Progress (remove status:ready)
  -> status:blocked when execution cannot continue
  -> status:needs-evidence when implementation exists but acceptance evidence is missing
  -> Project Ready to Merge only after required evidence is green
  -> merged/closed + Project Done
```

A work item may move directly from In Progress to Blocked or Needs Evidence. Status labels should reflect the current exceptional/portable state, not preserve history. History belongs in Issue comments and GitHub events.

## Evidence rule

Never use a label as evidence.

Examples:

- `status:needs-evidence` does not mean tests failed; it means required proof is absent.
- `status:blocked` does not mean product failure; the Issue must classify the blocker.
- removing `status:blocked` does not imply PASS.
- `priority:p0` does not authorize bypassing gates.

Executable results remain explicit:

```text
NOT_RUN
PASS
TEST_FAIL
BOOTSTRAP_FAIL
HARNESS_FAIL
BLOCKED_EXTERNAL
```

## Current canonical mapping

As established by Issue #76:

```text
#70 Canonical Roadmaps 2-7 validation
  status:needs-evidence
  type:test
  priority:p0
  area:release

#71 Hosted Actions pre-step blocker
  status:blocked
  type:infra
  priority:p0
  area:release

#72 OpenAI Agents / CrewAI compatibility correction
  status:needs-evidence
  type:infra
  priority:p0
  area:runtime

#73 Release Evidence Validator
  status:needs-evidence
  type:test
  priority:p1
  area:release

PR #68 Canonical integration candidate
  status:needs-evidence
  type:feature
  priority:p0
  area:release

PR #69 Release Evidence Validator
  status:needs-evidence
  type:test
  priority:p1
  area:release
```

## Governance

Adding a new permanent status/type/priority/area label should be treated as repository-governance work when it changes the taxonomy rather than merely categorizing one item.

Before adding a new category, prefer an existing label if it represents the same operational concept. Avoid overlapping aliases such as `blocked`, `status:blocker`, and `status:blocked`.

The objective is a small taxonomy with reliable meaning, not exhaustive classification.
