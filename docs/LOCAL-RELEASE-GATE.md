# metaO Local Release Gate

Status: OPERATIONAL FALLBACK FOR HOSTED-RUNNER OUTAGE — PENDING RERUN AFTER DEPENDENCY COMPATIBILITY FIX.

This gate exists to produce executable evidence while GitHub-hosted Actions fails before the first job step. It does **not** weaken the normal remote merge gate and it does not convert local execution into a production-readiness claim.

## Hosted-runner evidence

Repeated GitHub Actions runs fail with the same pre-step fingerprint:

```text
job conclusion = failure
steps = null / []
logs = BlobNotFound
```

Minimal diagnostics removed metaO test complexity and reproduced the failure:

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
```

Both diagnostics were closed unmerged.

Therefore:

```text
METAO_TEST_LOGIC_CAUSE = NO
WORKFLOW_COMPLEXITY_CAUSE = NO
HOSTED_OS_SPECIFIC = NO
HOSTED_OS_SWITCH_WORKAROUND = NO
```

The hosted blocker remains upstream of repository execution.

## Canonical gate branch

Run only from the canonical integration candidate:

```text
roadmap7/integration-candidate-v1
```

Historical branch `ops/local-release-gate-v1` is superseded for release evidence.

## Prerequisites

- Windows PowerShell;
- Git;
- Python 3.12 available as `py -3.12` or `python`;
- network access for dependency installation;
- clean checkout by default.

The isolated environment is outside the repository:

```text
%LOCALAPPDATA%\metaO\release-gate-venv
```

Evidence is written outside the repository:

```text
%LOCALAPPDATA%\metaO\release-gate-evidence\gate-<timestamp>.json
```

## Dependency compatibility correction

The first real Windows dependency-resolution attempt exposed an incompatible prepared set before any functional test ran:

```text
openai-agents 0.21.1 -> openai >=3,<4
crewai 1.15.16       -> openai >=2.30,<3
result                -> ResolutionImpossible
```

The evidence-based active set is now:

```text
openai-agents == 0.20.0   # requires openai >=2.45,<3
crewai        == 1.15.16  # requires openai >=2.30,<3
langgraph     == 1.2.11
Python        == 3.12.x
```

The compatible shared OpenAI client range is therefore:

```text
openai >=2.45,<3
```

The third runtime remains OpenAI Agents SDK. No Core or `OrchestratorContract` change was required. See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

## Provider-free deterministic runtime seams

No paid provider call is required by the prepared real-runtime tests:

- OpenAI Agents 0.20.0 uses `tests/integration/_openai_agents_model.py`, a small test-only deterministic implementation of the SDK public `Model` interface;
- CrewAI uses a deterministic local `BaseLLM`;
- LangGraph uses local deterministic graphs.

The OpenAI test helper is not production code and does not change the SDK-neutral Core boundary.

## Execute

For a clean rerun after the earlier failed resolver attempt, remove the old gate venv once, then run the canonical candidate:

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

For later diagnostic reruns using an already validated exact dependency environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1 -SkipInstall
```

Dirty worktrees fail closed. `-AllowDirty` exists only for diagnosis and records `clean_worktree=false`; such a run is not valid release evidence.

## Executed gates

The local gate records 21 checks:

1. exact runtime versions;
2. installed CLI help;
3. installed package/import smoke;
4. Roadmap 2 WU05 deterministic feedback;
5. Roadmap 7 WU01 failure-aware replan;
6. Roadmap 7 WU02 durable escalation;
7. full unit suite;
8. Roadmap 2 real second-runtime sandbox;
9. Roadmap 3 real runtime certification;
10. Roadmap 4 real declarative certified runtimes;
11. Roadmap 5 real certificate lifecycle;
12. Roadmap 6 WU04 OpenAI adapter unit regression;
13. Roadmap 6 WU04 real OpenAI Agents conformance;
14. Roadmap 6 WU05 real three-runtime regression;
15. Roadmap 7 WU03 three-runtime recovery regression;
16. Block O O1 LangGraph real;
17. Block O O2 end-to-end sandbox;
18. Block O O3 failover sandbox;
19. Block O O4 governance gates;
20. Block O O5 runtime swap;
21. SDK-neutral Core/control-plane boundary.

Normal test gates continue after individual test failures so the final evidence contains the complete failing set.

## Outcome classification

```text
PASS           = full recorded battery completed with zero failures
TEST_FAIL      = functional/test gates executed and one or more failed
BOOTSTRAP_FAIL = environment/dependency setup failed before tests
HARNESS_FAIL   = release-gate mechanics failed after bootstrap
```

Exit codes:

```text
0 = PASS
1 = TEST_FAIL
2 = BOOTSTRAP_FAIL or HARNESS_FAIL
```

A legitimate local PASS requires:

```text
clean_worktree = true
phase = complete
fatal_error = null
failure_count = 0
overall = PASS
```

## Evidence semantics

A successful local gate may establish:

```text
LOCAL_EXECUTION = PASS
FUNCTIONAL_REGRESSION = PASS on recorded commit
REAL_PROVIDER_FREE_RUNTIME_SANDBOXES = PASS
SDK_NEUTRAL_BOUNDARY = PASS
```

It does **not** establish:

```text
GITHUB_ACTIONS = PASS
REMOTE_EXECUTION = PASS
PRODUCTION_READY = YES
```

The remote Actions blocker remains separate until a hosted run reaches real steps.

## Current status

```text
DEPENDENCY_CONFLICT_0_21_1 = CONFIRMED
ACTIVE_OPENAI_AGENTS_PIN = 0.20.0
LOCAL_GATE_IMPLEMENTATION = UPDATED
LOCAL_GATE_RERUN = PENDING
FUNCTIONAL_PASS = NOT CLAIMED
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
MERGE_GATE = PENDING
```
