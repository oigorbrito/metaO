# metaO Capability Map

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

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
| C11 | Project Discovery foundation | #174 | partially implemented / planned slices remain | Python | `src/metao/control_plane.py`, `src/metao/catalog.py` | P | Y | Y | P | N | N | N | P | L3-L4 | remaining Project Discovery slices | end-to-end discovery/completion path | current docs separate product next steps from baseline |
| C12 | Two-runtime / three-runtime proof | #176 / #177 / #149 | partially implemented | Python | integration tests | P | Y | Y | Y | N | P | N | P | L5-L6 | provider/runtime availability | current runtime set still supported on exact candidate | multiple runtimes pass through same Core |
| C13 | Hostile boundary / adversarial closure | #165 / #167 / #92 | partially implemented | Python | `src/metao/security.py`, acceptance tests | P | Y | Y | P | N | N | P | P | L4-L5 | gap in end-to-end hostile external-system closure | adversarial matrix reaches terminal path | hostile trust fails closed |
| C14 | Hosted CI execution | #71 | blocked externally | n/a | GitHub Actions | B | N | N | N | N | N | N | N | L0-L1 | external pre-step blocker | hosted runner reaches configured steps | product truth remains separated from hosted CI |

## Notes

- `PUBLICLY_WIRED` means the capability is reachable from a public API or entry point, not that it is final closure.
- `REAL_RUNTIME` is reserved for real runtime evidence, not deterministic test doubles.
- `REAL_EXTERNAL_SYSTEM` is only `P` where the repo explicitly documents provider/external-system reach.
- `MULTIPROCESS_TEST` is only `Y` when more than one process boundary is evidenced, not when two objects exist.

