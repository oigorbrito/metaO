# metaO Local Release Gate

Status: OPERATIONAL FALLBACK FOR HOSTED-RUNNER OUTAGE.

This gate exists to produce executable evidence while GitHub-hosted Actions is failing before the first job step. It does **not** weaken the normal remote merge gate and it does not convert local execution into a production-readiness claim.

## Why this exists

The repository currently has repeated GitHub Actions runs with the same pre-step fingerprint:

```text
job conclusion = failure
steps = null / []
logs = BlobNotFound
```

A dedicated minimal diagnostic PR removed metaO test complexity entirely and still reproduced the failure:

```text
PR = #65
workflow = Actions Runner Diagnostic
run = 32736704068
job = 97461133603
job name = smoke
configured work = one ubuntu-latest shell step
steps = null
logs = BlobNotFound
```

Therefore this failure is outside metaO test assertions and happens before runner execution.

## Gate branch

Run the gate from:

```text
ops/local-release-gate-v1
```

That branch is based directly on `roadmap7/wu04-closeout-readiness` and adds only the local gate script plus this documentation.

## Prerequisites

- Windows PowerShell;
- Git;
- Python 3.12 available as `py -3.12` or `python`;
- network access for the first dependency installation;
- a clean checkout by default.

The gate creates an isolated Python environment outside the repository:

```text
%LOCALAPPDATA%\metaO\release-gate-venv
```

Evidence is also written outside the repository so the run does not dirty its own checkout:

```text
%LOCALAPPDATA%\metaO\release-gate-evidence\gate-<timestamp>.json
```

## Execute

From the local metaO checkout:

```powershell
git fetch origin
git switch ops/local-release-gate-v1
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1
```

For later runs using the already-installed exact dependency environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1 -SkipInstall
```

Dirty worktrees fail closed. `-AllowDirty` exists only for diagnosis and records `clean_worktree=false`; such a run should not be used as release evidence.

## Exact runtime pins

The script installs and verifies:

```text
openai-agents == 0.21.1
crewai        == 1.15.16
langgraph     == 1.2.11
Python        == 3.12.x
```

No paid provider call is required by the prepared real-runtime tests. OpenAI Agents uses the deterministic first-party scripted model; CrewAI uses the deterministic local BaseLLM; LangGraph uses local deterministic graphs.

## Executed gates

The local gate executes, independently records and summarizes:

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

The script runs all test gates even if an individual test gate fails, then returns a non-zero process exit code when any recorded gate is `FAIL`.

Bootstrap failures such as missing Python 3.12 or dependency installation failure stop before the test battery; those are environment failures, not metaO functional PASS results.

## Evidence format

The generated JSON contains:

```text
schema_version
UTC timestamp
Git branch
Git commit
clean_worktree
Python version
exact runtime pins
per-gate status / exit code / duration
failure_count
overall
```

A legitimate local PASS requires:

```text
clean_worktree = true
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

It must **not** be rewritten as:

```text
GITHUB_ACTIONS = PASS
REMOTE_EXECUTION = PASS
PRODUCTION_READY = YES
```

The remote Actions blocker remains a separate infrastructure condition until a hosted run reaches `Set up job` and executes real steps.

## Hosted-runner remediation

Because the minimal one-step workflow reproduces the problem, repository code changes should not be used to chase this failure.

Operational checks are now limited to:

1. GitHub account **Settings -> Billing -> Spending limits**: Actions spending limit enabled and above zero;
2. Actions enabled for the private repository;
3. if those are healthy, GitHub Support with run/job IDs including `32736704068 / 97461133603` and the earlier Roadmap runs.

This diagnostic is intentionally outside the metaO architecture roadmap.
