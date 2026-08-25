# metaO Release Readiness

Status: ROADMAP 2-7 CANONICAL ASSEMBLY COMPLETE — LOCAL FUNCTIONAL GATE EXECUTED WITH FAILURES; MERGE GATE PENDING.

This document separates executed evidence from assembled-but-unexecuted capability.

## Last merged and actually executed baseline

```text
main = 628b73409aa596bdcea7cf39136f455a0c220b05
full regression = 171/171 PASS
```

Real runtime evidence already executed on that merged line:

- LangGraph 1.2.11;
- CrewAI 1.15.16 with deterministic local BaseLLM;
- Block O O1-O5;
- two-runtime selection/failover/governance;
- declarative runtime catalog;
- durable runtime quarantine;
- runtime control CLI;
- framework-neutral `OrchestratorContract`;
- independent metaO acceptance.

Those historical PASS results do not validate the later Roadmap 2-7 draft stack.

## Canonical Roadmap 2-7 candidate

PR #68 / `roadmap7/integration-candidate-v1` is the single cumulative merge surface.

It supersedes individually merging the historical stacked PRs after executable validation.

The candidate assembles:

- deterministic advisory runtime feedback;
- SDK-neutral runtime conformance and fail-closed admission;
- durable certification, freshness, revocation and latest-verdict authority;
- declarative certified onboarding and certificate reuse;
- OpenAI Agents + CrewAI + LangGraph runtime adapters/regressions;
- failure-aware deterministic replanning;
- bounded durable human escalation;
- heterogeneous three-runtime recovery;
- independent metaO acceptance;
- reproducible Windows local release gate.

Critical certification invariant:

```text
for orchestrator_id + runtime_version + probe_execution_id
ONLY THE LATEST CERTIFICATE GENERATION IS AUTHORITATIVE
```

Never fall back to an older PASS behind a newer FAIL, revoked PASS or stale generation.

## Runtime compatibility correction

The originally prepared Roadmap 6 third-runtime pin was:

```text
OpenAI Agents SDK 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

The first real local pip resolution attempt proved that exact joint set is impossible:

```text
openai-agents 0.21.1 -> openai >=3,<4
crewai 1.15.16       -> openai >=2.30,<3
result                -> ResolutionImpossible
```

No functional test executed in that attempt.

Upstream package metadata provides a compatible OpenAI Agents version while preserving the selected runtime and thin synchronous adapter architecture:

```text
openai-agents 0.20.0 -> openai >=2.45,<3
crewai 1.15.16       -> openai >=2.30,<3
shared range          -> openai >=2.45,<3
```

The active canonical runtime set is therefore:

```text
OpenAI Agents 0.20.0
CrewAI 1.15.16
LangGraph 1.2.11
Python 3.12.x
```

The correction does not modify metaO Core, `OrchestratorContract`, selection authority, policy, budget, approval, acceptance or replan semantics.

Because OpenAI Agents 0.20.0 predates the packaged `agents.testing.ScriptedModel` utility used by the originally prepared tests, provider-free integration tests now use the metaO-owned test-only helper `tests/integration/_openai_agents_model.py` built against the SDK public `Model` interface.

See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

Historical Roadmap 6 documents may still mention 0.21.1 when describing the originally evaluated/prepared state; those statements are retained for audit history and are superseded by the compatibility-correction document for all current executable gates and merge decisions.

## Architecture preserved

```text
CORE_CHANGED_FOR_FRAMEWORK = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IMPORT_IN_CORE = NO
PAID_PROVIDER_REQUIRED_FOR_SANDBOX = NO
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

No fourth runtime, learned routing, Kubernetes, cloud/distributed database expansion or framework-specific recovery authority was introduced.

## Roadmap 7 recovery authority

Prepared behavior remains:

```text
runtime/transient/timeout failure
-> deterministic replan when policy allows
-> exhausted automatic replan budget
-> durable WAITING_APPROVAL only if an unattempted routable runtime remains
-> human approval
-> fresh health/quarantine snapshot
-> exactly one additional unattempted runtime attempt
-> independent metaO acceptance
```

Safety properties remain:

- runtime free-form text cannot manufacture metaO POLICY/BUDGET/ACCEPTANCE authority;
- prior failed runtimes are not retried by escalation approval;
- approval does not reset the mission or create an unbounded loop;
- attempt numbering and lineage continue across persistence/restart;
- existing pre-runtime approval stays compatible;
- no framework SDK type enters Core contracts.

## GitHub Actions execution blocker

GitHub-hosted Actions continues to fail before the first job step materializes.

Known evidence includes:

```text
PR #56 rerun 32731724864 / job 97451005960 -> steps = null / BlobNotFound
PR #61 run 32734246554 -> pre-step failure
PR #62 run 32734943310 / job 97455418118 -> steps = null
PR #63 run 32735224146 / job 97456307354 -> steps = null
PR #65 minimal Ubuntu diagnostic / job 97461133603 -> steps = null
PR #67 cross-OS diagnostic -> macOS, Windows and Ubuntu all steps = null
PR #68 canonical candidate / job 97474055832 -> steps = null
```

No checkout, dependency installation or test command is known to have executed in those hosted jobs. They are external pre-execution blockers, not functional PASS/FAIL evidence for metaO code.

## Local executable evidence so far

The canonical local-gate path has produced these concrete findings:

```text
1. HARNESS_FAIL
   cause: PowerShell parser ambiguity in "$code:" and "$Phase:"
   correction: ${code}: and ${Phase}:
   metaO functional tests executed: NO

2. BOOTSTRAP_FAIL
   cause: Python 3.12 absent
   correction: install Python 3.12
   metaO functional tests executed: NO

3. BOOTSTRAP_FAIL / dependency resolver
   cause: openai-agents 0.21.1 and crewai 1.15.16 require disjoint openai major ranges
   correction: openai-agents 0.20.0, preserving selected runtime and architecture
   metaO functional tests executed: NO

4. BOOTSTRAP_FAIL / dirty worktree
   candidate: 8d5cd2b3d2d06643c8fcb5f404b2399b78948c68
   cause: generated src/metao_control_plane.egg-info/ in a repository without Python artifact ignore hygiene
   correction: add .gitignore coverage for generated Python packaging artifacts
   metaO functional tests executed: NO

5. TEST_FAIL / first complete local functional gate
   candidate: f16bb92cda77ede8299b6238a0561ed362070b71
   phase: complete
   clean_worktree: true
   results: 21
   failures: 8
   evidence: C:\Users\Igor B\AppData\Local\metaO\release-gate-evidence\gate-20260825-091038.json
   metaO functional tests executed: YES
```

Failed gate names in the first complete local functional gate:

```text
r2_wu05_feedback
r7_wu02_durable_escalation
full_unit_suite
r2_real_runtime_sandbox
r4_real_declarative_certified_runtimes
r5_real_certificate_lifecycle
r6_wu05_three_real_runtimes
r7_wu03_three_runtime_recovery
```

`full_unit_suite` includes the two individually failing unit gates and is therefore treated as a derived failure until exact test-method tracebacks prove an additional independent unit defect.

The integration failures are triaged bottom-up: first `r2_real_runtime_sandbox`, then the higher certification/lifecycle/three-runtime layers. Exact failing methods and tracebacks are required before modifying product code. No assertion, acceptance rule, certification rule or architectural boundary will be weakened merely to make the gate green.

The same completed gate reported PASS for Block O5 runtime swap and the SDK-neutral Core/control-plane boundary.

These failures are useful executable evidence. The earlier bootstrap/harness findings are not functional code failures; item 5 is a valid functional TEST_FAIL and must be corrected before merge.

## Required next execution

Use the already-created isolated Python 3.12 gate venv to capture exact tracebacks for the named failing gates without reinstalling dependencies or rerunning the complete 21-gate battery.

After concrete defects are corrected, rerun focused affected gates first, then repeat the full local gate from a clean checkout of the new frozen PR #68 head.

Required result for local functional validation:

```text
clean_worktree = true
phase = complete
fatal_error = null
failure_count = 0
overall = PASS
```

If the run returns `TEST_FAIL`, fix only concrete failing gates and repeat the complete gate. If it returns `BOOTSTRAP_FAIL` or `HARNESS_FAIL`, correct the environment/harness without misclassifying the result as a metaO functional failure.

## Merge rule

Do not merge PR #68 while executable functional evidence is failing or absent.

After a verified local PASS on the exact candidate SHA:

1. review the JSON evidence;
2. verify the tested SHA equals PR #68 head;
3. keep hosted Actions status explicitly separate while the external blocker remains;
4. do not individually merge historical stacked PRs #56-#64 or component PR #66;
5. only make PR #68 merge-eligible under the agreed green-gate policy and explicit merge authorization.

## Current evidence status

```text
LAST_MERGED_EXECUTED_FULL_SUITE = 171/171 PASS
CANONICAL_PR_68_ASSEMBLY = COMPLETE
THIRD_RUNTIME = OpenAI Agents SDK
ACTIVE_OPENAI_AGENTS_PIN = 0.20.0
CREWAI_PIN = 1.15.16
LANGGRAPH_PIN = 1.2.11
DEPENDENCY_CONFLICT_0_21_1 = CONFIRMED
COMPATIBILITY_CORRECTION = APPLIED
THREE_RUNTIME_LIFECYCLE_REGRESSION = PREPARED
FAILURE_AWARE_REPLAN = PREPARED
DURABLE_REPLAN_ESCALATION = PREPARED
THREE_RUNTIME_RECOVERY_REGRESSION = PREPARED
LOCAL_GATE_FIRST_COMPLETE_EXECUTION = TEST_FAIL
LOCAL_GATE_RESULTS = 21
LOCAL_GATE_FAILURES = 8
POST_BASELINE_FUNCTIONAL_PASS = NOT CLAIMED
REMOTE_EXECUTION = BLOCKED_EXTERNAL_PRE_STEP
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```

## Not claimed

The repository does not currently claim:

- executable validation of the complete Roadmap 2-7 candidate;
- production deployment readiness or SLO compliance;
- paid-provider production execution;
- scale/load characteristics not separately measured;
- Kubernetes/cloud/distributed-database readiness;
- learned routing/reinforcement learning;
- security certification or penetration-test completion.

## Next legitimate gate

The next legitimate step is **focused traceback capture for the 8 reported failed gates using the existing local gate environment**.

Until then:

- do not merge PR #68;
- do not convert pre-step Actions failures into functional failures;
- do not declare PASS without real output;
- do not weaken assertions or architectural gates;
- do not add another framework merely to keep feature count moving.