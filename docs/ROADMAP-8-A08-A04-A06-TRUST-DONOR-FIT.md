# Roadmap 8 — A08/A04/A06 Approval Authority, Freshness and Hostile Provenance Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #113

## Objective

Freeze the smallest safe composition for three remaining acceptance gaps:

- A08 — approval authority and freshness;
- A04 — freshness when evidence or trust material is externally asserted;
- A06 — provenance/authenticity on the real terminal path.

This is a donor-fit decision only. No product code or dependency is introduced here.

## Current metaO state

`src/metao/governance.py` already has durable approval request/record binding and `resume_after_approval(...)` checks identity equality across approval, mission, execution, subject state and policy bundle.

`src/metao/acceptance.py` already has local freshness and provenance gates:

```text
expires_at_epoch
created_at_epoch
payload_digest
provenance_root
trusted_provenance_roots
```

Those primitives remain useful, but they are not sufficient for hostile-boundary authority/authenticity.

Frozen distinctions:

```text
APPROVAL_RECORD_EXISTS != APPROVER_AUTHORIZED_NOW
LOCAL_FRESHNESS_FIELDS_EXIST != AUTHORITATIVE_FRESHNESS_PROVEN
LOCAL_HASH_ROOT != CRYPTOGRAPHIC_AUTHENTICITY
CALLER_PROVENANCE_CLAIM != VERIFIED_PROVENANCE
```

## Frozen donors

### OMA

```text
repo   = tihotm/oma
commit = ca43381dc8bce4041da4fc09efbe939642729939
path   = src/oma/authority.py
```

Relevant patterns at the pin:

- trusted root issuers;
- explicit capability holder;
- action / target / scope authorization;
- authority epoch;
- not-before and expiry times;
- stale vs blocked authority decisions;
- delegation cannot escalate parent capability;
- actor must be the capability holder;
- missing, cyclic, self-issued or mismatched authority fails closed.

Decision:

```text
OMA capability/authority/freshness semantics = ADAPT
whole OMA dependency = NO
```

### in-toto

```text
repo   = in-toto/in-toto
commit = a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b
path   = in_toto/verifylib.py
```

Relevant patterns at the pin:

- layout expiration is checked before accepting old trust material;
- signature verification requires verification keys;
- invalid or unauthorized signatures do not count;
- authorized functionaries are distinct from merely present metadata;
- threshold requirements fail when insufficient authorized verified material exists;
- inspections abort on bad return values.

Decision:

```text
in-toto hostile provenance/authentication patterns = REFERENCE / ADAPT AT BOUNDARY
whole in-toto dependency in metaO Core = NO
hand-rolled crypto = FORBIDDEN
```

## A08 — approval authority + freshness

### Existing strength

Reuse the current durable approval transport and binding:

```text
ApprovalRequest
ApprovalRecord
require_human(...)
resume_after_approval(...)
```

Do not create another approval workflow engine.

### Missing authority

A record saying `approver_id=X` is a claim about who approved. Terminal acceptance must separately resolve whether X was authorized to approve that exact action/target/scope at the authoritative time/state.

Future minimum boundary should use the authoritative authority source already frozen by A07 and extend the request semantics, not create a second registry:

```text
AuthorityRegistryPort.resolve(
    authority_context_id,
    request = {
        actor = approver_id,
        action = "approve",
        target = mission/execution/obligation,
        scope = policy/subject context,
        capability identity where policy requires it
    }
)
```

Frozen rule:

```text
APPROVER_ID_MATCH = NECESSARY, NOT SUFFICIENT
```

### Approval freshness

The approval must be current for the exact subject state and policy identity already bound by the request, and its authority capability must be current.

Future approval authority observation should support at least:

```text
authority_context_id
authority_epoch
approved_at_epoch
not_before_epoch
expires_at_epoch
approver_id
action
target
scope
policy_bundle_id
subject_state_id
```

Required outcomes:

```text
expired capability -> STALE/BLOCK according to authoritative semantics
old authority epoch -> STALE
future/not-yet-valid capability -> BLOCK
wrong holder/action/target/scope -> BLOCK
untrusted issuer -> BLOCK
```

No confidence value may rescue a denied/stale approval.

## A04 — authoritative freshness

Local `created_at_epoch` / `expires_at_epoch` checks remain REUSE for evidence-envelope freshness.

For externally supplied trust metadata, timestamps themselves are not sufficient if the caller controls the trust material. Freshness must be evaluated against an authoritative trust/policy source or standards-backed signed object as applicable.

Composition rule:

```text
LOCAL_ENVELOPE_TIME_CHECK = REUSE
AUTHORITATIVE_STATE_CURRENTNESS = A05 SubjectStatePort
AUTHORITY_EPOCH/CAPABILITY_TIME = A07/OMA-adapted authority source
SIGNED_TRUST_MATERIAL_EXPIRATION = in-toto-style verification boundary
```

Forbidden:

```text
caller says "not expired" -> trust it
old signed policy/layout -> accept because signature is valid
old PASS -> regain authority after revoke/stale/fail
```

Latest authoritative generation/state remains authoritative.

## A06 — hostile provenance/authenticity

Current `payload_digest` and `provenance_root` are useful for deterministic binding and local integrity observations.

They do not prove who produced the material under a hostile boundary.

Frozen rule:

```text
DIGEST_BINDING = INTEGRITY INPUT
AUTHENTICATION = SEPARATE VERIFIED CLAIM
```

Future provenance verification must be pluggable behind a framework-neutral boundary. It may consume standards-backed signed attestations/layouts, but metaO Core must not import in-toto object types.

Minimum conceptual result:

```text
ProvenanceVerificationResult
- verification_id
- subject/payload digest binding
- verifier/trust-policy identity
- authenticated issuer/functionary identity
- freshness/expiry observation
- verified: bool
- reason
- result digest / observation root
```

This result remains evidence for metaO acceptance. It does not itself issue `METAO_ACCEPTED`.

## Trust-store rule

A known provenance-root string is not equivalent to authenticated provenance.

```text
KNOWN_ROOT_STRING != TRUSTED_SIGNATURE
TRUSTED_SIGNATURE != CURRENT_AUTHORIZATION
```

Keys/trust roots used for hostile verification must come from an explicit authoritative configuration or external trust provider. Do not let runtime output nominate its own trust root and then verify itself against it.

## Dependency composition

Future terminal order should preserve hard-gate precedence:

```text
canonical EvidenceEnvelope
-> authoritative subject state
-> authoritative policy
-> verifier identity/result binding
-> approval authority/freshness when required
-> provenance/authenticity verification when required
-> evidence freshness
-> retry-history gate
-> acceptance-budget gate
-> confidence advisory only after hard gates
-> terminal proof/closure
```

Exact implementation order may combine adjacent reads where safe, but authority boundaries must not collapse into caller context.

## Required future tests

A08:

1. correct approval IDs + unauthorized approver -> BLOCK;
2. authorized approver for wrong action -> BLOCK;
3. authorized approver for wrong target/scope -> BLOCK;
4. expired approver capability -> STALE/BLOCK, never ACCEPT;
5. stale authority epoch -> STALE;
6. not-yet-valid capability -> BLOCK;
7. approval for previous subject state -> STALE/BLOCK;
8. approval for previous policy bundle -> BLOCK;
9. high confidence cannot rescue bad approval authority.

A04:

10. expired evidence -> STALE;
11. future-created evidence -> BLOCK;
12. current envelope with stale authoritative subject state -> STALE;
13. signed but expired trust material -> reject;
14. prior PASS cannot recover authority after revoke/stale generation.

A06:

15. matching local hash without authenticated provenance cannot satisfy hostile provenance policy;
16. signature from unauthorized functionary/key does not count;
17. invalid signature does not count;
18. insufficient required threshold fails closed;
19. runtime-selected trust root cannot self-authorize;
20. authenticated provenance for another payload/subject is rejected by binding;
21. provenance verifier PASS remains evidence, not final metaO acceptance.

## Scope decision

```text
existing ApprovalRequest/ApprovalRecord = REUSE
existing resume_after_approval binding = REUSE
existing evidence local freshness = REUSE
existing payload_digest/provenance_root = REUSE AS BINDING INPUTS
A07 AuthorityRegistryPort = REUSE / EXTEND REQUEST SEMANTICS
OMA authority capability semantics = ADAPT
in-toto signature/expiry/authorized-threshold patterns = REFERENCE / ADAPT
new approval engine = NO
whole OMA dependency = NO
whole in-toto dependency in Core = NO
custom crypto = NO
```

## Product implementation ordering

This fit is complete, but terminal product composition remains deferred behind the prerequisite executable gates and existing Roadmap 8 slices:

```text
WU01 canonical EvidenceEnvelope -> executable-green
A18 usage/accounting primitives -> executable-green and composed
A02 verifier boundary -> executable-green and composed
A05/A07/A09 authoritative-source primitives -> executable-green
A11 retry-history primitives -> executable-green
A08/A04/A06 terminal trust composition
A14 confidence integration
A16/A19 terminal proof + adversarial closure
```

No product branch should claim final-path proof before those dependencies are executable.

## Measurement

```text
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
PRODUCT_CODE_CHANGED = NO
NEW_APPROVAL_ENGINE = NO
NEW_CRYPTO = NO
```

## Acceptance criteria result

```text
A08_DONOR_FIT = COMPLETE
A04_DONOR_FIT = COMPLETE
A06_DONOR_FIT = COMPLETE
APPROVAL_AUTHORITY_RULE = FROZEN
APPROVAL_FRESHNESS_RULE = FROZEN
HOSTILE_PROVENANCE_RULE = FROZEN
LOCAL_HASH_NOT_AUTHENTICITY = PRESERVED
WHOLE_DONOR_DEPENDENCY = NO
PRODUCT_IMPLEMENTATION = DEFERRED
```
