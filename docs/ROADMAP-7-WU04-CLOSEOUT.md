# Roadmap 7 WU04 — Closeout / Readiness

Date: 2026-08-24

## Final status

```text
ROADMAP_7_FUNCTIONAL_ASSEMBLY = COMPLETE
ROADMAP_7_EXECUTION = PENDING
ROADMAP_7_REMOTE_EXECUTION = BLOCKED_EXTERNAL
ROADMAP_7_MERGE_GATE = PENDING
ROADMAP_7_PRODUCTION_CLAIM = NO
```

No Roadmap 7 test is declared PASS because no Roadmap 7 workflow reached an executable step on GitHub-hosted Actions.

## What Roadmap 7 fixed

Roadmap 7 closed a real control-plane gap rather than adding another framework.

Before Roadmap 7:

- framework-neutral `replan.py` already defined failure classes and `REPLAN/HALT/ESCALATE` actions;
- the real `execute_mission()` loop did not consume that authority;
- failed attempts simply moved to another runtime until `max_attempts` was exhausted;
- runtime free-form error text could classify as words such as policy/budget even though those are metaO authorities;
- replan-limit escalation had no durable human continuation path.

After Roadmap 7 assembly:

### WU01 — failure-aware replan authority — PR #61

- `execute_mission()` consumes `replan.evaluate()`;
- recoverable runtime/timeout/transient failures may replan;
- cancellation halts;
- exact attempt exhaustion escalates;
- runtime error text is advisory only for runtime recovery classes;
- policy/budget/acceptance authority cannot be manufactured by SDK error strings;
- `OrchestratorContract` unchanged.

### WU02 — durable bounded replan escalation — PR #62

- replan-limit outcome becomes durable `WAITING_APPROVAL` only when an unattempted routable runtime remains;
- human approval authorizes exactly one additional attempt;
- prior failed runtimes cannot be retried by that approval;
- health/quarantine is re-read at resume time;
- attempts, history, approval binding and current budget snapshot remain durable;
- existing pre-runtime approval remains compatible;
- SQLite schema did not need a migration.

### WU03 — real three-runtime recovery regression — PR #63

Prepared exact-pin proof with:

```text
OpenAI Agents SDK 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

Expected real recovery path:

```text
OpenAI Agents failure
-> REPLAN
-> CrewAI timeout
-> replan limit
-> durable human approval
-> LangGraph one-shot continuation
-> independent metaO acceptance
```

The regression also covers quarantine after escalation and SQLite restart with exact certificate reuse.

WU03 changes no production code.

## Deliberately skipped work

A proposed work unit to persist an additional `replan_action` field was not implemented.

Reason:

- `MissionAttempt.failure_class` is already durable;
- `MissionState.history` is already durable;
- `MissionRunContext.max_attempts` is already durable;
- adding another field would have required a SQLite schema migration while mostly duplicating derivable audit information.

This was rejected as unnecessary scope.

## GitHub Actions evidence

The external pre-execution blocker reproduced on every new Roadmap 7 workflow checked.

Observed examples:

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

The canonical PR #56 controlled rerun also previously reproduced the same class of failure with `steps = null` and `BlobNotFound` logs.

Therefore this is still treated as an external runner/pre-execution blocker, not a functional metaO test result.

## Architecture invariants preserved

```text
META_ORCHESTRATOR_SCOPE = PRESERVED
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IN_CORE = NO
LEARNED_ROUTING = NO
POLICY_AUTHORITY_IN_METAO = YES
BUDGET_AUTHORITY_IN_METAO = YES
APPROVAL_AUTHORITY_IN_METAO = YES
REPLAN_AUTHORITY_IN_METAO = YES
QUARANTINE_AUTHORITY_IN_METAO = YES
INDEPENDENT_ACCEPTANCE_AUTHORITY_IN_METAO = YES
```

## Merge/readiness rule

No Roadmap 7 PR is merge-eligible while its dependency chain is unvalidated.

Required execution order remains:

1. validate canonical PR #56;
2. validate Roadmap 6 third-runtime stack;
3. validate Roadmap 7 WU01 focused + full regressions;
4. validate Roadmap 7 WU02 durable approval/restart regressions;
5. validate Roadmap 7 WU03 exact-pin three-runtime recovery;
6. run full unit suite, Block O O1-O5 and SDK-neutral boundary gates;
7. only then build a clean canonical consolidation/merge path.

Do not merge the historical stacked PRs individually merely because implementation is complete.

## Next gate

The next legitimate gate is executable evidence and stack consolidation after green tests.

Do **not** add a fourth runtime, distributed infrastructure, learned routing or a new approval subsystem merely to keep feature development moving while execution remains unavailable.
