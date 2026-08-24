# metaO Release Readiness

Status: ROADMAP 7 FUNCTIONAL ASSEMBLY COMPLETE — EXECUTION AND MERGE GATES PENDING.

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

Those historical PASS results do not validate the later draft stack.

## Canonical Roadmap 2-5 candidate

PR #56 / `roadmap6/integration-candidate-v1` remains the canonical cumulative integration candidate for Roadmaps 2-5.

It assembles:

- deterministic advisory runtime feedback;
- SDK-neutral runtime conformance;
- fail-closed runtime admission;
- durable PASS/FAIL certification;
- exact certificate reuse;
- certificate freshness;
- immutable revocation;
- certification lifecycle CLI;
- latest exact certification verdict authority.

Critical invariant:

```text
for orchestrator_id + runtime_version + probe_execution_id
ONLY THE LATEST CERTIFICATE GENERATION IS AUTHORITATIVE
```

Never fall back to an older PASS behind a newer FAIL, revoked PASS or stale generation.

PR #56 remains draft/unmerged and has no post-stack PASS claim.

## Roadmap 6 — third runtime

Roadmap 6 selected and prepared:

```text
OpenAI Agents SDK 0.21.1
```

Stack:

- PR #57 — current third-runtime evaluation/selection;
- PR #58 — thin OpenAI Agents adapter using `run_sync`/`final_output` duck typing;
- PR #59 — three-real-runtime declarative regression;
- PR #60 — Roadmap 6 closeout/readiness.

Prepared exact-pin runtime set:

```text
OpenAI Agents 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

Roadmap 6 preserves:

```text
CORE_CHANGED_FOR_FRAMEWORK = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IMPORT_IN_CORE = NO
PAID_PROVIDER_REQUIRED_FOR_SANDBOX = NO
```

## Roadmap 7 — failure-aware recovery authority

Roadmap 7 addressed a control-plane gap instead of adding another framework.

### PR #61 — failure-aware replan authority

The repository already had framework-neutral `FailureClass`, `ControlAction`, `ReplanLimit` and `replan.evaluate()`, but the real mission loop did not consume them.

Prepared behavior:

- runtime/timeout/transient failures may `REPLAN`;
- cancellation `HALT`s;
- exact automatic attempt exhaustion `ESCALATE`s;
- runtime free-form error text cannot manufacture metaO `POLICY`, `BUDGET` or `ACCEPTANCE` authority;
- framework SDK types remain outside Core/control-plane contracts.

### PR #62 — durable bounded replan escalation

Prepared durable human recovery semantics:

```text
replan limit reached
+ unattempted routable runtime exists
-> WAITING_APPROVAL
-> bound durable ApprovalRequest
-> human approval
-> fresh health/quarantine snapshot
-> exactly ONE additional unattempted runtime attempt
```

Safety properties:

- prior failed runtimes are not retried by escalation approval;
- approval does not reset the mission;
- approval does not create another automatic loop;
- current outcome budget snapshot is preserved;
- attempt numbering and lineage continue;
- existing pre-runtime approval remains compatible;
- no SQLite schema migration was required.

### PR #63 — real three-runtime recovery regression

Prepared heterogeneous recovery proof:

```text
OpenAI Agents runtime failure
-> REPLAN
-> CrewAI timeout
-> replan limit
-> durable human approval
-> LangGraph one-shot continuation
-> independent metaO acceptance
```

Also prepared:

- quarantine of the remaining runtime after waiting;
- SQLite restart between wait / approve / resume;
- exact fresh certificate reuse across restart;
- proof that already-attempted real runtimes are not re-executed after approval.

WU03 adds no production code.

### PR #64 candidate — Roadmap 7 closeout

`roadmap7/wu04-closeout-readiness` records the assembled Roadmap 7 state and updates this readiness document.

## Deliberately rejected scope

Roadmap 7 did not add a separate durable `replan_action` field because the repository already persists:

- `MissionAttempt.failure_class`;
- `MissionState.history`;
- `MissionRunContext.max_attempts`.

Adding a redundant action field would require a SQLite migration without proportional audit value.

Also not added:

- repeated human escalation generations;
- retries of already-failed runtimes after escalation;
- learned recovery policy;
- arbitrary runtime override by framework-specific hooks;
- fourth orchestrator framework;
- Kubernetes/cloud/distributed database expansion.

## GitHub Actions execution blocker

GitHub-hosted Actions continues to fail before the first job step materializes.

Canonical controlled rerun evidence:

```text
PR #56 workflow run = 32731724864
run_attempt = 2
job_id = 97451005960
steps = null
logs = BlobNotFound
```

Roadmap 7 reproduced the same pre-execution class:

```text
WU01 workflow run = 32734246554
conclusion = failure

WU02 workflow run = 32734943310
job_id = 97455418118
steps = null

WU03 workflow run = 32735224146
job_id = 97456307354
steps = null
```

No checkout, dependency installation or test command is known to have executed in these jobs. Therefore the failures are classified as external pre-execution blockers, not functional PASS/FAIL evidence for metaO code.

## Required execution order

No draft stack is merge-eligible until executable output confirms the gates.

Required order:

1. execute PR #56 canonical Roadmap 2-5 candidate;
2. fix any concrete regression without weakening Core boundaries;
3. execute Roadmap 6 OpenAI Agents adapter/conformance;
4. execute Roadmap 6 three-runtime lifecycle regression;
5. execute Roadmap 7 WU01 failure-aware replan regression;
6. execute Roadmap 7 WU02 durable escalation + SQLite restart regression;
7. execute Roadmap 7 WU03 exact-pin heterogeneous recovery regression;
8. run full unit suite;
9. run real LangGraph/CrewAI/OpenAI Agents sandboxes;
10. run Block O O1-O5;
11. verify installed CLI compatibility and SDK-neutral source boundary;
12. only then build/merge a clean canonical consolidation path.

Do not merge all historical stacked PRs individually merely because implementation is assembled.

## Current evidence status

```text
LAST_MERGED_EXECUTED_FULL_SUITE = 171/171 PASS
CANONICAL_PR_56_IMPLEMENTATION = ASSEMBLED
ROADMAP_6_FUNCTIONAL_ASSEMBLY = COMPLETE
ROADMAP_7_FUNCTIONAL_ASSEMBLY = COMPLETE
THIRD_RUNTIME = OpenAI Agents SDK 0.21.1
THREE_RUNTIME_LIFECYCLE_REGRESSION = PREPARED
FAILURE_AWARE_REPLAN = PREPARED
DURABLE_REPLAN_ESCALATION = PREPARED
THREE_RUNTIME_RECOVERY_REGRESSION = PREPARED
POST_BASELINE_TEST_PASS = NOT CLAIMED
REMOTE_EXECUTION = BLOCKED_EXTERNAL
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```

## Not claimed

The repository does not currently claim:

- production deployment readiness or SLO compliance;
- executable validation of the draft Roadmap 2-7 stack;
- paid provider production execution;
- scale/load characteristics not separately measured;
- Kubernetes/cloud/distributed-database readiness;
- learned routing/reinforcement learning;
- security certification or penetration-test completion.

## Next legitimate gate

The next legitimate gate is **executable evidence**, followed by canonical stack consolidation after green results.

Until then:

- do not merge PR #56 or the stacked Roadmap 6/7 PRs;
- do not convert pre-step Actions failures into functional code failures;
- do not declare PASS without real output;
- do not add another framework merely to keep feature count moving.
