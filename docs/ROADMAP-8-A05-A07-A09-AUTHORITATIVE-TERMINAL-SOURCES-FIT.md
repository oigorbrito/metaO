# Roadmap 8 — A05/A07/A09 Authoritative Terminal Sources Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #96

## Objective

Close the donor-selection and boundary-design question for three frozen acceptance gaps that share one root problem: **caller-composed context is not an acceptable terminal source of truth**.

The target is not to add another policy engine or storage subsystem. The target is to make terminal acceptance re-read authoritative state, authority and policy immediately before issuing the final metaO decision.

## Frozen requirements

```text
A05 — mutated state
acceptance-critical evidence must still refer to current authoritative subject state

A07 — authority
capabilities/authority must come from an authoritative registry; caller strings cannot create root authority

A09 — policy evidence
policy identity/version/root must be authoritative, deterministic and auditable
```

## Frozen donor pin

Primary donor:

```text
repo   = tihotm/oma
commit = ca43381dc8bce4041da4fc09efbe939642729939
```

Consumed paths:

```text
src/oma/snapshot.py
src/oma/authority_registry.py
src/oma/authority.py
src/oma/policy.py
src/oma/pipeline.py
```

No donor code is copied in this audit.

---

# A05 — Authoritative subject-state re-read

## Donor behavior

`src/oma/snapshot.py` evaluates a previously verified acceptance snapshot against the current state and distinguishes three cases:

```text
rollback / malformed authoritative state -> BLOCK
legitimate forward movement / binding drift -> STALE
exact acceptance-critical equality -> ALLOW
```

Acceptance-critical bindings include:

- subject identity;
- subject state identity;
- monotonic state version;
- terminal epoch;
- policy bundle identity/root;
- obligation root;
- evidence/provenance root;
- ledger head.

Rollback is treated more severely than ordinary staleness because it can resurrect a previously valid state.

## metaO adaptation

metaO does not need OMA's concrete snapshot classes in Core. It needs the invariant and a framework/domain-neutral authoritative port.

Design target:

```text
AuthoritativeSubjectState
  subject_id
  subject_state_id
  state_version
  terminal_epoch
  policy_bundle_id
  policy_bundle_root
  obligation_root
  evidence_root
  ledger_head

SubjectStatePort
  current(subject_id) -> AuthoritativeSubjectState
```

The terminal path must compare the state bound to evidence/verification with a **fresh read** from `SubjectStatePort`.

Decision semantics:

```text
subject mismatch                  -> BLOCK
version/epoch rollback            -> BLOCK
forward version/epoch             -> STALE
binding/root drift                -> STALE
exact equality                    -> continue hard gates
```

A caller-provided `AcceptanceContext.subject_state_id` may express the candidate binding but may not be the terminal source of truth.

Decision:

```text
SOURCE = OMA snapshot.py
MODE = ADAPT INVARIANTS / MINIMUM METAO PORT
```

---

# A07 — Authoritative capability/authority registry

## Donor behavior

`src/oma/authority_registry.py` implements a durable SQLite authority issuance boundary.

Important properties:

- one trusted authority context is initialized explicitly;
- root capabilities are admitted only during trusted bootstrap;
- post-bootstrap root creation is rejected;
- later capabilities must be delegated children;
- durable context epoch/digest is verified on reads;
- capability ids are unique per authority context;
- invalid/malformed storage fails closed;
- delegated issuance is evaluated against already-authoritative capability state;
- caller issuer-name fabrication is closed inside the supported local trust boundary.

The donor explicitly does **not** claim cryptographic issuer authenticity against a hostile process. metaO preserves that threat-model separation.

## metaO adaptation

metaO needs authority as a source-of-truth port, not an `authorized_authorities` set supplied by a request context.

Design target:

```text
AuthorityRequest
  actor_id
  action
  target
  scope
  capability_id?

AuthoritativeAuthorityDecision
  decision       # ALLOW / STALE / BLOCK
  authority_context_id
  authority_epoch
  capability_id?
  reason
  evidence_root

AuthorityRegistryPort
  resolve(authority_context_id, request) -> AuthoritativeAuthorityDecision
```

Terminal acceptance must obtain authority through this port and bind the resulting authority context/capability evidence to the exact subject, policy and verification request.

Required local-trust rules:

```text
unknown context                    -> BLOCK
context digest/epoch mismatch      -> BLOCK or STALE according to authoritative transition semantics
fabricated root capability         -> BLOCK
delegation outside parent subset   -> BLOCK
expired/not-yet-valid capability   -> BLOCK/STALE per policy
valid authoritative capability     -> continue hard gates
```

For hostile/distributed roots, authenticity must be delegated to standard attestation/crypto components; no custom signature system belongs here.

Decision:

```text
SOURCE = OMA authority_registry.py + authority.py
MODE = ADAPT DURABLE AUTHORITY INVARIANTS / MINIMUM METAO PORT
```

---

# A09 — Authoritative policy bundle and decision evidence

## Donor behavior

`src/oma/policy.py` provides deterministic canonical roots for policy objects and bundles.

Its bundle evaluation fails closed unless:

- expected bundle identity is valid;
- bundle epoch is valid;
- required policy-kind set matches exactly;
- each policy id matches;
- each policy root matches;
- every bound policy-bundle id points to the expected bundle;
- presented and expected bundle identity/epoch are equal.

Successful evaluation yields a deterministic `policy_bundle_root`.

`src/oma/pipeline.py` then binds that root to snapshot/current state and uses it as evidence in the composed validation graph.

## metaO adaptation

metaO should not make caller-provided `policy_bundle_id` the authority. The caller/evidence can state which bundle it claims, but terminalization must resolve the authoritative bundle and compare exact identity/version/root.

Design target:

```text
AuthoritativePolicyBinding
  policy_kind
  policy_id
  policy_root

AuthoritativePolicyBundle
  policy_bundle_id
  bundle_epoch
  bindings
  policy_bundle_root

PolicyRegistryPort
  get(policy_bundle_id) -> AuthoritativePolicyBundle
```

Terminal rules:

```text
unknown bundle                       -> BLOCK
bundle id mismatch                   -> BLOCK
policy-kind set mismatch             -> BLOCK
policy id/root mismatch              -> BLOCK
bundle epoch behind authoritative    -> STALE or BLOCK according to rollback/transition semantics
exact authoritative bundle/root      -> continue hard gates
```

A policy engine may be introduced later only behind this boundary and only after fit justification. OPA is not made a mandatory runtime dependency by this work.

Decision:

```text
SOURCE = OMA policy.py + pipeline.py
MODE = ADAPT ROOT/BUNDLE INVARIANTS / MINIMUM METAO PORT
```

---

# Shared terminal composition

The three ports are separate authorities but must be read in one terminal verification phase.

Design target:

```text
candidate evidence + candidate AcceptanceContext
        |
        v
SubjectStatePort.current(subject_id)
AuthorityRegistryPort.resolve(...)
PolicyRegistryPort.get(policy_bundle_id)
        |
        v
construct authoritative terminal context / evidence bindings
        |
        v
compare candidate bindings to authoritative values
        |
        +-- rollback / fabrication / invalid root -> BLOCK
        +-- legitimate forward mutation           -> STALE
        +-- exact match                            -> continue
        |
        v
existing acceptance hard gates
        |
        v
metaO final decision
```

The exact implementation may expose one composition service over the three ports, but the authority responsibilities must remain distinct and testable.

## Important rule

```text
CALLER_CONTEXT = CANDIDATE CLAIMS
AUTHORITATIVE_PORTS = TERMINAL SOURCE OF TRUTH
```

The terminal path may not simply transform caller data into an object named "authoritative". A real independent read is required.

---

# Proposed implementation order

This audit does not change product code.

The future product slice should remain ordered after the current Roadmap 8 structural/functional dependencies:

```text
#90 / PR #91 — canonical EvidenceEnvelope -> executable-green
A18 budget composition per #92 ordering
A02 verifier boundary after canonical evidence target
A05/A07/A09 authoritative terminal sources
```

The three authoritative ports should be implemented in one bounded work unit because introducing only one while leaving the other two caller-authoritative would create a misleading partial terminal-authority claim.

This does not require all storage backends at once. A reference in-memory implementation plus a durable implementation where the existing persistence architecture requires it may be introduced behind the same ports, with executable adversarial tests.

---

# Required future tests

Product implementation must eventually prove at least:

1. evidence created for state N is `STALE` after authoritative forward mutation to N+1;
2. authoritative state rollback is `BLOCK`;
3. caller lies about current state but terminal re-read wins;
4. caller fabricates an authority id/capability but registry denies it;
5. post-bootstrap fabricated root capability is rejected;
6. delegated capability cannot exceed its parent authority;
7. caller supplies a valid bundle id with altered policy root and is blocked;
8. authoritative policy epoch/root advances and old evidence becomes stale/blocked per transition policy;
9. all authoritative reads are bound to the same terminal evaluation;
10. same authoritative inputs produce deterministic final decision/proof;
11. no orchestrator SDK type enters these ports;
12. no standard-crypto claim is made without a standard provider.

These must traverse the real metaO terminal path; primitive-only unit tests are insufficient for final-path proof.

---

# Composition / measurement

```text
DONOR_REPO = tihotm/oma
DONOR_COMMIT = ca43381dc8bce4041da4fc09efbe939642729939
DONOR_PATHS = snapshot.py, authority_registry.py, authority.py, policy.py, pipeline.py

DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO

A05_MODE = ADAPT
A07_MODE = ADAPT
A09_MODE = ADAPT
WHOLE_OMA_DEPENDENCY = NO
```

## Non-goals

```text
NO new policy engine
NO OPA mandatory dependency
NO whole OMA import
NO hand-rolled crypto
NO caller-authored terminal authority
NO fourth orchestrator
NO learned routing
NO distributed database expansion
```

## Acceptance criteria result

```text
EXACT_DONOR_PIN_PATHS = RECORDED
A05_A07_A09_SOURCE_OF_TRUTH_COMPOSITION = DOCUMENTED
MINIMUM_PORTS = DOCUMENTED
CALLER_AUTHORITY_PROHIBITION = EXPLICIT
ROLLBACK_BLOCK_FORWARD_MUTATION_STALE = PRESERVED
WHOLE_DONOR_DEPENDENCY = NO
PRODUCT_CODE_CHANGE = NO
IMPLEMENTATION = DEFERRED_TO_ORDERED_ROADMAP8_WU
```
