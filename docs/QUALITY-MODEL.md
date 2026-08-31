# metaO Quality Model

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

## Functional suitability

QUALITY_GOAL: control-plane behavior is complete for the committed operational slice.

WHY_IT_MATTERS_TO_METAO: metaO exists to govern and accept work, not just execute work.

MEASURABLE_CRITERION: mission selection, policy/budget handling, evidence normalization, and independent acceptance all have executable paths.

EVIDENCE_SOURCE: `src/metao/*.py`, unit tests, integration tests, release gate docs.

CURRENT_EVIDENCE_LEVEL: L5 to L6 depending on slice.

MISSING_EVIDENCE: not every roadmap item has the same path maturity.

CLOSURE_GATE: end-to-end acceptance path on the authoritative candidate head.

## Reliability

QUALITY_GOAL: failures are classified and absorbed without corrupting durable state.

WHY_IT_MATTERS_TO_METAO: the control plane must survive partial execution, restart, and failover.

MEASURABLE_CRITERION: fencing, replay, recovery, retry history, and durable state tests pass.

EVIDENCE_SOURCE: `src/metao/runtime.py`, `src/metao/sqlite_*`, `tests/unit/test_block_i_replan_failover.py`, `tests/unit/test_chassis_l5_*`.

CURRENT_EVIDENCE_LEVEL: L4 to L6.

MISSING_EVIDENCE: full operational fault closure across all environments.

CLOSURE_GATE: restart/failover path proven on the current authoritative release slice.

## Compatibility / interoperability

QUALITY_GOAL: multiple orchestrator runtimes can pass through the same Core abstraction.

WHY_IT_MATTERS_TO_METAO: replaceability is a central architectural invariant.

MEASURABLE_CRITERION: at least two materially different orchestrators or runtime seams are adapted through the same Core contracts.

EVIDENCE_SOURCE: adapter modules, runtime tests, integration tests for OpenAI Agents, CrewAI, and LangGraph seams.

CURRENT_EVIDENCE_LEVEL: L5 to L6.

MISSING_EVIDENCE: hostile-boundary and broader cross-orchestrator parity remain distinct from simple adapter fit.

CLOSURE_GATE: proven adapter neutrality on the current canonical architecture.

## Security

QUALITY_GOAL: authority, provenance, and credentials fail closed.

WHY_IT_MATTERS_TO_METAO: acceptance is not allowed to mint trust from caller claims.

MEASURABLE_CRITERION: secret leakage prevention, authority binding, provenance binding, and stale-state rejection have executable tests.

EVIDENCE_SOURCE: `src/metao/acceptance.py`, `src/metao/security.py`, `tests/unit/test_block_j_acceptance_trust.py`, `tests/unit/test_block_m_hostile_trust.py`.

CURRENT_EVIDENCE_LEVEL: L4 to L5.

MISSING_EVIDENCE: full hostile external-system proof is not implied by local primitives.

CLOSURE_GATE: authoritative trust path with no caller-owned trust object admitted as final authority.

## Maintainability

QUALITY_GOAL: the code remains modular and replaceable.

WHY_IT_MATTERS_TO_METAO: Core must be stable while adapters and runtimes evolve.

MEASURABLE_CRITERION: clear module boundaries, low coupling across Core and adapters, tests that isolate behavior.

EVIDENCE_SOURCE: package layout, adapter modules, contract definitions, unit tests.

CURRENT_EVIDENCE_LEVEL: L3 to L5.

MISSING_EVIDENCE: no formal coupling metric is needed to claim this slice.

CLOSURE_GATE: architecture remains stable while higher-level capability work continues.

## Flexibility

QUALITY_GOAL: capability expansion happens by adaptation, not by rewriting Core.

WHY_IT_MATTERS_TO_METAO: new runtimes and policies are expected over time.

MEASURABLE_CRITERION: adding or replacing a runtime does not require Core acceptance semantics to change.

EVIDENCE_SOURCE: `src/metao/adapters/`, `src/metao/core.py`, roadmap 6-7 docs.

CURRENT_EVIDENCE_LEVEL: L4 to L6.

MISSING_EVIDENCE: wider runtime set still constrained by available evidence and external blockers.

CLOSURE_GATE: new runtime paths do not violate the frozen architecture.

## Safety

QUALITY_GOAL: control-plane failure behavior remains fail closed.

WHY_IT_MATTERS_TO_METAO: incorrect acceptance is a safety issue for the control plane.

MEASURABLE_CRITERION: missing, stale, duplicate, unauthorized, or conflicting evidence does not produce ACCEPT.

EVIDENCE_SOURCE: `src/metao/acceptance.py`, `tests/unit/test_chassis_invalid_states_v1.py`, `tests/unit/test_block_g_runtime_invariants.py`.

CURRENT_EVIDENCE_LEVEL: L5.

MISSING_EVIDENCE: final operational closure across all blocker classes.

CLOSURE_GATE: no hidden acceptance rescue path exists.

