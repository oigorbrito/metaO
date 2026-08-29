# metaO Acceptance Contract

Status: FROZEN for Block C (2026-08-23)

## 1. Purpose

The metaO acceptance layer is the final authority over whether an orchestrator execution is accepted. An orchestrator may report `DONE`, `SUCCESS`, or an equivalent terminal state, but that state is only an execution claim.

Invariant:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

Only metaO may produce the final acceptance decision for a mission/execution.

## 2. Architectural boundary

The acceptance contract is framework-neutral.

```text
LangGraph result       \
CrewAI result           > thin adapter -> metaO EvidenceEnvelope -> Acceptance
OpenAI Agents result   /
other orchestrators   /
```

The metaO Core MUST NOT import orchestrator-specific SDKs or expose orchestrator-specific types in its acceptance contract.

Replacing an orchestrator, including its agents, tools, memory, prompts, routing and workflows, MUST NOT require changes to the metaO Core acceptance semantics.

## 3. Decision model

The canonical acceptance semantics are:

- `ACCEPT` — all mandatory hard gates passed and acceptance requirements are satisfied.
- `NOT_DONE` — execution/evidence is well formed but mandatory acceptance work or evidence is incomplete or failed in a recoverable/non-terminal way.
- `STALE` — evidence, authority, state, trust or snapshot is older than the authoritative state required for acceptance.
- `BLOCK` — integrity, policy, authority, provenance, conflict, authenticity or other fail-closed condition prevents acceptance.
- `REQUIRE_HUMAN` — automatic acceptance cannot complete under policy/risk/confidence rules and durable human escalation is required.

Decision precedence for terminal safety is conceptually:

```text
BLOCK > STALE > REQUIRE_HUMAN > NOT_DONE > ACCEPT
```

A concrete implementation may encode this differently, but MUST preserve the safety semantics.

## 4. Framework-neutral EvidenceEnvelope

The implementation may choose concrete names, but the acceptance boundary MUST carry the following conceptual fields.

### Execution identity

- mission identity
- execution identity
- orchestrator identity
- adapter identity and version
- attempt identity
- run identity

### Subject binding

- subject identity
- authoritative subject state/version

### Verification binding

- verification context identity
- policy bundle identity/version/root
- required obligation/evidence-set identity
- evidence identity
- evidence payload digest/root

### Provenance and authenticity

- provenance chain/root
- verifier identity
- trust/issuer identity where applicable
- freshness/epoch/timestamp where applicable

### Governance evidence

- authority/capability evidence
- policy decision evidence
- approval evidence where required
- retry/recovery lineage evidence

### Quality/scoring

- verifier score(s), when applicable
- confidence, when applicable
- score/confidence explanation or reason binding

### Acceptance cost

- verification monetary cost
- verification token cost
- verification wall-clock time
- verifier/escalation attempt count

### Final decision evidence

- final acceptance decision
- deterministic decision reasons
- acceptance proof/digest sufficient for later audit

## 5. Hard gates before scoring

Scoring/confidence is never an authorization mechanism. Before any score or confidence may influence acceptance, the following hard gates MUST be evaluated:

1. schema / identity / binding integrity;
2. authoritative subject-state freshness;
3. provenance and authenticity requirements;
4. authority/capability requirements;
5. policy requirements;
6. required evidence/obligation completeness;
7. retry/recovery lineage integrity;
8. acceptance budget;
9. conflict, duplicate and evidence-set integrity;
10. quarantine or other explicit global governance gates when applicable.

Rule:

```text
HARD_GATE_DENY -> candidate cannot be rescued by score
```

## 6. Confidence semantics

Confidence is advisory after hard gates.

The following are forbidden:

```text
high confidence CANNOT override policy DENY
high confidence CANNOT override stale evidence
high confidence CANNOT override missing required evidence
high confidence CANNOT override unauthorized executor
high confidence CANNOT override provenance/authenticity failure
high confidence CANNOT override retry-history violation
high confidence CANNOT override budget exhaustion
```

Confidence may only influence:

- whether additional verification is required;
- whether a stronger verifier should run;
- whether a human escalation is required;
- ordering among otherwise eligible verification paths.

Confidence MUST be bound to the verifier identity, verification context, subject state and evidence payload it evaluates.

## 7. Partial and conflicting evidence

Missing mandatory evidence yields `NOT_DONE` unless a stricter integrity condition requires `BLOCK`.

Duplicate, substituted, unexpected or conflicting evidence MUST NOT be silently cherry-picked to manufacture acceptance.

Where a required evidence set is defined, metaO MUST evaluate that exact set or a policy-authorized version of it.

A best-of-N pattern that discards contradictory evidence is forbidden unless an explicit aggregation policy defines and audits that behavior.

## 8. Freshness and mutation

Acceptance evidence MUST be bound to the authoritative subject state/version that it verified.

If authoritative state advances after evidence generation, that evidence MUST be treated as stale unless policy explicitly proves that the change cannot invalidate the evidence.

Caller-supplied current state is not sufficient as the final source of truth at the terminal acceptance boundary.

## 9. Provenance

Every acceptance-critical evidence item MUST have provenance sufficient to establish:

- who/what produced it;
- what subject/state it refers to;
- what verification context/policy it used;
- the digest/root of the evaluated payload;
- the chain/root by which the verifier/issuer is trusted.

Unrelated provenance nodes, cycles, revoked/untrusted verifiers or digest substitutions MUST fail closed.

## 10. Authority

Execution authority and final acceptance authority are distinct.

An orchestrator/executor may have authority to perform work without having authority to declare that work accepted.

The metaO acceptance layer owns final acceptance authority.

Authority/capability inputs used at a durable terminal boundary MUST come from an authoritative source, not from caller strings alone.

## 11. Approval and human escalation

Human approval is a durable control-plane event, not an in-memory callback.

When policy requires a person:

```text
RUNNING -> REQUIRE_HUMAN -> durable wait -> APPROVE | REJECT -> resume/replan/block
```

The approval record MUST bind at least:

- mission/execution;
- subject state;
- requested action/decision;
- policy/approval rule;
- approver identity/authority;
- approval outcome;
- time/version/freshness information required by the trust profile.

A stale approval MUST NOT authorize a mutated subject state.

## 12. Retry preservation

Acceptance MUST use authoritative retry/recovery history when such history affects policy, cost or terminal eligibility.

A caller MUST NOT be able to omit prior attempts/cost events to reopen an acceptance path.

Retry/recovery lineage MUST preserve successful progress where safe while preventing historical omission, replay and budget reset.

## 13. Cross-orchestrator evidence

All orchestrator adapters MUST normalize their results into the same EvidenceEnvelope contract.

The envelope MUST carry `orchestrator_id` and `adapter_id/version`, but MUST NOT embed framework-specific SDK objects in the metaO Core.

Evidence from different orchestrators may be compared or composed only when subject, state, verification context, policy and evidence semantics are compatible and explicitly bound.

Cross-orchestrator proof is an implementation acceptance test for a later block; this contract is frozen now so those tests have a stable target.

## 14. Deterministic final acceptance

Evidence generation may use probabilistic models. The final metaO decision over the recorded evidence set MUST be deterministic for the same:

- policy bundle;
- authoritative state;
- trust context;
- evidence set;
- verifier outputs;
- acceptance budget state.

The acceptance result MUST be reproducible from the durable audit record.

## 15. AcceptanceBudget

Verification itself consumes resources and MUST be governed.

`AcceptanceBudget` is a metaO concept that MUST support, at minimum:

- maximum verification monetary cost;
- maximum verification token cost;
- maximum verification wall-clock time;
- maximum verifier/escalation attempts.

Budget exhaustion is a hard gate. It may produce `BLOCK`, `NOT_DONE`, `REQUIRE_HUMAN`, or a policy-defined escalation, but MUST NOT silently continue unbounded verification.

The budget mechanism is metaO-specific composition. Inspect AI cost/token/time-limit and usage-accounting patterns are approved donors for adaptation; they are not the acceptance authority.

## 16. Trust profiles

### LOCAL_TRUSTED_CONTROL_PLANE

Assumptions:

- metaO-owned durable state is trusted against ordinary callers/adapters;
- local SQLite/DB registries can be authoritative for issuance/history within the supported process/host boundary;
- callers cannot bypass the public control-plane boundary by executing arbitrary code inside the same trusted process.

OMA local durable registries and validation-closure patterns are valid donors under this profile.

### HOSTILE_OR_DISTRIBUTED_BOUNDARY

Assumptions may include hostile processes, remote orchestrators, compromised transport, untrusted storage/operator domains, or independent trust roots.

Required rule:

```text
USE STANDARD CRYPTOGRAPHY / ATTESTATION PROTOCOLS
DO NOT INVENT CRYPTOGRAPHY IN METAO
```

Approved references/adoption candidates include in-toto and Sigstore/Cosign/Rekor semantics for signed attestations, verification, timestamps/transparency and hostile-boundary authenticity.

## 17. Adversarial executor rule

An executor is treated as untrusted with respect to final acceptance claims.

The acceptance path MUST remain safe if an executor attempts to:

- declare false `DONE`;
- submit evidence for the wrong subject/state;
- replay or duplicate evidence;
- omit failed evidence or historical retries;
- fabricate caller-owned authority objects;
- substitute stale state;
- alter evidence after verification;
- submit unexpected evidence to manipulate aggregation.

## 18. Auditability

For every final decision, metaO MUST be able to answer from durable evidence:

- which orchestrator ran;
- which adapter/version normalized the result;
- which subject/state was evaluated;
- which obligations were required;
- which evidence was considered;
- who/what verified each evidence item;
- what policy and authority applied;
- whether approval was required and by whom;
- whether retry/recovery history affected the decision;
- how much acceptance verification cost;
- why the final decision was produced.

## 19. Donor-derived acceptance invariants

Primary donor: `tihotm/oma`.

Accepted invariants include:

- `DONE` is not acceptance;
- fail closed on integrity failures;
- exact evidence/obligation binding;
- authoritative freshness at terminalization;
- durable retry-history authority;
- provenance closure;
- authority/capability source-of-truth;
- deterministic validation closure;
- durable audit proof.

Supplementary donors are defined in `COMPOSITION-MAP.md`.

## 20. Freeze conditions

This contract is FROZEN for the implementation roadmap.

A future change to any of the following requires an explicit architecture decision and regression acceptance plan:

- final acceptance authority;
- framework-neutrality of the EvidenceEnvelope;
- hard-gate-before-score rule;
- trust profiles;
- decision semantics;
- no hand-rolled cryptography rule;
- authoritative retry/state/authority requirements;
- cross-orchestrator evidence boundary.

Implementation may refine concrete schemas and APIs while preserving these invariants.

## 21. Post-v0.1 verifier/accounting composition

The post-v0.1 A02/A18 slice adds a minimal Rust-native composition boundary for independent verifier execution and factual accounting.

Required behavior:

- metaO selects an eligible verifier from its own registry;
- a `VerificationAttemptStarted` record is appended before verifier invocation;
- verifier result/request/binding mismatches fail closed;
- exact usage facts are recorded before budget application;
- budget exhaustion fails closed while preserving factual attempt/usage records;
- verifier success does not mint final acceptance;
- final acceptance remains owned only by `canonical_acceptance`.

Post-v0.1 terminal source composition:

- A05 re-reads subject state from an authoritative subject-state port;
- A07 resolves authority through an authoritative registry port;
- A09 resolves the policy bundle/root through an authoritative policy registry port;
- caller/runtime/verifier claims remain candidate inputs only;
- authoritative source mismatch or rollback fails closed before terminal acceptance continues.

This slice intentionally stops before broader evidence-envelope normalization gaps that remain tracked in `#228`.

## 22. Authoritative retry history

The post-v0.1 A11 slice adds an append-only retry history authority for retry/recovery/attempt/cost facts.

Required behavior:

- retry history is factual and authoritative for the scoped mission/execution ledger;
- callers may not omit prior attempts, shorten the factual history, or reset counters to reopen acceptance;
- duplicate record identity, sequence gaps and binding mismatches fail closed;
- factual history is preserved even when budget application later fails;
- retry history is not the final acceptance authority; only `canonical_acceptance` can mint final acceptance.
