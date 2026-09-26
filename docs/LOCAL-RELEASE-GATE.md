# metaO Local Release Gate

Status: OPERATIONAL AND EXECUTED SUCCESSFULLY FOR THE ROADMAPS 2-7 CANONICAL CANDIDATE — HOSTED RUNNERS REMAIN EXTERNALLY BLOCKED.

Historical note: this document remains the local-gate evidence record for the validated v0.1 lineage. It does not override `docs/POST-MVP-OPERATIONAL-BASELINE-V1.md` for current baseline authority.

The local release gate exists to produce reproducible executable evidence when GitHub-hosted Actions cannot reach repository execution. It does not convert local execution into a production-readiness claim and it does not turn an external hosted-runner failure into a metaO functional failure.

## Validated Roadmaps 2-7 run

The canonical candidate completed the full gate successfully:

```text
branch = roadmap7/integration-candidate-v1
commit = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
phase = complete
clean_worktree = true
results = 21
failure_count = 0
fatal_error = null
overall = PASS
LOCAL_RELEASE_GATE = PASS
```

The same candidate recorded:

```text
FULL_UNIT_SUITE = PASS 279/279
R2_REAL_SANDBOX = PASS 13/13
R4 = PASS
R5 = PASS
R6 = PASS 8/8
R7_REAL_RECOVERY = PASS 4/4
```

The tested SHA matched PR #68 head. After explicit authorization, PR #68 was merged into `main` as:

```text
58feb12531982342bf3c12b9e8b8c61a5e819c5f
```

## Evidence location

Release-gate evidence is written outside the repository:

```text
%LOCALAPPDATA%\metaO\release-gate-evidence\gate-<timestamp>.json
```

The successful Roadmaps 2-7 run reported:

```text
C:\Users\Igor B\AppData\Local\metaO\release-gate-evidence\gate-20260825-103527.json
```

That exact JSON remains subject to the independent fail-closed validator tracked by Issue #73 / PR #69. Console PASS must not be silently substituted for independent JSON re-validation.

## Hosted-runner evidence

Repeated GitHub Actions runs fail with a pre-step fingerprint:

```text
job conclusion = failure
steps = null / []
runner_id = 0 on representative runs
logs = BlobNotFound / unavailable on several runs
checkout = NOT REACHED
setup = NOT REACHED
tests = NOT REACHED
```

Minimal diagnostics reproduced the problem on standard Ubuntu, Windows, and macOS hosted pools.

On the final validated candidate SHA, representative CI evidence includes:

```text
run = 32854214991
job = 97822118499
head_sha = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
steps = []
runner_id = 0
```

Therefore:

```text
METAO_TEST_LOGIC_CAUSE = NO
WORKFLOW_COMPLEXITY_CAUSE = NO
HOSTED_OS_SPECIFIC = NO
HOSTED_OS_SWITCH_WORKAROUND = NO
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
```

See Issue #71 and `docs/GITHUB-ACTIONS-SUPPORT-PACKET.md`.

## Active runtime pins

The executed gate uses:

```text
Python        = 3.13.x
openai-agents = 0.20.0
crewai        = 1.15.16
langgraph     = 1.2.11
```

The originally prepared OpenAI Agents `0.21.1` pin was rejected after real pip resolution proved its OpenAI client range incompatible with CrewAI `1.15.16`.

The active shared client range is compatible:

```text
openai-agents 0.20.0 -> openai >=2.45,<3
crewai 1.15.16       -> openai >=2.30,<3
shared range          -> openai >=2.45,<3
```

No Core or `OrchestratorContract` change was required.

## Provider-free deterministic runtime seams

The real-runtime gate does not require a paid provider call:

- OpenAI Agents `0.20.0` uses the test-only deterministic implementation in `tests/integration/_openai_agents_model.py`, built against the SDK public `Model` interface;
- CrewAI uses a deterministic local `BaseLLM`;
- LangGraph uses local deterministic graphs.

These seams are test infrastructure only and do not move framework SDK types or authority into Core.

## Prerequisites for future runs

- Windows PowerShell;
- Git;
- Python 3.13 available as `py -3.13` or `python`;
- network access when dependency installation is required;
- clean checkout unless running an explicitly diagnostic `-AllowDirty` invocation.

The isolated gate environment lives outside the repository:

```text
%LOCALAPPDATA%\metaO\release-gate-venv
```

## Running the gate for a future candidate

Run the gate from the exact candidate checkout that is intended to receive release authority. Do not reuse the historical Roadmap 7 SHA for a later release claim.

Example:

```powershell
cd C:\path\to\candidate-checkout
git status --short
git rev-parse HEAD
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1
```

For a diagnostic rerun with an already validated exact dependency environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-local-release-gate.ps1 -SkipInstall
```

Dirty worktrees fail closed. `-AllowDirty` exists only for diagnosis and records `clean_worktree=false`; such a run is not valid release evidence.

## Executed gate set

The release gate records 21 checks:

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

Normal test gates continue after individual failures so a completed failed run contains the entire failing set rather than stopping at the first red gate.

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

## Historical failed attempts

Failures before the final green run remain audit evidence:

- PowerShell parser defect -> `HARNESS_FAIL` before functional tests;
- missing Python 3.13 -> `BOOTSTRAP_FAIL` before functional tests;
- OpenAI Agents `0.21.1` / CrewAI `1.15.16` resolver conflict -> bootstrap failure before functional tests;
- generated `egg-info` dirty-worktree state -> bootstrap failure before functional tests;
- first complete candidate `f16bb92cda77ede8299b6238a0561ed362070b71` -> `TEST_FAIL`, 21 results / 8 failures.

Those concrete defects were corrected without weakening architecture or assertions. The later `aa9e4e9a...` run is the authoritative Roadmaps 2-7 local functional result.

## Evidence semantics

A successful local gate may establish:

```text
LOCAL_EXECUTION = PASS
FUNCTIONAL_REGRESSION = PASS on recorded commit
REAL_PROVIDER_FREE_RUNTIME_SANDBOXES = PASS
SDK_NEUTRAL_BOUNDARY = PASS
```

It does **not** by itself establish:

```text
GITHUB_ACTIONS = PASS
REMOTE_EXECUTION = PASS
PRODUCTION_READY = YES
SECURITY_CERTIFIED = YES
SLO_VALIDATED = YES
```

The external hosted-runner blocker remains separate until a hosted job reaches configured steps.

## Current status

```text
LOCAL_GATE_IMPLEMENTATION = OPERATIONAL
VALIDATED_CANDIDATE = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
LOCAL_RELEASE_GATE = PASS 21/21
FUNCTIONAL_PASS = CLAIMED_FOR_VALIDATED_SHA
PR_68 = MERGED
MAIN = 58feb12531982342bf3c12b9e8b8c61a5e819c5f
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
EXACT_JSON_VALIDATION = BLOCKED_EVIDENCE_FILE_UNAVAILABLE
```
