# Project Discovery and Reference Intake

## Objective

metaO must not treat a vague product request as a complete build specification. A request such as `build a marketplace` starts a discovery phase whose goal is to convert user intent into a bounded, testable MVP contract before implementation begins.

```text
AMBIGUOUS_SPEC != READY_TO_BUILD
ASSUMPTION != USER_REQUIREMENT
MVP != PROTOTYPE
```

## Discovery flow

```text
User Intent
  ↓
Discovery / Clarification
  ↓
Reference Intake
  ↓
MVP Contract
  ↓
Acceptance Criteria
  ↓
Work Breakdown
  ↓
Implementation / Verification Loop
  ↓
Project Completion Gate
```

## Reference Intake

When product shape, UX, workflow, business model, or scope can be interpreted in materially different ways, metaO should ask for references before silently choosing one interpretation.

Example for `build a marketplace`:

- Is it closer to Facebook Marketplace, OLX, WebMotors, Mercado Livre, Enjoei, or another product?
- Which aspects of those references should be copied conceptually: listing flow, search, checkout, seller profiles, messaging, moderation, catalog structure, admin operations, visual density, etc.?
- Are there links, screenshots, repositories, documents, wireframes, or existing products that should be treated as inspiration?
- Which aspects must explicitly *not* be copied?
- Is the reference about appearance, functionality, workflow, business rules, or all of these?

References are inspiration/evidence inputs, not implicit requirements. metaO must extract explicit desired traits from them and record those traits in the ProjectContract.

```text
REFERENCE != REQUIREMENT
REFERENCE + USER_SELECTION -> REQUIREMENT CANDIDATE
```

## Clarification policy

Questions are mandatory when the unresolved answer can materially change architecture, user-visible behavior, data model, required surfaces, compliance, cost, or the definition of done.

Examples:

- target users and roles;
- buyer/seller relationship;
- catalog/listing model;
- payments in or out of MVP;
- messaging/contact model;
- admin/moderation requirements;
- web/mobile surfaces;
- required integrations;
- geography/language/currency;
- required stack or deployment constraints;
- reference products and links;
- non-negotiable UX or workflow expectations.

Questions should not become an interrogation. If a missing choice is low-risk, reversible, and does not materially affect acceptance, metaO may choose a documented default.

```text
MATERIAL_AMBIGUITY -> ASK_HUMAN
SAFE_REVERSIBLE_DEFAULT -> RECORD_ASSUMPTION + CONTINUE
```

## ProjectContract

Discovery should produce a versioned ProjectContract containing at minimum:

```text
project_goal
target_users
roles
required_capabilities
required_surfaces
core_user_flows
business_rules
reference_products
reference_traits
constraints
technical_constraints
non_functional_requirements
out_of_scope
assumptions
human_decisions
definition_of_done
acceptance_criteria
acceptance_tests
```

A reference entry should distinguish the source from the desired trait, for example:

```text
reference:
  name: WebMotors
  url: <user supplied URL if any>
  desired_traits:
    - vehicle-first structured listings
    - strong faceted search
    - seller contact flow
  explicitly_not_required:
    - financing integration
    - production-scale advertising stack
```

## Marketplace example

A vague request:

```text
"Build a marketplace."
```

should not directly create implementation tasks. metaO should first determine whether the intended product resembles, for example:

```text
Facebook Marketplace -> local/social listings and messaging
OLX                  -> classifieds/search/contact
WebMotors            -> vertical marketplace with structured domain catalog
Mercado Livre        -> transactional marketplace, cart/orders/payments/seller ops
Enjoei                -> curated consumer resale with strong listing UX
Other                 -> user-supplied reference or original model
```

The user may combine traits:

```text
"Use WebMotors-style structured listings and filters,
OLX-style seller contact,
and Mercado Livre-style order tracking,
but no real payments in MVP."
```

That combination must become explicit ProjectContract requirements rather than remaining informal conversation context.

## MVP completion rule

A marketplace MVP is not complete merely because a UI exists. The ProjectContract decides the required minimum, but when applicable metaO should require proof of the promised end-to-end product:

```text
usable frontend
+ real backend
+ persistent data
+ required authentication/authorization
+ integrated core flows
+ basic error states
+ reproducible startup/setup
+ required acceptance tests
= MVP candidate
```

Only independent acceptance may mark the project complete.

```text
IMPLEMENTATION_DONE != PROJECT_ACCEPTED
ALL_REQUIRED_WORK_UNITS_ACCEPTED != PROJECT_ACCEPTED
PROJECT_CONTRACT_PROVEN -> PROJECT_ACCEPTED
```

## State model

```text
INTENT_RECEIVED
↓
NEEDS_CLARIFICATION
↓
REFERENCE_INTAKE
↓
SPEC_READY
↓
PLAN_READY
↓
IMPLEMENTING
↓
VALIDATING
↓
MVP_ACCEPTED | BLOCKED
```

## Architectural placement

This capability sits above the existing orchestrator-control pipeline; it does not change the frozen runtime abstraction.

```text
ProjectRequest
↓
SpecificationCoordinator
↓
ProjectContract
↓
ProjectPlanner
↓
WorkUnitGraph
↓
Mission / Strategy / Policy / Runtime / Evidence / Acceptance
↓
ProjectCompletionGate
```

The central runtime substitution invariant remains unchanged: replacing a whole orchestrator, including its internal agents/tools/memory/workflows, must not require changing metaO Core.
