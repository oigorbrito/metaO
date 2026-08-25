# Roadmap 8 — A16/A19 Terminal Proof and Adversarial Closure Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #100

## Objective

Freeze the minimum design needed to make final metaO decisions reconstructible from durable evidence (A16) and to prove the frozen adversarial-executor threat model through the real terminal path (A19).

This is not a new security subsystem. It composes existing metaO durability/observability with donor-proven validation-closure and attack-test patterns.

## Current metaO strengths

Current `main` already contains:

```text
AcceptanceProof
EventLedgerPort
InMemoryEventLedger
SQLiteEventLedger
ObservableMissionOperator
MissionStorePort / SQLiteMissionStore
security.py standards-provider boundary
```

The event ledger is framework-neutral and append-only. The observable operator records mission creation, policy, selection, runtime execution, evidence, acceptance, replans, approval and terminal events.

The acceptance layer produces a deterministic proof digest.

These are valuable primitives and must be reused rather than replaced.

## Current gap

The present `AcceptanceProof` binds:

```text
decision
reasons
evidence_ids
```

It does not yet bind the exact set of authoritative gate results that produced terminal acceptance, such as current subject-state authority, policy root, authority/capability result, authoritative retry history, budget state, approval authority or hostile attestation result.

The event ledger records events, but there is no current validation-profile/closure digest that proves which required gate observations were included and which exact evidence roots supported each gate.

Therefore:

```text
EVENTS_EXIST != TERMINAL_DECISION_RECONSTRUCTIBLE
DETERMINISTIC_ACCEPTANCE_PROOF != COMPLETE_VALIDATION_CLOSURE
SECURITY_PRIMITIVE_EXISTS != ADVERSARIAL_TERMINAL_PATH_PROVEN
```

## Frozen primary donor

```text
repo   = tihotm/oma
commit = ca43381dc8bce4041da4fc09efbe939642729939
paths  = src/oma/validation.py
         src/oma/pipeline.py
         src/oma/sqlite_commit.py
         tests/test_closure_proof.py
         tests/test_authority_authenticity_audit.py
         tests/test_retry_ledger_audit.py
         tests/test_trust_artifact_authenticity_audit.py
```

Supplementary hostile-boundary technology remains the frozen standard-attestation references (in-toto / Sigstore/Cosign semantics). No custom cryptography is authorized.

---

# A16 — Deterministic terminal closure

## Donor pattern

OMA `validation.py` defines:

- a validation graph with named nodes and dependencies;
- an exact closure required by the terminal node;
- one `ValidationObservation` per node with decision + evidence root;
- duplicate/unknown/outside-closure observations fail closed;
- missing required observations cannot yield terminal acceptance;
- a deterministic closure digest bound to graph id, terminal node, graph order, decisions and evidence roots.

`tests/test_closure_proof.py` additionally proves:

- the same exact closure yields the same digest;
- changing the validation graph id changes the digest;
- changing a valid factual input changes the relevant evidence root and closure digest;
- durable terminal records preserve the exact precommit proof across database reopen.

## metaO decision

Adapt the closure concept, not the OMA graph topology.

```text
OMA validation closure = ADAPT
OMA concrete validation graph = DO NOT COPY AS METAO AUTHORITY
existing metaO EventLedger/MissionStore = REUSE
new audit database = NO
```

metaO needs a validation profile describing which gate families are required for one mission/decision type, then an exact set of observations over that profile.

## Proposed minimum design target

Names are provisional; invariants are frozen by this audit.

```text
TerminalObservation
  gate_id
  decision
  evidence_root

TerminalValidationProfile
  validation_profile_id
  required_gate_ids
  optional_gate_rules
  terminal_gate_id

TerminalDecisionProof
  proof_version
  mission_id
  execution_id / attempt binding
  subject_id
  subject_state binding
  validation_profile_id
  terminal_decision
  reasons
  ordered_gate_ids
  closure_digest

TerminalProofBuilder
  build(profile, observations, bindings) -> TerminalDecisionProof
```

Required behavior:

```text
duplicate observation              -> BLOCK
unknown observation                -> BLOCK
observation outside allowed closure -> BLOCK
missing required observation       -> NOT_DONE/BLOCK per frozen gate semantics
missing evidence root              -> BLOCK
same inputs                         -> same proof
fact/root/decision change           -> different proof
```

## Observation roots

An observation root is a deterministic digest/reference of the authoritative evidence used by that gate. It is **not automatically a cryptographic authenticity proof**.

Future Roadmap 8 slices should expose deterministic roots for applicable gate families:

```text
state/freshness                # A05
verifier/trust/provenance      # A02/A04/A06
authority/capability           # A07
policy bundle/decision         # A09
evidence completeness/conflict # A03/A10/A13
retry/recovery history         # A11
approval/human decision        # A08/A15 when required
acceptance budget              # A18
confidence/escalation          # A14 when applicable
```

The validation profile defines the exact required denominator. A caller cannot omit a required gate simply by omitting its observation.

## Persistence decision

Do not introduce a second audit datastore by default.

Recommended composition:

```text
MissionOutcome / durable mission record
  retains complete TerminalDecisionProof or stable resolvable proof record

MISSION_TERMINAL event
  binds closure_digest + validation_profile_id + terminal decision

EventLedger
  continues append-only operational/audit timeline
```

The existing event ledger is a projection/audit stream. The terminal proof is the deterministic decision-closure artifact. They complement rather than replace each other.

---

# A19 — Adversarial terminal-path closure

## Existing metaO evidence

Current tests already prove useful primitives:

- executor completion is not metaO acceptance;
- wrong bindings/duplicates/conflicts are governed by acceptance;
- hostile trust profile exists;
- standards-based crypto provider boundary exists;
- freshness, replay, revoked verifier and untrusted verifier primitives fail closed.

However Block M currently calls security primitives directly. It does not prove that those primitives, authoritative state, retry history, authority registry and policy roots are all consumed by the same final mission terminalization path.

Classification remains:

```text
PRIMITIVE/UNIT PROOF != COMPOSED TERMINAL ADVERSARIAL PROOF
```

## OMA adversarial patterns to adapt

### Authority fabrication

OMA terminal tests prove that a caller-provided fabricated capability claiming a trusted/root issuer cannot replace authoritative registry state. Caller omission of the authoritative capability set also does not remove the stored authority.

Pattern to adapt:

```text
caller authority claim != authoritative authority source
```

### Retry omission

OMA proves that a caller can present only an early retry prefix and still be blocked when authoritative history contains over-limit events.

Pattern to adapt:

```text
caller retry tuple != authoritative retry history
```

### Local trust negative lesson

OMA also contains an intentionally important audit result: under its local semantic trust model, a caller-fabricated artifact that merely claims a known root id can pass if no cryptographic authenticity mechanism exists.

metaO must preserve this negative lesson:

```text
KNOWN_ROOT_STRING != CRYPTOGRAPHIC_AUTHENTICITY
LOCAL_HASH_ROOT != HOSTILE_AUTHENTICATION
```

No documentation/test may represent local root identity as hostile/distributed issuer proof.

---

# Trust-profile split

## LOCAL_TRUSTED_CONTROL_PLANE

Within the frozen local profile, metaO may rely on trusted process/host durable state plus deterministic digests to establish:

- reproducibility;
- source-of-truth consistency against ordinary callers/adapters;
- detection of malformed/mismatched durable records;
- audit reconstruction.

This is not cryptographic non-repudiation against a hostile database administrator/process.

## HOSTILE_OR_DISTRIBUTED_BOUNDARY

If evidence crosses an untrusted process/domain/transport boundary, terminal verification must compose a vetted standards-based attestation implementation through the existing `CryptoProviderPort`-style boundary or an equivalent frozen standard integration.

Required hostile semantics include, as applicable:

- signature/attestation verification;
- authorized identity/functionary;
- freshness/time validity;
- replay protection;
- revocation/trust-root checks;
- exact artifact/payload digest binding.

Forbidden:

```text
custom signature scheme in metaO
string issuer/root treated as authentication
local closure hash advertised as non-repudiation
```

---

# Future A19 terminal attack matrix

The final composed Roadmap 8 acceptance path must eventually execute adversarial scenarios against the real terminal authority.

## Execution / evidence

1. orchestrator returns `DONE/SUCCESS` with missing required evidence -> not accepted;
2. evidence belongs to wrong mission/execution/subject -> block;
3. evidence refers to stale subject state -> stale/block per authoritative mutation semantics;
4. payload altered after verification/digest mismatch -> block;
5. duplicate/replayed evidence id -> block;
6. conflicting evidence for one obligation -> block;
7. unexpected evidence used to manipulate aggregation -> block.

## Verifier / provenance / trust

8. executor selects/fabricates a verifier not authorized by metaO -> block;
9. revoked/untrusted verifier -> block;
10. provenance root/subgraph substitution -> block;
11. stale attestation -> block/stale;
12. replayed hostile attestation -> block;
13. hostile artifact claims trusted root but standards attestation fails/missing -> block.

## Authority / policy / state

14. caller fabricates root capability -> block;
15. caller omits authoritative capabilities -> stored authoritative decision still wins;
16. policy bundle id is correct but policy root/content changed -> block;
17. authoritative policy/state advances after verification -> stale/block according to frozen rules;
18. caller passes old/current-state claim to bypass terminal reread -> authoritative read wins.

## Retry / budget / approval

19. caller omits old retries -> authoritative history wins;
20. restart attempts to reset attempt/cost budget -> history wins;
21. over-limit retry event remains factual and blocks;
22. verification budget is omitted/reset -> authoritative A18 state wins;
23. stale/mismatched approval -> block;
24. unauthorized approver -> block once A08 authority is composed.

## Terminal/audit assertions for every applicable attack

Tests must assert more than a helper exception.

At minimum:

```text
specific gate decision is correct
final metaO decision is not ACCEPT
TerminalDecisionProof closure includes the failing gate observation
closure digest is deterministic for the same attack inputs
blocked attack does not create an accepted terminal record
EventLedger terminal/audit events agree with the durable final decision
```

A positive control must exist for each attack family so a test cannot pass because the entire feature is permanently blocked.

---

# Composition decision

```text
OMA validation closure/root pattern = ADAPT
OMA adversarial test patterns = ADAPT
metaO EventLedger = REUSE
metaO MissionStore = REUSE
metaO security standards-provider boundary = REUSE
whole OMA dependency = NO
new audit database/service = NO
custom crypto = FORBIDDEN
```

The metaO-specific BUILD is limited to the cross-gate terminal proof composition required by its control-plane role.

## Why no new audit service

The current repository already has durable mission and event storage. Adding another service solely for proof storage would create operational scope without solving a proven gap.

Only if a future hostile/distributed threat model requires external transparency/non-repudiation should a standard transparency/attestation component be adopted through a separate architecture decision.

---

# Ordering

This donor fit is complete now, but product implementation belongs late in Roadmap 8.

A closure proof over caller-supplied/non-authoritative values would create false assurance. Therefore the final closure must follow the authority-producing slices:

```text
WU01 canonical EvidenceEnvelope -> executable-green
A18 acceptance-budget composition
A02 independent verifier boundary
A05/A07/A09 authoritative terminal sources
A11 authoritative retry history
A14/A08/A06 composition as required
A16/A19 terminal proof + full adversarial closure
```

A16 proof structures may be introduced earlier if needed, but `FINAL_PATH_PROVEN` cannot be claimed until the required authoritative observations are actually composed.

---

# Measurement

```text
DONOR_REPO = tihotm/oma
DONOR_COMMIT = ca43381dc8bce4041da4fc09efbe939642729939
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO
NEW_AUDIT_DATABASE = NO
STANDARD_CRYPTO_REQUIREMENT_PRESERVED = YES
```

## Acceptance criteria result

```text
EXACT_DONOR_PIN_PATHS = RECORDED
CURRENT_PROOF_EVENT_STRENGTHS_AND_GAPS = DOCUMENTED
DETERMINISTIC_CLOSURE_PATTERN = DOCUMENTED
EXISTING_DURABLE_SURFACES_REUSED = YES
LOCAL_VS_HOSTILE_BOUNDARY = EXPLICIT
OMA_NEGATIVE_AUTHENTICITY_LESSON = PRESERVED
ADVERSARIAL_TERMINAL_MATRIX = DOCUMENTED
PRODUCT_CODE_CHANGE = NO
IMPLEMENTATION = DEFERRED_TO_LATE_ROADMAP8_CLOSURE
```
