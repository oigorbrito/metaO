# metaO Traceability

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

## Traceability chain

Stakeholder goal -> requirement -> architecture component -> implementation -> test/evidence -> quality characteristic -> acceptance criterion -> issue / PR

## Representative mappings

| GOAL | REQUIREMENT | ARCHITECTURE | IMPLEMENTATION | TEST / EVIDENCE | QUALITY | ACCEPTANCE | ISSUE / PR |
|---|---|---|---|---|---|---|---|
| Independent acceptance authority | acceptance must not equal execution success | Evidence -> Independent Acceptance | `src/metao/acceptance.py` | `tests/unit/test_block_j_acceptance_trust.py`, `tests/unit/test_chassis_l5_evidence_replay_v1.py` | Safety, reliability | deterministic fail-closed acceptance | #228 / #271 |
| Replaceable orchestrator runtimes | Core must remain adapter-neutral | OrchestratorContract -> Runtime Adapter | `src/metao/core.py`, `src/metao/adapters/*` | integration runtime tests | Compatibility, maintainability | two materially different runtimes pass through same Core | #163 / #206 |
| Durable failure handling | stale workers and failed steps must not corrupt state | Runtime / recovery | `src/metao/runtime.py`, `src/metao/sqlite_*` | `tests/unit/test_block_i_replan_failover.py`, `tests/unit/test_chassis_l5_budget_atomicity_v1.py` | Reliability | restart/failover preserves success and rejects stale ownership | #141 / #160 / #164 |
| Governance over mission work | policy, budget, approval must be metaO-owned | Policy / Budget | `src/metao/governance.py`, `src/metao/operator.py` | `tests/unit/test_block_k_governance_budget_approval.py` | Safety, reliability | execution cannot bypass governance | #140 / #142 |
| Exact-head release evidence | evidence must bind to current candidate state | release evidence / validator | `scripts/run-local-release-gate.ps1`, `scripts/validate_release_evidence.py` | local release gate docs and validator tests | Reliability, auditability | current evidence file matches exact SHA/branch | #73 / #69 |

## Rules

- a test only proves the requirement it directly exercises;
- documentation-only claims do not create implementation authority;
- old release evidence cannot be reused for a different head;
- issue/PR links are informative, not authoritative by themselves.

