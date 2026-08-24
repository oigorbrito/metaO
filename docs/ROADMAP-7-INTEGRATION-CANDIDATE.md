# Roadmap 7 Canonical Integration Candidate

Status: FROZEN FOR EXECUTION EVIDENCE — RERUN REQUIRED AFTER DEPENDENCY COMPATIBILITY CORRECTION.

## Purpose

This branch is the single canonical merge surface for cumulative Roadmaps 2 through 7 plus the reproducible local release gate prepared while GitHub-hosted Actions is blocked before runner allocation.

It exists so executable evidence can be tied to one exact commit and one final PR to `main` rather than to a long dependency stack of draft PRs.

## Base

```text
main = 628b73409aa596bdcea7cf39136f455a0c220b05
```

The candidate descends directly from that baseline without rebasing or rewriting the historical stack.

## Included capability

The candidate includes:

- deterministic runtime feedback without learned routing;
- framework-neutral runtime conformance and admission;
- durable runtime certification, freshness, revocation and latest-verdict authority;
- declarative certified onboarding and certificate reuse;
- OpenAI Agents SDK adapter alongside CrewAI and LangGraph;
- real provider-free three-runtime regression scenarios;
- failure-aware deterministic replanning;
- bounded durable human escalation;
- three-runtime recovery ending in independent metaO acceptance;
- reproducible Windows local release gate with machine-readable evidence.

Active executable runtime pins:

```text
OpenAI Agents SDK 0.20.0
CrewAI 1.15.16
LangGraph 1.2.11
Python 3.12.x
```

## Compatibility correction

The Roadmap 6 preparation originally pinned OpenAI Agents 0.21.1. The first real local pip resolution proved that 0.21.1 cannot coexist with CrewAI 1.15.16 in one Python environment:

```text
openai-agents 0.21.1 -> openai >=3,<4
crewai 1.15.16       -> openai >=2.30,<3
```

OpenAI Agents 0.20.0 preserves the selected runtime and the synchronous adapter fit while restoring a compatible dependency intersection:

```text
openai-agents 0.20.0 -> openai >=2.45,<3
crewai 1.15.16       -> openai >=2.30,<3
shared range          -> openai >=2.45,<3
```

No metaO Core or `OrchestratorContract` change was required.

Because the first-party `agents.testing.ScriptedModel` used by the originally prepared 0.21.1 tests is not exposed by 0.20.0, the candidate uses a test-only deterministic implementation of the SDK public `Model` interface in `tests/integration/_openai_agents_model.py`. Production remains unchanged.

The detailed audit record is `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

## Architecture

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

Invariant:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

Architecture test:

```text
Can an entire orchestrator runtime be replaced without changing metaO Core?
```

The dependency correction does not alter that answer.

## Intentionally excluded

- fourth runtime;
- learned routing or reinforcement learning;
- framework-specific logic in metaO Core;
- Kubernetes/cloud infrastructure;
- distributed database work;
- production paid-provider execution;
- weakening quarantine, policy, budget, approval or acceptance authority.

## Hosted Actions blocker

Minimal diagnostics isolated the hosted-runner failure outside metaO logic.

```text
PR #65 / Ubuntu
run 32736704068
job 97461133603
steps = null
logs = BlobNotFound

PR #67 / cross-OS
macOS  job 97463231179 -> steps = null
Windows job 97463231312 -> steps = null
Ubuntu  job 97463231320 -> steps = null

PR #68 canonical candidate
job 97474055832 -> steps = null
```

The hosted blocker is classified as external pre-step infrastructure. It is neither functional PASS nor functional FAIL for the candidate.

## Canonical executable gate

All new local evidence must come from:

```text
roadmap7/integration-candidate-v1
```

After a failed dependency-resolution attempt, recreate the isolated venv before the next release-evidence run:

```powershell
cd C:\Projetos\metao-gate
git fetch origin
git switch roadmap7/integration-candidate-v1
git pull --ff-only
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\metaO\release-gate-venv" -ErrorAction SilentlyContinue
git status --short
git rev-parse HEAD
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

JSON evidence is emitted outside the repository under `%LOCALAPPDATA%\metaO\release-gate-evidence`.

## Merge rule

Do not merge this candidate while executable functional evidence is absent.

Outcome handling:

1. `BOOTSTRAP_FAIL` -> fix environment/dependency setup only and rerun;
2. `HARNESS_FAIL` -> fix gate mechanics and rerun;
3. `TEST_FAIL` -> fix concrete regressions without weakening architecture and rerun the complete gate;
4. `PASS` -> review generated evidence and exact candidate SHA;
5. only a verified PASS may make the canonical PR merge-eligible under the agreed gate policy;
6. hosted Actions remains a separate infrastructure condition and must not be falsely marked green.

After validation and merge, historical stacked PRs #56 through #64 and component PR #66 should be superseded/closed rather than individually merged.

## Current status

```text
ROADMAP_2_TO_7_ASSEMBLY = COMPLETE
CANONICAL_INTEGRATION_CANDIDATE = CREATED
DEPENDENCY_CONFLICT_0_21_1 = CONFIRMED
ACTIVE_OPENAI_AGENTS_PIN = 0.20.0
CANONICAL_LOCAL_GATE = UPDATED
CANONICAL_EXECUTION_AFTER_FIX = PENDING
FUNCTIONAL_PASS = NOT CLAIMED
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
MAIN_MODIFIED = NO
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```
