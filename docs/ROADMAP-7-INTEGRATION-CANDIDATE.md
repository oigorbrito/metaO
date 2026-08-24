# Roadmap 7 Canonical Integration Candidate

Status: FROZEN FOR EXECUTION EVIDENCE — NOT MERGE-ELIGIBLE YET.

## Purpose

This branch is the single canonical merge surface for cumulative Roadmaps 2 through 7 plus the reproducible local release gate prepared while GitHub-hosted Actions is blocked before runner allocation.

It exists so executable evidence can be tied to one exact commit and one final PR to `main` rather than to a long dependency stack of draft PRs.

## Base

```text
main = 628b73409aa596bdcea7cf39136f455a0c220b05
```

The candidate is descended directly from that baseline and was assembled without rebasing or rewriting history.

Pre-freeze comparison immediately before this document was added:

```text
ahead = 99 commits
behind = 0 commits
```

## Included capability

The candidate includes the cumulative implementation prepared in Roadmaps 2-7:

- deterministic runtime feedback without learned routing;
- framework-neutral runtime conformance and admission;
- durable runtime certification, freshness, revocation and latest-verdict authority;
- declarative certified onboarding and certificate reuse;
- OpenAI Agents SDK 0.21.1 adapter alongside CrewAI 1.15.16 and LangGraph 1.2.11;
- real provider-free three-runtime regression scenarios;
- failure-aware deterministic replanning;
- bounded durable human escalation;
- three-runtime recovery path ending in independent metaO acceptance;
- reproducible Windows local release gate with machine-readable evidence.

The central architecture remains:

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter
  -> Real Orchestrator
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

And the invariant remains:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

## What is intentionally not included

- fourth runtime;
- learned routing or reinforcement learning;
- framework-specific logic in metaO Core;
- Kubernetes or cloud infrastructure;
- distributed database work;
- production paid-provider execution;
- weakening of quarantine, policy, budget, approval or acceptance authority.

## Hosted Actions blocker

Two minimal diagnostics isolated the current hosted-runner failure outside metaO logic.

Single Ubuntu diagnostic:

```text
PR #65
run 32736704068
job 97461133603
steps = null
logs = BlobNotFound
```

Cross-OS diagnostic:

```text
PR #67
run 32737346242
macOS  job 97463231179 -> steps = null
Windows job 97463231312 -> steps = null
Ubuntu  job 97463231320 -> steps = null
```

Both diagnostic PRs were closed unmerged.

Therefore the hosted blocker is classified as external pre-step allocation/entitlement infrastructure. It is not a functional PASS or FAIL for the candidate.

## Canonical executable gate

All local evidence must now be generated from this exact branch:

```text
roadmap7/integration-candidate-v1
```

From a clean Windows checkout:

```powershell
git fetch origin
git switch roadmap7/integration-candidate-v1
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1
```

The gate executes 21 recorded checks covering exact runtime pins, CLI/import smoke, Roadmaps 2-7, Block O and the SDK-neutral Core/control-plane boundary.

A valid local functional PASS requires:

```text
clean_worktree = true
phase = complete
fatal_error = null
failure_count = 0
overall = PASS
```

The JSON evidence is emitted outside the repository under `%LOCALAPPDATA%\metaO\release-gate-evidence`.

## Merge rule

Do not merge this candidate while executable evidence is absent.

When the local gate executes:

1. if `BOOTSTRAP_FAIL`, fix environment only and rerun;
2. if `HARNESS_FAIL`, fix the gate/harness and rerun;
3. if `TEST_FAIL`, fix concrete regressions without weakening architecture and rerun the full gate;
4. if `PASS`, review the generated evidence and exact candidate SHA;
5. only after verified PASS may this canonical PR become merge-eligible;
6. hosted Actions remains a separate infrastructure condition and must not be falsely marked green.

After this canonical candidate is validated and merged, historical stacked PRs #56 through #64 and the operational component PR #66 should be superseded/closed rather than individually merged.

## Current status

```text
ROADMAP_2_TO_7_ASSEMBLY = COMPLETE
CANONICAL_INTEGRATION_CANDIDATE = CREATED
CANONICAL_LOCAL_GATE = PREPARED
CANONICAL_EXECUTION = PENDING
FUNCTIONAL_PASS = NOT CLAIMED
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
MAIN_MODIFIED = NO
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```
