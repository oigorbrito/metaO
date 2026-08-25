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

## Current canonical candidate local evidence

The first complete executable local gate on the synchronized Roadmap 7 candidate reached all 21 gates on a clean Windows worktree and produced a valid functional failure result:

```text
candidate = f16bb92cda77ede8299b6238a0561ed362070b71
branch = roadmap7/integration-candidate-v1
phase = complete
clean_worktree = true
results = 21
failures = 8
overall = TEST_FAIL
```

Evidence path reported by the local gate:

```text
C:\Users\Igor B\AppData\Local\metaO\release-gate-evidence\gate-20260825-091038.json
```

Failed gate names:

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

`full_unit_suite` includes the two named failing unit gates, so it is not yet evidence of an independent third unit defect. The integration failures are intentionally triaged bottom-up: first the R2 real-runtime sandbox, then the higher certification/lifecycle/three-runtime layers. Exact failing test methods and tracebacks are still required before any product-code correction; no assertion or architectural gate will be weakened merely to make the release gate green.

The same completed gate also reported PASS for Block O5 runtime swap and the SDK-neutral Core/control-plane boundary.

## Active runtime pins

```text
OpenAI Agents = 0.20.0
CrewAI = 1.15.16
LangGraph = 1.2.11
Python = 3.12.x
```

The OpenAI Agents compatibility correction remains active: `0.21.1` is historical audit context only and is not an executable release pin.

## Hosted Actions

GitHub-hosted Actions remain classified as `BLOCKED_EXTERNAL_PRE_STEP`: prior minimal and cross-OS diagnostics failed before repository checkout or any workflow step. Hosted failures therefore remain neither product PASS nor product FAIL until runner allocation/entitlement is remediated.

## Merge gate

No merge or production claim is authorized from the current evidence. Required next sequence:

1. capture exact failing test methods/tracebacks from the existing isolated local venv without reinstalling dependencies;
2. correct concrete defects only;
3. rerun focused affected gates;
4. rerun the entire 21-gate local release gate from a clean worktree on one frozen candidate SHA;
5. require `phase=complete`, `clean_worktree=true`, `failure_count=0`, `overall=PASS` before considering merge authorization.
