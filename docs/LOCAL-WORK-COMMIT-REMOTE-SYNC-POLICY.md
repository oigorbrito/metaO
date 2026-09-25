# Local Work, Commit, Branch and Remote Synchronization Policy

Status: NORMATIVE_FOR_REPOSITORY_HYGIENE
Applies to: repository `oigorbrito/metaO`
Issue: #657

## 1. Purpose

This policy governs the repository lifecycle from local worktree to commit, branch, remote synchronization, pull request, review, merge, and cleanup.

Its purpose is to prevent accumulated local residue, stale branches, mixed scopes, and oversized pull requests from becoming the default engineering path.

The governing sequence is:

```text
authoritative base
  -> fetch/prune
  -> clean worktree
  -> bounded Issue
  -> bounded branch
  -> incremental atomic commits
  -> local diff inspection
  -> synchronization check
  -> bounded PR
  -> review/evidence
  -> merge
  -> remote/local cleanup
```

This policy is repository-governance authority only. It does not redefine product architecture, empirical-evidence semantics, runtime authority, or final Acceptance.

## 2. Empirical basis and limits of the evidence

This policy uses empirical code-review evidence conservatively.

### 2.1 What the evidence supports

Research and engineering guidance support the following claims:

- review quality and usefulness can degrade as a change spans more files;
- reviewer attention is a finite resource and can be diluted across large multi-file reviews;
- focused, self-contained changes are easier to reason about and self-review;
- separating refactoring/mechanical work from semantic behavior changes improves review clarity;
- large dependent work can be decomposed into stacked changes when each layer remains reviewable.

### 2.2 What the evidence does not support

A large cross-platform study found no meaningful relationship between smaller code changes and faster merge time.

Therefore this policy MUST NOT claim:

```text
SMALL_PR == FAST_MERGE
SIZE_LIMIT == QUALITY_PROOF
UNDER_BUDGET == SAFE
OVER_BUDGET == BUGGY
```

The numeric thresholds below are metaO review-risk budgets and decomposition triggers. They are not universal empirical optima.

## 3. Repository invariants

The following rules are normative:

```text
ONE_WORK_UNIT -> ONE_BOUNDED_BRANCH
UNRELATED_CHANGE -> DIFFERENT_COMMIT_OR_BRANCH
UNTRACKED_RESIDUE -> NOT_SILENTLY_CARRIED_FORWARD
LOCAL_HEAD != REMOTE_TRUTH_UNTIL_FETCHED
OLD_BASE != CURRENT_REVIEW_BASE
PR_SIZE != QUALITY_SCORE
MERGED != LOCAL_CLEANUP_COMPLETE
```

Existing evidence invariants remain unchanged:

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
OLD_SHA_PASS != CURRENT_HEAD_PASS
```

## 4. Work-unit initialization

Before material work begins:

1. identify the governing Issue;
2. identify the intended base branch;
3. fetch remote state;
4. prune deleted remote refs;
5. inspect local status;
6. reconcile or remove unrelated local residue;
7. create a dedicated branch from the intended base.

Preferred preparation:

```console
git fetch --prune origin
git status --short
git switch main
git pull --ff-only
git switch -c <type>/issue-<n>-<short-name>
```

If the work depends on another unmerged branch, use that explicit dependency as the base and record it in the Issue/PR. Do not silently branch from a stale or unrelated working branch.

## 5. Worktree hygiene

### 5.1 Clean-boundary rule

A clean worktree is required at these boundaries:

- immediately before creating a new work-unit branch, unless the existing changes are intentionally moved to that branch and reviewed;
- after each intended commit before switching to unrelated work;
- before publishing a branch as review-ready;
- before exact-SHA qualification or release evidence;
- before checkpoint/handoff operations that already require a clean worktree.

A dirty worktree is allowed while actively editing. It is not an acceptable long-lived storage mechanism.

### 5.2 Untracked-file rule

Before commit and before branch switch, inspect:

```console
git status --short --untracked-files=all
```

Every untracked file must be one of:

- intentionally added to the current work unit;
- intentionally ignored by repository policy;
- deliberately retained local-only and outside the repository;
- removed.

An agent or developer MUST NOT leave unexplained generated files, logs, benchmark outputs, local databases, temporary patches, exports, or scratch files in the repository and allow them to accumulate into a later PR.

### 5.3 Stash is temporary transport, not storage

`git stash` MAY be used for short-lived context switching.

A stash MUST NOT be treated as a durable work queue. If the work matters, bind it to an Issue/branch/commit. Stale stashes should be reconciled or removed.

## 6. Commit discipline

Commits are durable engineering checkpoints.

A commit SHOULD:

- represent one coherent change;
- have a message that states the engineering intent;
- contain only files necessary for that intent;
- include directly related tests with semantic code changes when practical;
- avoid unrelated formatting or cleanup;
- preserve a buildable/testable repository state where practical.

Separate, unless inseparable:

- semantic behavior change;
- refactor/rename/move;
- generated output;
- dependency/lockfile update;
- documentation-only reconciliation;
- benchmark/evidence artifact ingestion;
- broad formatting.

A branch may contain multiple commits when the work unit needs multiple reviewable checkpoints. A commit is not required to map one-to-one to a PR, but unrelated concerns must not be hidden inside one commit merely to reduce commit count.

## 7. Change classification

Every PR MUST classify its dominant change surface.

Allowed classes:

```text
ORDINARY
DOCUMENTATION
MECHANICAL
GENERATED
DEPENDENCY_VENDOR
EVIDENCE_ARTIFACT
MIGRATION
```

Definitions:

- `ORDINARY`: semantic product/test/tooling/configuration changes;
- `DOCUMENTATION`: documentation-only changes;
- `MECHANICAL`: behavior-preserving rename/move/format/refactor produced by a repeatable procedure;
- `GENERATED`: output produced by a declared generator from reviewed inputs;
- `DEPENDENCY_VENDOR`: lockfile/vendor/dependency snapshot changes;
- `EVIDENCE_ARTIFACT`: benchmark/test/evidence data intentionally retained under repository policy;
- `MIGRATION`: broad schema/layout/API migration whose decomposition constraints differ from normal feature work.

Classification does not exempt a change from review. It determines whether a large-change exception is even eligible.

## 8. Review budgets

### 8.1 Normal budget

For an ordinary review surface, the target budget is:

```text
SOFT_REVIEW_TRIGGER:
  changed_files > 20
  OR changed_lines > 600

NORMAL_REVIEW_BLOCK:
  changed_files > 40
  OR changed_lines > 1200
```

`changed_lines = additions + deletions` for the PR diff against its merge base.

These thresholds are metaO governance values, not empirically universal optima.

### 8.2 Soft review trigger

Crossing the soft trigger requires an explicit self-review of decomposition before the PR is marked ready.

The PR must answer:

- can this be split by concern, layer, dependency, or behavior?
- are refactors or generated changes mixed with semantic changes?
- are documentation/evidence files inflating a code review that could be separated?
- would stacked PRs preserve dependency order while reducing review surface?

Crossing the soft trigger is not an automatic failure.

### 8.3 Normal review block

An `ORDINARY` or `DOCUMENTATION` PR above the normal review block MUST be decomposed before review-ready status.

A normal 350-file PR is therefore invalid by policy.

### 8.4 Large-change exception

A PR above the normal block may proceed only when ALL of the following hold:

1. class is `MECHANICAL`, `GENERATED`, `DEPENDENCY_VENDOR`, `EVIDENCE_ARTIFACT`, or `MIGRATION`;
2. the governing Issue records why decomposition would reduce correctness or reviewability;
3. the PR records the exact repeatable generator/command/procedure where applicable;
4. semantic and mechanical changes are separated as far as practical;
5. reviewers can inspect the transformation using a bounded verification strategy;
6. an explicit exception identifier is supplied to the hygiene guard;
7. tests/evidence appropriate to the change class are recorded.

Large-change exceptions are auditable exceptions, not silent bypasses.

## 9. Decomposition strategies

When a change exceeds the normal budget, prefer in this order where appropriate:

1. separate unrelated concerns;
2. separate refactor from behavior change;
3. split by architectural layer or stable interface;
4. split documentation/evidence from executable change when they are independently reviewable;
5. split preparatory tests from later refactor when this improves safety;
6. use stacked PRs for ordered dependent layers;
7. isolate generated/vendor/mechanical output from hand-authored semantic changes.

Each resulting PR must still be internally coherent and leave the repository in an acceptable intermediate state.

Do not split solely to game numeric thresholds if the resulting pieces are harder to understand than the original change.

## 10. Local self-review before publish

Before the first push and before marking a PR ready, inspect at minimum:

```console
git status --short --untracked-files=all
git log --oneline --decorate <base>..HEAD
git diff --stat <merge-base>..HEAD
git diff --name-status <merge-base>..HEAD
git diff --check <merge-base>..HEAD
```

Review the complete diff for:

- accidental files;
- generated artifacts;
- secrets/credentials;
- debug output;
- unrelated formatting;
- stale documentation;
- duplicate changes already present in base;
- scope drift from the governing Issue.

The author/agent should review the same diff that the reviewer will receive.

## 11. Remote synchronization

### 11.1 Fetch before reasoning about remote truth

Before any of the following, fetch the relevant remote:

- creating a branch from a remote-tracked base;
- reporting ahead/behind state;
- opening or materially updating a PR;
- declaring a branch current;
- requesting final review;
- merge/readiness assessment.

Use:

```console
git fetch --prune origin
```

A local tracking ref that has not been fetched is not sufficient evidence of current remote state.

### 11.2 Base freshness

Before a PR is review-ready, determine whether current remote base is an ancestor of the PR head.

If not, classify the branch as stale against the current base and synchronize by the repository-approved method.

Do not claim exact-head/current-base evidence from a stale merge base.

### 11.3 Force-push safety

Do not force-push shared or reviewed history casually.

If history rewrite is required for an unmerged feature branch:

- use `--force-with-lease`, never blind `--force`;
- fetch first;
- confirm the expected remote head;
- record material history rewrites when review context could be invalidated.

Protected/canonical branches must not be force-pushed through this workflow.

## 12. PR lifecycle

Open a draft PR early enough to expose scope, but do not allow it to become an indefinite accumulation branch.

At each material expansion:

1. compare the new scope to the governing Issue;
2. inspect changed-file/line budget;
3. split new independent concerns immediately rather than waiting until final review;
4. update the PR description with current evidence and dependency state.

If a branch crosses the normal review block due to accumulated unrelated work, stop adding files and decompose before further implementation.

## 13. Merge and cleanup

After merge:

1. verify the intended commit/change landed on the target branch;
2. fetch/prune remote state;
3. delete the merged transient remote branch when repository policy permits;
4. remove the corresponding local branch/worktree when no longer needed;
5. reconcile stashes and local-only artifacts associated with the completed work;
6. confirm no superseded branch is still being treated as active authority.

Long-lived evidence/protected refs are exempt only when explicitly classified as such.

## 14. Machine-checkable hygiene guard

The repository-owned guard is:

```console
python scripts/check_change_hygiene.py --base-ref origin/main --change-class ORDINARY
```

The guard reports:

- current branch;
- head/base/merge-base identities;
- changed file count;
- changed line count;
- worktree cleanliness;
- ahead/behind counts;
- budget state.

Exit semantics:

```text
0 = PASS
2 = WARN / decomposition review required
3 = BLOCK / normal review budget exceeded or invariant violation
```

A large-change exception requires both an eligible change class and an explicit `--exception-id`.

The guard does not prove code quality, correctness, test success, or Acceptance.

## 15. Evidence record for PR hygiene

A PR that reaches the soft trigger or higher SHOULD record:

```text
BASE_REF:
BASE_SHA:
HEAD_SHA:
MERGE_BASE_SHA:
CHANGE_CLASS:
CHANGED_FILES:
CHANGED_LINES:
AHEAD:
BEHIND:
WORKTREE_CLEAN:
BUDGET_STATE:
EXCEPTION_ID:
DECOMPOSITION_DECISION:
```

This record is review metadata, not product evidence.

## 16. References

Empirical and engineering references:

1. Bosu, A. et al. (2015), *Characteristics of Useful Code Reviews: An Empirical Study at Microsoft*, MSR 2015, DOI 10.1109/MSR.2015.21.
   https://ieeexplore.ieee.org/document/7180075/
2. Kudrjavets, G., Nagappan, N., Rastogi, A. (2022), *Do Small Code Changes Merge Faster? A Multi-Language Empirical Investigation*, arXiv:2203.05045.
   https://arxiv.org/abs/2203.05045
3. Rahman, M. S., Codabux, Z., Roy, C. K. (2026), *Does Order Matter? An Empirical Investigation into the Impact of File Ordering on Code Review Effectiveness*, arXiv:2609.22610. Preprint.
   https://arxiv.org/abs/2609.22610
4. GitHub Docs, *Helping others review your changes*.
   https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes
5. GitHub Docs, *Stack code changes in pull requests*.
   https://docs.github.com/en/pull-requests/tutorials/stack-code-changes-in-pull-requests
6. Google Engineering Practices, *Small CLs*.
   https://google.github.io/eng-practices/review/developer/small-cls.html

Repository empirical claims remain governed by `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.
