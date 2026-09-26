# metaO Blocker Register

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Last reconciled commit: `4bedae3715ff30ce36cb183417f136400f1a8c91`

Current reconciliation note: the GitHub API was reachable during the 2026-09-26 audit. The exact-head `main` CI run `36213551526` completed with failure before any configured step (`steps=[]`), so it is recorded as an external pre-step blocker rather than a product test failure. Historical hosted-runner and API-authentication observations below remain evidence for their original runs.

## Current product blockers

| BLOCKER | TYPE | CURRENT_STATUS | IMPACT |
|---|---|---|---|
| Hosted GitHub Actions pre-step failure | external infrastructure | blocked-current-head | `main` run `36213551526` failed with `steps=[]`; hosted CI cannot be used as product PASS evidence |
| Exact release JSON file availability | evidence availability | blocked | independent revalidation of historical release evidence cannot proceed without the file |
| Real external runtime/provider execution | external provider / secret | blocked locally | Rust and Python conformance paths are not real provider execution without configured SDK dependencies/secrets |
| Real credential broker lifecycle | external/local infrastructure | blocked locally | provider-neutral credential lease contracts are not a real issue/renew/revoke broker lifecycle |
| Formal model execution | local toolchain | blocked | TLC/java are not available in the current environment |
| GitHub PR/issue API reconciliation | external API / auth | resolved for this audit | Read-only `gh` PR, issue, release and run queries succeeded on 2026-09-25; prior authentication failures remain historical evidence |

## Current operational blockers

| BLOCKER | TYPE | CURRENT_STATUS | IMPACT |
|---|---|---|---|
| `.smag/` workspace residue | local workspace hygiene | present | untracked local state exists in the checkout |
| `experiments/rust-chassis-a/target/` residue | local workspace hygiene | present | build output exists in the checkout |

## Current execution blockers observed during final closure

| BLOCKER_ID | BLOCKER_CLASS | AFFECTED_CAPABILITY | EXACT_COMMAND | EXACT_ERROR | HUMAN_OR_EXTERNAL_ACTION_REQUIRED | INDEPENDENT_WORK_REMAINING |
|---|---|---|---|---|---|---|
| PY_RUNTIME_DEPS | BLOCKED_TOOLCHAIN | Python real-runtime historical tests | `python -m unittest tests.integration.test_r6_wu05_three_real_runtimes tests.integration.test_r7_wu03_three_runtime_recovery` | `ModuleNotFoundError: No module named 'agents'` | install/use environment with required Python SDK dependencies | no; Rust closure work continued |
| PY_CREWAI_DEPS | BLOCKED_TOOLCHAIN | CrewAI historical runtime tests | `python -m unittest tests.integration.test_r6_wu04_openai_agents_real tests.integration.test_r2_wu01_second_real_runtime` | `ModuleNotFoundError: No module named 'crewai'` | install/use environment with CrewAI dependency if historical Python runtime proof must be rerun | no; Rust closure work continued |
| PY_LANGGRAPH_DEPS | RESOLVED_IN_HERMETIC_ENV | provider-free LangGraph integration tests | Python 3.13 temporary environment with `langgraph==1.2.11`; selected integration command plus O1 and canonical initialization | local Python 3.11 lacked the dependency; the declared hermetic environment passed | retain the hermetic dependency installation in the release path | 7/7 selected integration tests, O1 and initialization E2E passed |
| FORMAL_TLC | BLOCKED_TOOLCHAIN | bounded formal model execution | `where.exe tlc`; `where.exe java` | no matching executable found | provide TLC/java or equivalent model-checking toolchain | no; executable Rust tests continued |
| REAL_BROKER | BLOCKED_EXTERNAL | credential broker lifecycle | not executed | no safe local credential broker/provider configured | provide approved local broker/provider or revise acceptance criterion | no; provider-neutral composition continued |
| PYTHON312_GATE | BLOCKED_TOOLCHAIN | local release gate bootstrap | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-local-release-gate.ps1` | `Python 3.12 is required`; launcher reports no suitable 3.12 runtime | install/provide Python 3.12 for the declared release environment | gate aborted in bootstrap with `RESULTS = 0`; no release claim was made |

## Rules

- product blockers must not be collapsed into historical notes;
- external blockers must remain separate from implementation defects;
- a blocker is resolved only when the documented resolution condition is met.
