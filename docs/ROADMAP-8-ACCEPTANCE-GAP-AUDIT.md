# Roadmap 8 — Acceptance A01–A20 Gap Audit

Status: AUDIT COMPLETE / NO PRODUCT CODE CHANGED.

Issue: #92

Baseline:

```text
main = 58feb12531982342bf3c12b9e8b8c61a5e819c5f
Roadmaps 2-7 local gate = PASS 21/21
full unit suite = PASS 279/279
```

This audit applies the evidence rule:

```text
PRIMITIVE_EXISTS != FINAL_PATH_PROVEN
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
```

Classification:

- `FINAL_PATH_PROVEN` — capability is materially present on the current terminal path and covered by existing executable evidence from the validated Roadmaps 2-7 candidate.
- `PARTIAL_COMPOSITION` — useful implementation exists, but a frozen invariant is not yet authoritative on the final path.
- `PRIMITIVE_ONLY` — standalone primitive/test exists but final acceptance does not consume it as authority.
- `BLOCKED_BY_DEPENDENCY` — implementation order depends on an already-open structural work unit.
- `MISSING` — no first-class implementation surface was found in current `main`.

## Matrix

| ID | Frozen requirement | Current surface / evidence | Classification | Remaining gap / order |
|---|---|---|---|---|
| A01 | executor `DONE` != accepted | `acceptance.evaluate_acceptance`, `control_plane.execute_mission_once`, Block J | FINAL_PATH_PROVEN | none for V1 |
| A02 | independent verifier | verifier identity/trust fields exist, but no first-class framework-neutral verifier registry/selection/execution boundary found | MISSING | candidate after canonical evidence boundary; donor audit required before BUILD |
| A03 | evidence binding | subject/state/context/policy/obligation binding in `acceptance.py`; Block J | FINAL_PATH_PROVEN | strengthen authoritative sources in A05/A07/A09 |
| A04 | stale evidence | `check_freshness`; separate hostile `security.verify_freshness`; Blocks J/M | PARTIAL_COMPOSITION | local final path exists; hostile attestation freshness is not composed into terminal acceptance |
| A05 | mutated authoritative state | `subject_state_id` mismatch fails stale | PARTIAL_COMPOSITION | final path receives `AcceptanceContext`; no independent authoritative subject-state re-read/CAS at terminalization |
| A06 | provenance | payload digest + provenance root + trusted root checks; security attestation primitive | PARTIAL_COMPOSITION | no authoritative provenance closure/DAG or hostile attestation binding on final path |
| A07 | authority | `authority_id` checked against `AcceptanceContext.authorized_authorities` | PARTIAL_COMPOSITION | authority set is supplied in context; no authoritative capability/delegation registry is terminal source of truth |
| A08 | approval | durable `MissionOperator` wait/approve/resume; mission store persists record | PARTIAL_COMPOSITION | approver identity is bound, but approver authority/capability is not independently validated |
| A09 | policy evidence | policy effect and `policy_bundle_id` binding exist | PARTIAL_COMPOSITION | immutable policy decision/root evidence and authoritative policy source are not fully composed |
| A10 | partial acceptance | missing/failed obligations -> `NOT_DONE`; Block J | FINAL_PATH_PROVEN | none for current V1 semantics |
| A11 | retry preservation | mission attempts, bounded replan, durable run context, escalation preserves attempted runtimes | PARTIAL_COMPOSITION | durable mission lineage exists, but final acceptance does not query an independent retry-history authority before terminal decision |
| A12 | cross-orchestrator evidence | LangGraph/CrewAI/OpenAI Agents normalize to acceptance envelope; Block L / Roadmaps 6-7 | BLOCKED_BY_DEPENDENCY | `main` exposes a second divergent public Core envelope; #90/PR #91 canonicalizes before expansion |
| A13 | conflicting evidence | duplicate IDs, duplicate/conflicting obligations, unexpected obligations fail closed | FINAL_PATH_PROVEN | none for current fixed-set aggregation |
| A14 | confidence | `apply_confidence_after_hard_gates` in governance; Block K | PRIMITIVE_ONLY | not applied by `evaluate_acceptance` / control-plane terminal path |
| A15 | human escalation | durable `WAITING_APPROVAL`, bounded replan escalation, resume path in `MissionOperator` | FINAL_PATH_PROVEN for local durable profile | Conductor HUMAN-task transport remains a foundation integration enhancement, not required to claim local durable semantics |
| A16 | auditability | `AcceptanceProof`, mission state/history, event ledger/SQLite stores | PARTIAL_COMPOSITION | one terminal proof cannot yet reconstruct every frozen A16 authority/policy/approval/retry/cost source from authoritative records |
| A17 | deterministic acceptance | deterministic aggregation/proof digest and replay; Block J | FINAL_PATH_PROVEN | keep deterministic final authority |
| A18 | acceptance verification cost | `AcceptanceBudget` tracks money/tokens/wall-time/attempts; control plane currently consumes verifier attempts only | BLOCKED_BY_DEPENDENCY | compose full accounting after #90/PR #91 is executable-green; Inspect AI limit/usage donor pattern already frozen |
| A19 | adversarial executor | Block J integrity tests + Block M trust/replay/revocation primitives | PARTIAL_COMPOSITION | port full false-DONE/stale/substitution/authority/retry/provenance attack matrix through one real terminal path |
| A20 | only metaO issues final acceptance | control plane maps execution result -> independent `evaluate_acceptance`; runtime success alone never terminal accept | FINAL_PATH_PROVEN | preserve invariant |

## Counts

```text
FINAL_PATH_PROVEN = 7
  A01 A03 A10 A13 A15 A17 A20

PARTIAL_COMPOSITION = 9
  A04 A05 A06 A07 A08 A09 A11 A16 A19

PRIMITIVE_ONLY = 1
  A14

BLOCKED_BY_DEPENDENCY = 2
  A12 A18

MISSING = 1
  A02
```

These counts are implementation-composition classifications, not new executable PASS counts.

## Sequencing decision

Roadmap 8 must not become a broad rewrite. The recommended order is:

```text
WU01  canonical EvidenceEnvelope boundary                 # already #90 / PR #91
  -> executable focused + full regression

WU02  AcceptanceBudget final-path accounting              # A18
  -> money + tokens + wall-clock + verifier attempts

WU03  independent VerifierPort / verifier registry        # A02
  -> donor audit first; no evaluator framework becomes final authority

WU04  authoritative terminal state/authority/policy read  # A05 + A07 + A09
  -> source-of-truth ports; no caller-owned terminal authority

WU05  confidence integration after hard gates             # A14
  -> cannot rescue BLOCK/STALE/NOT_DONE

WU06  adversarial terminal-path closure                    # A04/A06/A08/A11/A16/A19
  -> prove composed defenses, do not add features merely for count
```

WU02 remains ordered after WU01 because accounting belongs on the canonical evidence/acceptance boundary. WU03 can be designed independently, but should not be merged ahead of the canonical evidence contract if it emits or transforms evidence envelopes.

## Non-goals

```text
NO fourth orchestrator for feature count
NO learned routing
NO Kubernetes/distributed DB expansion
NO hand-rolled cryptography
NO weakening of hard gates
NO replacement of metaO final acceptance authority
```

## Next legitimate implementation

The first product-code change after this audit remains **Roadmap 8 WU01 executable validation**. If its execution remains externally blocked, the next safe independent engineering action is the **A02 verifier donor/fit audit** without merging a dependent terminal-path implementation.
