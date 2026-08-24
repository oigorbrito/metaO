# GitHub-native engineering workflow

## Purpose

metaO uses GitHub as the persistent operational ledger for engineering work.

The repository workflow is **Issue-first**:

```text
Project / Roadmap
  -> Issue
  -> Branch
  -> Pull Request
  -> Tests / Evidence
  -> PASS / FAIL / BLOCKED
  -> Merge
  -> Close Issue
```

Chat, local terminals, and external research may help execute the work, but they are not the durable source of truth for work status.

## Sources of truth

### Project

The GitHub Project is the visual operating view: backlog, active work, blockers, evidence state, merge readiness, and completed work.

Recommended status model:

```text
Backlog
Ready
In Progress
Blocked
Needs Evidence
Ready to Merge
Done
```

The Project is a view over work. It does not replace the Issue.

### Issue

The Issue is the **operational source of truth** for a work unit.

It owns:

- objective;
- context and evidence that justify the work;
- in-scope and out-of-scope boundaries;
- architecture/safety invariants;
- acceptance criteria;
- dependencies and blockers;
- progress and execution evidence;
- final disposition.

Relevant implementation work should not start without an Issue.

A parent/roadmap Issue may own a work tree through native sub-issues or explicit checklist links.

### Branch

A branch is the isolated implementation surface for one Issue or one tightly coupled set of Issues.

Preferred naming examples:

```text
feat/issue-123-short-name
fix/issue-123-short-name
ops/issue-123-short-name
docs/issue-123-short-name
research/issue-123-short-name
```

Existing roadmap/WU branch naming remains valid for historical work. Do not rename historical branches only for cosmetics.

### Pull Request

A PR answers **what changed in the repository** and provides the review/merge surface.

A PR does not replace the governing Issue.

Every relevant PR should:

- link its governing Issue;
- state outcome, scope, and out-of-scope items;
- identify the change surface;
- preserve applicable architecture invariants;
- classify execution evidence honestly;
- remain draft while the merge gate is not satisfied.

Use `Closes #<issue>` only when merge of that PR should complete the Issue. Otherwise use a normal related/tracks link and close the Issue only after its full acceptance criteria are satisfied.

### Actions / local gates

Actions and local executable gates provide evidence. They do not define intent or scope.

A workflow failure must be classified before it is treated as a product failure.

### Release / tag

A release or tag represents an accepted repository state. It must be backed by evidence from the exact accepted commit, not by a prior or adjacent SHA.

## Evidence discipline

The core evidence policy is:

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

### Allowed execution classifications

Use explicit states such as:

```text
NOT_RUN
PASS
TEST_FAIL
BOOTSTRAP_FAIL
HARNESS_FAIL
BLOCKED_EXTERNAL
```

Meaning:

- `NOT_RUN`: implementation/tests may exist, but execution has not happened;
- `PASS`: the relevant command/gate actually executed successfully;
- `TEST_FAIL`: executable functional/test evidence failed;
- `BOOTSTRAP_FAIL`: environment/dependency/bootstrap stopped execution before the intended gates;
- `HARNESS_FAIL`: the validation harness itself failed;
- `BLOCKED_EXTERNAL`: external infrastructure prevented meaningful repository execution.

A GitHub Actions job that never reaches configured steps is not a metaO functional test failure.

Static review may prove scope or architecture properties, but it is never a substitute for executable PASS when the acceptance criterion requires execution.

## Architecture guardrails

Every Issue and PR must preserve applicable metaO invariants.

Canonical invariants include:

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter
  -> Orchestrator real
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

And:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
ADOPT > ADAPT > BUILD
```

The central replaceability test remains:

> Can an entire orchestrator, including its agents, tools, memory, prompts, routing, and workflows, be replaced without changing metaO Core?

If not, the abstraction must be reviewed before merge.

Framework SDKs remain adapter/plugin concerns. Policy, budget, approval, quarantine, replan authority, certification authority, and independent acceptance remain metaO-owned.

## Work-unit lifecycle

### 1. Create the Issue

Before implementation, record:

- objective;
- evidence/context;
- scope;
- out of scope;
- invariants;
- acceptance criteria;
- evidence plan;
- parent/roadmap relationship when applicable.

If the work is exploratory, the Issue may end in a documented `not planned` decision rather than code.

### 2. Move to Ready / In Progress

Work should be actionable and bounded before implementation begins.

If a required dependency is unresolved, keep it `Blocked` rather than silently implementing around it.

### 3. Create a branch

Branch from the correct dependency/base state.

Do not branch from `main` by habit when the Issue explicitly depends on an unmerged integration candidate. Conversely, repository-governance or independent operational work should not be stacked on a functional candidate without need.

Record the base relationship in the Issue/PR when it matters.

### 4. Implement the smallest accepted scope

Prefer:

```text
ADOPT > ADAPT > BUILD
```

Do not introduce adjacent features merely because the current block is waiting on evidence.

Any material scope expansion must be recorded in the Issue before implementation.

### 5. Open a draft PR

The PR should exist early enough to hold review/evidence, but draft status must not be confused with merge readiness.

The PR template requires:

- linked Issue;
- outcome;
- scope/out-of-scope;
- architecture guardrails;
- change surface;
- validation/evidence state;
- exact branch/SHA evidence binding;
- merge gate.

### 6. Execute validation

Use the acceptance criteria from the Issue, not an ad-hoc smaller test set chosen after implementation.

Typical progression when applicable:

```text
focused test
-> full unit regression
-> real runtime / integration sandbox
-> architecture/boundary gate
-> release/canonical gate
```

Record exact commands, run/job IDs, evidence artifacts, and the tested SHA.

### 7. Classify failures

Do not patch production code until the failure class is understood.

Prefer the smallest correct layer:

- environment/dependencies -> bootstrap correction;
- gate mechanics -> harness correction;
- framework mismatch -> adapter/plugin correction;
- actual metaO behavior -> production correction;
- external runner/account failure -> external blocker Issue.

Do not weaken Core invariants simply to turn a gate green.

### 8. Ready to Merge

A PR becomes merge-ready only when:

- governing Issue acceptance criteria are satisfied;
- required executable evidence is green;
- evidence belongs to the exact head SHA being reviewed;
- unresolved review threads are cleared;
- dependency/base state is valid;
- documentation is current.

### 9. Merge and close

Merge only after the merge gate is satisfied and authorized by the project workflow.

After merge:

- confirm the accepted change exists in the target branch;
- close/supersede obsolete stacked PRs only when their intended artifacts are actually contained in the accepted state;
- update the governing Issue with final evidence;
- close the Issue as completed;
- move the Project item to Done.

An Issue may instead close as `not planned`/duplicate when that is the explicit decision and is documented.

## Parent Issues and roadmaps

Use a parent Issue for a roadmap/cycle when several independently verifiable blocks contribute to one acceptance target.

Example:

```text
Parent: Canonical integration validation
  -> hosted-runner blocker
  -> dependency compatibility
  -> release evidence validator
  -> canonical local gate
  -> merge/supersession decision
```

The parent closes only when its own acceptance criteria are satisfied; completing one child does not imply parent acceptance.

## Blockers

A blocker deserves its own Issue when it has an independent investigation, owner, evidence set, or resolution condition.

Record:

- classification;
- evidence already collected;
- checks already completed;
- remaining actions;
- workaround if one exists;
- exact condition that resolves the blocker.

Do not repeatedly rerun a blocked external system without new diagnostic value.

## Documentation vs Issues

Use repository documentation for durable architecture, contracts, operating rules, and accepted design decisions.

Use Issues for evolving execution state, tasks, blockers, and acceptance progress.

Use PRs for reviewable repository changes.

This separation prevents long-lived architecture from being trapped in chat history while preventing static documents from becoming an inaccurate task tracker.

## Current adoption

The Issue-first model was introduced during the Roadmaps 2–7 canonical validation cycle.

Initial operational Issues:

- #70 — Roadmap 2–7 canonical integration validation;
- #71 — GitHub Actions hosted-runner pre-step blocker;
- #72 — OpenAI Agents / CrewAI dependency compatibility correction;
- #73 — fail-closed release evidence validator;
- #74 — this repository workflow/template rollout.

Historical PRs do not need retroactive Issues solely for bookkeeping. Create/retain Issues for work that is still open, blocked, or materially relevant to project continuity.
