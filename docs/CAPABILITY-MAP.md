# metaO Capability Map

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Qualified executable commit: `974bb9389ea34e409d8d9cff50b47f427f7877e2`
Date reconciled: 2026-09-09

A later documentation-only merge may advance repository `HEAD` without changing the executable evidence binding above. Any later change to product code, packaging, executable tests, or workflows must be requalified before inheriting these PASS claims.

This matrix is the primary convergence view for current implementation truth.

Legend:

- `Y` = present / evidenced
- `P` = partial / composed but not final-path complete
- `S` = specified only
- `B` = blocked externally or by dependency

| CAPABILITY_ID | CAPABILITY | OWNER_ISSUE | IMPLEMENTATION | LANGUAGE | MODULE | PUBLICLY_WIRED | FOCUSED_TEST | REGRESSION_TEST | INTEGRATION_TEST | MULTIPROCESS_TEST | REAL_RUNTIME | REAL_EXTERNAL_SYSTEM | ADVERSARIAL_TEST | CURRENT_LEVEL | BLOCKER | NEXT_REQUIRED_EVIDENCE | CLOSURE_CRITERION |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | Framework-neutral contract | #90 / #91 / #228 | implemented | Python | `src/metao/core.py` | Y | Y | Y | Y | N | N | N | P | L5 | none | exact current-head acceptance traceability | contract stays adapter-neutral |
| C02 | Independent acceptance | #228 / #271 | implemented | Python | `src/metao/acceptance.py` | Y | Y | Y | Y | N | N | N | P | L5-L6 | none | broader authoritative-source composition | acceptance remains separate from execution success |
| C03 | Fencing / restart / recovery | #164 / #141 / #160 | implemented | Python | `src/metao/runtime.py` | Y | Y | Y | P | N | N | N | P | L4-L5 | none | more complete operational fault evidence | stale workers remain rejected |
| C04 | Governance budget / approval | #140 / #142 | implemented | Python | `src/metao/governance.py`, `src/metao/operator.py` | Y | Y | Y | Y | N | N | N | P | L4-L5 | none | release-path budget/approval evidence on current head | budget/approval remain metaO-owned |
| C05 | Mission store / durable state | #175 / #176 / #177 | implemented | Python | `src/metao/mission_store.py`, `src/metao/sqlite_store.py` | Y | Y | Y | P | N | N | N | P | L4-L5 | none | stronger end-to-end persistence proof | mission state survives restart/replan |
| C06 | Runtime admission / health | #160 / #166 | implemented | Python | `src/metao/runtime_admission.py` | Y | Y | Y | Y | N | N | N | P | L4-L5 | none | authoritative health/admission coupling | unhealthy runtimes are excluded |
| C07 | Runtime certification / revocation | #162 / #167 | implemented | Python | `src/metao/runtime_certification*.py` | Y | Y | Y | Y | N | N | N | P | L5 | none | hosted/real evidence on current baseline | certificates are fresh and revocable |
| C08 | Adapter boundary for OpenAI/CrewAI/LangGraph | #163 / #206 / #228 | implemented | Python | `src/metao/adapters/` | Y | Y | Y | Y | N | P | N | P | L5-L6 | external provider/runtime constraints | adapters continue to preserve Core neutrality |
| C09 | Local release gate | #70 / #73 / #69 | operational evidence | Python | `scripts/run-local-release-gate.ps1` | Y | Y | Y | Y | N | P | N | P | L7 | exact evidence JSON file availability | validator and gate are rerunnable on the same candidate | local release evidence stays reproducible |
| C10 | Release evidence validator | #73 / #69 | implemented | Python | `scripts/validate_release_evidence.py` | Y | Y | Y | Y | N | N | N | N | L5 | none | revalidate exact evidence JSON when present | file-level evidence must match exact head |
| C11 | Project Discovery foundation | #174 / #176 | implemented | Rust | `metao-contracts::{discovery_coordinator,discovery_persistence}` | Y | Y | Y | Y | N | N | N | Y | L6 | none | remote issue reconciliation | Discovery can save, reopen and resume against exact ProjectContract binding |
| C12 | Two-runtime / three-runtime proof | #176 / #177 / #149 | partially implemented | Python | integration tests | P | Y | Y | Y | N | P | N | P | L5-L6 | provider/runtime availability | current runtime set still supported on exact candidate | multiple runtimes pass through same Core |
| C13 | Hostile boundary / adversarial closure | #165 / #167 / #92 | partially implemented | Python | `src/metao/security.py`, acceptance tests | P | Y | Y | P | N | N | P | P | L4-L5 | gap in end-to-end hostile external-system closure | adversarial matrix reaches terminal path | hostile trust fails closed |
| C14 | Hosted CI execution | #71 | blocked externally | n/a | GitHub Actions | B | N | N | N | N | N | N | N | L0-L1 | external pre-step blocker | hosted runner reaches configured steps | product truth remains separated from hosted CI |
| C15 | Rust Project Discovery composition | #170 / #175 / #176 / #177 | implemented | Rust | `metao-contracts`, `metao-testkit` | Y | Y | Y | Y | N | N | Y | Y | L6 | none | remote issue reconciliation | vague intent reaches SPEC_READY/ProjectCompletionGate only through explicit evidence and durable Discovery state reopens fail-closed |
| C16 | Rust governed execution composition | #140 / #141 / #142 / #160 | implemented | Rust | `execution_governance`, `runtime_health`, `failure_causality`, `execution_stage_evidence` | Y | Y | Y | Y | N | N | N | Y | L6 | none | Strategy/runtime integration beyond contract level | policy/risk/budget/health/failure/stage facts compose without authority leakage |
| C17 | Rust external-effect dedup with restart | #158 | implemented | Rust | `metao-testkit` local effect service | Y | Y | Y | Y | N | N | Y | P | L6 + REAL_EXTERNAL_SYSTEM | none | broader external provider coverage | tested logical effect deduplicates under lost ACK and restart |
| C18 | Rust multiprocess fencing | #164 | implemented | Rust | `metao-testkit` fence service | Y | Y | Y | Y | Y | N | N | P | L6 + MULTIPROCESS | none | distributed/hosted HA remains outside local proof | stale owner and stale DONE-like mutation are rejected |
| C19 | Rust two-runtime conformance | #145 | implemented | Rust | `metao-registry`, `metao-testkit` | Y | Y | Y | Y | N | N | N | P | L6 | real provider execution unavailable locally | real-runtime execution with external SDK/provider if required | two material runtime implementations share the same Core acceptance path |
| C20 | Rust composed closure system proof | #168 | implemented on final-closure branch | Rust | `metao-testkit/tests/composed_system_closure_tests.rs` | Y | Y | Y | Y | Y | N | Y | Y | L6 + MULTIPROCESS + REAL_EXTERNAL_SYSTEM + FAULT_INJECTION | real external orchestrator/provider not configured | final gates on exact branch SHA and remote landing | governance, lost ACK, health degradation, fencing, dedup, stage evidence and independent acceptance compose |
| C21 | Formal model execution | #161 / #327 | specified | TLA+ | `experiments/rust-chassis-a/formal` | S | N | N | N | N | N | N | N | L1 | `tlc`/`java` not available locally | run bounded TLC/equivalent checker | model invariants checked without treating them as implementation proof |
| C22 | Real credential broker lifecycle | #165 | specified/contracted | Rust/Python | credential lease contracts and historical docs | P | Y | Y | P | N | N | N | P | L4-L6 depending slice | no real broker configured locally | issue/renew/revoke lifecycle against safe broker | secret material absent from canonical evidence and lease binding enforced |
| C23 | Canonical operator initialization / bootstrap | #398 / #400 / #402 / #404 / #406 / #408 / #410 / #412 / #414 / #416 / #418 / #430 | implemented and integrated | Python | installed `metao` CLI, `runtime_factory`, declarative catalog, certification/admission, SQLite mission state | Y | Y | Y | Y | N | Y (LangGraph) | N | N | L6 + REAL_RUNTIME | none for local initialization; hosted CI separately blocked by #71 | repeat exact clean-room E2E after executable-surface changes | clean environment reaches doctor PASS, certified/admitted runtime, mission ACCEPTED, and separate-process observable inspect |
| C24 | README clean-room onboarding | #436 / #437 | implemented and integrated | Python | `README.md`, committed example runtime/catalog/mission, installed `metao` CLI | Y | Y | Y | Y | N | N (deterministic local runtime) | N | N | L6 | none locally; hosted CI separately blocked by #71 | repeat on executable-surface/documented-command changes | fresh clone/install follows documented commands to mission ACCEPTED and cross-process inspect without hidden app modules or credentials |
| C25 | Installed-console negative bootstrap | #438 / #439 | implemented and integrated | Python | `tests/integration/test_operator_bootstrap_negative_e2e.py`, installed `metao` CLI | Y | Y | Y | Y | N | N | N | Y | L6 | none locally; hosted CI separately blocked by #71 | repeat after CLI/bootstrap error-path changes | covered invalid first-run inputs fail early with structured state and no partial mission persistence |

## Operational/onboarding evidence binding

For C23-C25, the exact qualified executable context is:

```text
REPOSITORY = oigorbrito/metaO
BRANCH = main
QUALIFIED_EXECUTABLE_COMMIT = 974bb9389ea34e409d8d9cff50b47f427f7877e2
OS = Windows PowerShell clean-room clone
PYTHON = 3.12.10
ISOLATED_VENV = YES
INSTALLED_CLI = YES
UNIT_REGRESSION = current full suite PASS
README_QUICKSTART_E2E = PASS
README_EVIDENCE_GATE = PASS
NUMERIC_FOCUSED_REGRESSION = PASS
NUMERIC_HARD_GATE_AUDIT = RESOLVED
NEGATIVE_BOOTSTRAP_E2E = PASS
CANONICAL_INITIALIZATION_E2E = PASS
FIRST_MISSION = ACCEPTED
CROSS_PROCESS_INSPECT = PASS
FINAL_WORKTREE = CLEAN
HOSTED_CI = BLOCKED_EXTERNAL_PRE_STEP (#71)
```

The initialization E2E uses a real LangGraph runtime locally but no external model/provider call. Therefore `REAL_RUNTIME = Y` for C23's runtime boundary while `REAL_EXTERNAL_SYSTEM = N` for this claim. C24 deliberately uses a deterministic committed local runtime so README onboarding has no hidden credential/provider dependency. C25 proves installed-console negative paths and absence of partial mission persistence for the covered cases.

## Notes

- `PUBLICLY_WIRED` means the capability is reachable from a public API or entry point, not that it is final closure.
- `REAL_RUNTIME` is reserved for real runtime evidence, not deterministic test doubles.
- `REAL_EXTERNAL_SYSTEM` is only `P` where the repo explicitly documents provider/external-system reach.
- `MULTIPROCESS_TEST` is only `Y` when more than one process boundary is evidenced, not when two objects exist.
- C23-C25 local PASS and C14 hosted CI BLOCKED are intentionally independent claims: `LOCAL_OPERABILITY_PASS != HOSTED_CI_PASS`.
- A documentation-only merge may advance repository HEAD while retaining evidence binding to the exact executable commit above; later executable-surface changes require requalification.
