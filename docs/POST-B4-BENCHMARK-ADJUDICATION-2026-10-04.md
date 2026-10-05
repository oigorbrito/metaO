# Post-B4 Benchmark Battery Adjudication — 2026-10-04

Updated: 2026-10-05
Status: EVIDENCE_RECORD
Issue: #748
Applies to: repository `oigorbrito/metaO`

## 1. Scope

This document records the adjudication of the benchmark battery after B4.

It does not redefine the prior B2-B4 benchmarks and does not create product Acceptance authority.

The governing distinctions remain:

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
BENCHMARK_EVIDENCE != METAO_ACCEPTANCE
GAP_IDENTIFIED != PASS
```

## 2. Frozen prior battery: B2-B4

The prior benchmark evidence remains owned by PR #735,
`docs: record MetaO runtime and benchmark test evidence`.

That record defines and reports:

- B2 — MetaO workspace-write benchmark;
- B3 — executor comparison / supervision;
- B4 — cost proxy.

This post-B4 adjudication does not modify their definitions, evidence, results, or limitations.
B5 and B6 are later independent benchmarks and must not be retroactively folded into B2-B4.

## 3. B5 — decomposition -> execution -> recomposition

B5 evaluates whether metaO can:

1. decompose an original project/specification into work units;
2. execute those work units;
3. preserve dependency and contract semantics;
4. recompose the accepted outputs;
5. verify the recomposed project result against the original specification.

### Evidence identity

- Governing issue: #744
- Benchmark PR: #745
- Benchmark head: `ba1c8a9990390b3b140ba840bebdc63fa74a5513`
- Hosted workflow: `B5 Decomposition Recomposition Benchmark`
- Workflow run: `37250414857`
- Workflow result: success
- Product-gap follow-up: #746

### Observed result

The control fixture established:

- decomposition: PASS;
- work-unit execution: PASS;
- dependency preservation: PASS;
- local unit verification: PASS.

The adversarial fixture produced:

- left fragment: `A`;
- right fragment: `X`;
- both local work-unit verifiers: PASS;
- metaO project verdict: `PROJECT_ACCEPTED`;
- deterministic recomposition baseline: `AX`;
- original required composite: `AB`;
- original-spec verification: FAIL.

The current `ProjectSupervisionResult` / trace surface does not expose an explicit
project-level recomposition artifact or a project-level recomposition trace event.

### B5 re-adjudication — 2026-10-05

The historical run above remains the evidence that identified the gap.

The current integrated implementation candidate adds an explicit project recomposer,
an independent project-level original-spec verifier, and a fail-closed
`PROJECT_UNVERIFIED` terminal for local-only completion.

Current exact-head evidence:

- Integration PR: #767
- Exact head: `62442b873abd3955537a0813fc3bfea36ce6f1b5`
- Hosted workflow: `B5 Decomposition Recomposition Benchmark`
- Workflow run: `37336920793`
- Workflow result: success
- CI run on the same head: `37336921042` — success
- Release Evidence Validator: `37336921110` — success

The current B5 gate proves all three required paths:

- valid recomposition `AB` -> `PROJECT_ACCEPTED`;
- local-PASS/global-mismatch `AX` -> `PROJECT_BLOCKED`;
- local-only completion without project recomposition/original-spec verification
  -> `PROJECT_UNVERIFIED`, never `PROJECT_ACCEPTED`.

| Dimension | Status |
|---|---|
| Decomposition | PASS |
| Work-unit execution | PASS |
| Dependency preservation | PASS |
| Local unit verification | PASS |
| Recomposition | PASS |
| Original-spec verification after recomposition | PASS |
| Local-only fail-closed acceptance boundary | PASS |
| Aggregate B5 | PASS |

Claim boundary:

```text
LOCAL_WORK_UNIT_ACCEPTANCE != ORIGINAL_SPEC_SATISFIED
PROJECT_ACCEPTED_WITHOUT_RECOMPOSITION_EVIDENCE != B5_PASS
DECOMPOSITION_EXECUTION_PASS != RECOMPOSITION_PASS
```

B5 is therefore adjudicated as PASS on the exact integrated candidate head above.

This is benchmark/execution evidence for the candidate. It does not by itself mean the
product changes have been merged into `main`.

## 4. B6 — operational continuity

B6 evaluates continuity across checkpoints, handoffs, restart/resume, lineage,
ownership/fencing, and protection against duplicated effects.

B6 is independent of B5.

### Evidence identity

- Benchmark PR: #743
- Benchmark head: `b4c87e6df483594a884bd31d5f9a7e223c92a3d2`
- Hosted workflow: `B6 Continuity Benchmark`
- Workflow run: `37249025419`
- Workflow result: success
- Product-gap follow-up: #747

### Observed result

The current exact-head evidence establishes:

- mechanical project handoff: PASS;
- trusted Git/checkpoint handoff: PASS;
- corrective replan: PASS;
- remote checkpoint: PASS;
- durable SQLite mission restart/resume: PASS;
- observability across SQLite restart: PASS;
- CLI continuity across invocations: PASS;
- heterogeneous runtime restart/lineage: PASS.

The heterogeneous-runtime gate executed with pinned runtime versions and passed after
a benchmark-harness import-path defect was corrected. Earlier dependency/import failures
were harness/environment failures and are not metaO continuity failures.

Inspection of the Project Plane established that `supervise_project()` keeps material
supervision progress process-local. Repository checkpoint persistence does not serialize
the full supervision state required for a process-B restore after a real process-A crash.

Therefore the evidence does not establish:

- restoration of partially accepted Project Plane state after process death;
- rejection of stale ownership after takeover;
- prevention of repeated non-idempotent work/effects across the crash window;
- generalized external cross-provider handoff.

### B6 re-adjudication — 2026-10-05

The historical run above remains the evidence that identified the Project Plane gaps.

The current integrated candidate adds durable Project Plane snapshots, revision/CAS,
owner fencing, an atomic SQLite action-fence boundary, crash-safe resume, durable
logical accepted-result bindings, and explicit effect reconciliation.

Current exact-head evidence:

- Integration PR: #767
- Exact head: `62442b873abd3955537a0813fc3bfea36ce6f1b5`
- Hosted workflow: `B6 Continuity Benchmark`
- Workflow run: `37336920918`
- Workflow result: success
- CI run on the same head: `37336921042` — success
- Release Evidence Validator: `37336921110` — success

The B6 evidence payload reports:

| Dimension | Status |
|---|---|
| Mechanical project handoff | PASS |
| Durable mission restart/resume | PASS |
| Observability across SQLite restart | PASS |
| CLI continuity across invocations | PASS |
| Heterogeneous runtime restart/lineage | PASS |
| Project-process crash/resume | PASS |
| Duplicate-effect crash window | PASS |
| Cross-provider external handoff | NOT_PROVEN |
| Aggregate B6 | NOT_PROVEN |

The workflow itself succeeds because all currently executable gates pass and the payload
records the unresolved external handoff boundary explicitly. Workflow success is not an
aggregate B6 PASS.

Claim boundary:

```text
REPOSITORY_CHECKPOINT != PROJECT_PLANE_STATE
MISSION_RESTART_PASS != PROJECT_PROCESS_CRASH_RESUME_PASS
CHECKPOINT_CONTINUITY != EXACTLY_ONCE_EFFECT
HETEROGENEOUS_RUNTIME_RESTART_PASS != CROSS_PROVIDER_EXTERNAL_HANDOFF_PASS
```

B6 is therefore materially advanced: the Project Plane crash/resume and duplicate-effect
gaps are executed as PASS on the current exact head. Aggregate B6 remains
`NOT_PROVEN` solely because generalized cross-provider external handoff has not been
executed.

## 5. Battery disposition

The post-B4 battery now has explicit evidence and bounded claims for both independent
benchmarks.

| Benchmark | Disposition |
|---|---|
| B2 | Frozen prior evidence; unchanged here |
| B3 | Frozen prior evidence; unchanged here |
| B4 | Frozen prior evidence; unchanged here |
| B5 | PASS on current exact-head integrated evidence |
| B6 | NOT_PROVEN — cross-provider external handoff remains |

The battery is **re-adjudicated with one explicit unresolved B6 boundary**.

It is not an all-PASS battery. B5 now has exact-head PASS evidence. B6 has exact-head
PASS evidence for Project Plane crash/resume and duplicate-effect reconciliation, but
must not be promoted to aggregate PASS while cross-provider external handoff remains
`NOT_PROVEN`.

Product work is tracked separately:

- #746 / #761 — project-level recomposition, original-spec verification, and fail-closed local-only acceptance;
- #747 / #753 / #754 / #762 — durable Project Plane state, crash-safe resume, atomic fencing, and duplicate-effect protection;
- #765 / #767 — integrated candidate carrying the current exact-head evidence.

Merging benchmark or documentation PRs records the evidence state. It does not convert
`GAP_IDENTIFIED` into product PASS.
