# metaO Requirements Baseline

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Last reconciled commit: `0e6da02c7ec09c141bf5ae002ecbbea71fedc721`

## Project purpose

metaO provides a control plane for selecting, governing, supervising, and independently accepting orchestrator work.

## Stakeholder needs

- deterministic acceptance authority;
- replaceable orchestrator runtimes;
- durable governance over policy, budget, and approval;
- reproducible evidence and replay;
- operational clarity about what is built, wired, tested, and blocked.

## System requirements

- the system shall expose a framework-neutral `OrchestratorContract`;
- the system shall separate execution success from acceptance;
- the system shall preserve evidence binding to subject, state, policy, and obligations;
- the system shall support independent acceptance decisions;
- the system shall represent runtime health, admission, certification, and recovery.

## Software requirements

- current repository code shall remain adapter-neutral at Core boundaries;
- runtime-specific SDKs shall remain outside Core;
- evidence objects shall carry enough identity to replay acceptance deterministically;
- runtime and governance modules shall reject stale, conflicting, or unauthorized state.

## Architectural invariants

- `ORCHESTRATOR_DONE != METAO_ACCEPTED`
- current runtime selection must not require Core changes
- authoritative state must be read from the correct boundary, not caller strings alone
- hard gates must deny before score/confidence can rescue a decision

## Quality requirements

- reliability: fail closed, preserve progress, restart safely;
- security: isolate credentials, trust, authority, and provenance;
- interoperability: two materially different orchestrators through one Core abstraction;
- maintainability: clear module boundaries and bounded adapters;
- functional suitability: end-to-end mission governance through independent acceptance.

## Acceptance criteria

- focused tests cover the relevant unit boundaries;
- regression tests cover the current release path;
- integration tests exercise real runtime or provider-free runtime seams;
- operational evidence is explicit when claims exceed unit/regression evidence.

## Operational requirements

- keep release evidence tied to exact commit and run identity;
- keep external infrastructure blockers separate from product correctness;
- preserve worktree and historical evidence discipline;
- use GitHub as the persistent engineering ledger.

## Explicit non-goals

- formal ISO certification claims;
- cloud deployment claims;
- security certification claims without explicit evidence;
- production SLO claims without dedicated measurement;
- silent document promotion of historical plans into present authority.

## Deferred / future capabilities

- broader runtime diversity beyond current supported set;
- external hosted CI recovery;
- parity proofs for the Rust-native future product direction where not yet established.
