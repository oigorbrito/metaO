# metaO Blocker Register

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `19152a5451a55bdf354b14d4ac88f08f0c335187`

## Current product blockers

| BLOCKER | TYPE | CURRENT_STATUS | IMPACT |
|---|---|---|---|
| Hosted GitHub Actions pre-step failure | external infrastructure | blocked | hosted CI cannot be used as product PASS evidence |
| Exact release JSON file availability | evidence availability | blocked | independent revalidation of historical release evidence cannot proceed without the file |
| Real external runtime/provider execution | external provider / secret | blocked locally | Rust and Python conformance paths are not real provider execution without configured SDK dependencies/secrets |
| Real credential broker lifecycle | external/local infrastructure | blocked locally | provider-neutral credential lease contracts are not a real issue/renew/revoke broker lifecycle |
| Formal model execution | local toolchain | blocked | TLC/java are not available in the current environment |

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
| FORMAL_TLC | BLOCKED_TOOLCHAIN | bounded formal model execution | `where.exe tlc`; `where.exe java` | no matching executable found | provide TLC/java or equivalent model-checking toolchain | no; executable Rust tests continued |
| REAL_BROKER | BLOCKED_EXTERNAL | credential broker lifecycle | not executed | no safe local credential broker/provider configured | provide approved local broker/provider or revise acceptance criterion | no; provider-neutral composition continued |

## Rules

- product blockers must not be collapsed into historical notes;
- external blockers must remain separate from implementation defects;
- a blocker is resolved only when the documented resolution condition is met.

