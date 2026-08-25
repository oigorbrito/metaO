# Roadmap 7 WU04 — Closeout / Readiness

Date: 2026-08-24

## Final status

```text
ROADMAP_7_FUNCTIONAL_ASSEMBLY = COMPLETE
ROADMAP_7_RUNTIME_COMPATIBILITY_CORRECTION = APPLIED
ROADMAP_7_EXECUTION_AFTER_FIX = PENDING
ROADMAP_7_REMOTE_EXECUTION = BLOCKED_EXTERNAL
ROADMAP_7_MERGE_GATE = PENDING
ROADMAP_7_PRODUCTION_CLAIM = NO
```

No Roadmap 7 functional PASS is declared because the corrected cumulative candidate has not yet completed an executable test battery.

## What Roadmap 7 fixed

Roadmap 7 closed a control-plane gap rather than adding another framework.

### WU01 — failure-aware replan authority — PR #61

- `execute_mission()` consumes framework-neutral replan authority;
- recoverable runtime/timeout/transient failures may replan;
- cancellation halts;
- exact attempt exhaustion escalates;
- runtime error text cannot manufacture metaO policy/budget/acceptance authority;
- `OrchestratorContract` remains unchanged.

### WU02 — durable bounded replan escalation — PR #62

- replan-limit outcome becomes durable `WAITING_APPROVAL` only when an unattempted routable runtime remains;
- human approval authorizes exactly one additional attempt;
- prior failed runtimes cannot be retried by that approval;
- health/quarantine is re-read at resume time;
- attempts, history, approval binding and current budget snapshot remain durable;
- existing pre-runtime approval remains compatible;
- no SQLite schema migration was required.

### WU03 — real three-runtime recovery regression — PR #63

Active executable set:

```text
OpenAI Agents SDK 0.20.0
CrewAI 1.15.16
LangGraph 1.2.11
```

The originally prepared OpenAI Agents 0.21.1 pin was superseded after the first real local pip resolution proved it incompatible with CrewAI 1.15.16. This version correction changes no metaO Core behavior. See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

Prepared recovery path:

```text
OpenAI Agents failure
-> REPLAN
-> CrewAI timeout
-> replan limit
-> durable human approval
-> LangGraph one-shot continuation
-> independent metaO acceptance
```

The regression also covers quarantine after escalation and SQLite restart with exact certificate reuse. WU03 changes no production code.

## Local executable evidence so far

The canonical local gate has produced environment/harness evidence only:

```text
PowerShell parser defect -> HARNESS_FAIL -> fixed
Python 3.12 absent -> BOOTSTRAP_FAIL -> environment corrected
0.21.1/CrewAI resolver conflict -> BOOTSTRAP dependency failure -> pin corrected to OpenAI Agents 0.20.0
```

No functional Roadmap 7 test had executed before the compatibility correction, so these outcomes are not functional test failures and cannot count as PASS.

## GitHub Actions evidence

Hosted Actions still fails before job steps materialize. Examples include Roadmap 7 workflows, the canonical candidate and minimal Ubuntu/Windows/macOS diagnostics with `steps = null`.

This remains external pre-execution infrastructure evidence, not a functional metaO result.

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

The dependency compatibility correction itself changes no `src/metao/**` file relative to the last locally attempted candidate SHA.

## Merge/readiness rule

PR #68 / `roadmap7/integration-candidate-v1` is now the canonical cumulative merge surface. Do not merge the historical Roadmap 6/7 stacked PRs individually.

Required next order:

1. update the local checkout to the exact current PR #68 head;
2. recreate the isolated gate venv after the failed resolver attempt;
3. execute the complete 21-gate local battery;
4. if `BOOTSTRAP_FAIL` or `HARNESS_FAIL`, correct only environment/harness mechanics and rerun;
5. if `TEST_FAIL`, fix concrete functional regressions without weakening architecture and rerun the complete gate;
6. if `PASS`, review JSON evidence and exact tested SHA;
7. only then consider the canonical candidate merge-eligible under the agreed green-gate policy;
8. keep hosted Actions explicitly separate until remote execution is repaired.

## Next gate

The next legitimate gate is executable evidence from the corrected canonical candidate.

Do **not** add a fourth runtime, distributed infrastructure, learned routing or a new approval subsystem merely to keep feature development moving.
