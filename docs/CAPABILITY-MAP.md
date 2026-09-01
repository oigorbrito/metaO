# metaO Capability Map

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `5348605cbcfb3bc02f3076fe1723447feff3ecdd`

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

## Notes

- `PUBLICLY_WIRED` means the capability is reachable from a public API or entry point, not that it is final closure.
- `REAL_RUNTIME` is reserved for real runtime evidence, not deterministic test doubles.
- `REAL_EXTERNAL_SYSTEM` is only `P` where the repo explicitly documents provider/external-system reach.
- `MULTIPROCESS_TEST` is only `Y` when more than one process boundary is evidenced, not when two objects exist.
