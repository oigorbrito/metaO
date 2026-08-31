# Post-v0.1 Product Roadmap Reconciliation

Historical note: this document records the post-v0.1 roadmap reconciliation for the v0.1 cycle. Current baseline authority has moved to `docs/POST-MVP-OPERATIONAL-BASELINE-V1.md`.

This document establishes the canonical execution order for the metaO repository following the v0.1 acceptance closure.

## 1. Classification Matrix

| Issue | Title | Classification | Canonical Owner | Safe To Close |
|---|---|---|---|---|
| #274 | Post-v0.1 product roadmap reconciliation | PROCESS_CANONICAL | #274 | NO |
| #254 | Empirical/reproducible engineering concepts | RESEARCH_ONLY | #254 | NO |
| #245 | Engineering execution protocol | PROCESS_CANONICAL | #245 | NO |
| #227 | Repository convergence wave 1 | PROCESS_CANONICAL | #227 | NO |
| #209 | Research/Spike: autonomous project governance | SATISFIED_OR_SUPERSEDED_SAFE_TO_CLOSE | #209 | YES |
| #206 | Executable evidence-control donor | DONOR_EVALUATION_ONLY | #206 | NO |
| #205 | Legacy scientific/design donors | DONOR_EVALUATION_ONLY | #205 | NO |
| #204 | Operator UX | ACTIVE_PRODUCT_NOW | #204 | NO |
| #180 | Scientific fit — ClarifyCodeBench | RESEARCH_ONLY | #180 | NO |
| #177 | Project Discovery — E2E scenario | DEFERRED_PRODUCT_WITH_TRIGGER | #177 | NO |
| #176 | Project Discovery — state machine and coordinator | DEFERRED_PRODUCT_WITH_TRIGGER | #176 | NO |
| #175 | Project Discovery — MVP DoD and ProjectCompletionGate | DEFERRED_PRODUCT_WITH_TRIGGER | #175 | NO |
| #174 | Project Discovery — ProjectContract foundations | ACTIVE_PRODUCT_NOW | #174 | NO |
| #173 | Project Discovery — clarification policy | PRODUCT_NEXT_DEPENDENCY | #173 | NO |
| #172 | Project Discovery — technical stack intake | PRODUCT_NEXT_DEPENDENCY | #172 | NO |
| #171 | Project Discovery — reference intake | PRODUCT_NEXT_DEPENDENCY | #171 | NO |
| #170 | Project Discovery — turn vague intent into MVP | SATISFIED_OR_SUPERSEDED_SAFE_TO_CLOSE | #170 | YES |
| #168 | Scientific validation matrix | DEFERRED_PRODUCT_WITH_TRIGGER | #168 | NO |
| #167 | Audit assurance | DEFERRED_PRODUCT_WITH_TRIGGER | #167 | NO |
| #166 | Control-plane admission | DEFERRED_PRODUCT_WITH_TRIGGER | #166 | NO |
| #165 | Security boundary | DEFERRED_PRODUCT_WITH_TRIGGER | #165 | NO |
| #164 | Control-plane HA | DEFERRED_PRODUCT_WITH_TRIGGER | #164 | NO |
| #163 | Interoperability — CloudEvents | DEFERRED_PRODUCT_WITH_TRIGGER | #163 | NO |
| #162 | Runtime certification | DEFERRED_PRODUCT_WITH_TRIGGER | #162 | NO |
| #161 | Scientific harness | DEFERRED_PRODUCT_WITH_TRIGGER | #161 | NO |
| #160 | Control-plane gap — runtime health | DEFERRED_PRODUCT_WITH_TRIGGER | #160 | NO |
| #159 | Control-plane gap — workload identity | DEFERRED_PRODUCT_WITH_TRIGGER | #159 | NO |
| #158 | Control-plane gap — external-effect idempotency | PRODUCT_NEXT_DEPENDENCY | #158 | NO |
| #149 | SMAG composition — security, isolation | DEFERRED_PRODUCT_WITH_TRIGGER | #149 | NO |
| #148 | SMAG composition — cost-aware routing | DEFERRED_PRODUCT_WITH_TRIGGER | #148 | NO |
| #147 | SMAG composition — operational service | DEFERRED_PRODUCT_WITH_TRIGGER | #147 | NO |
| #146 | SMAG composition — checkpoint/resume | DEFERRED_PRODUCT_WITH_TRIGGER | #146 | NO |
| #145 | SMAG composition — orchestrator expansion | DEFERRED_PRODUCT_WITH_TRIGGER | #145 | NO |
| #144 | SMAG composition — engineering-workload plugin | PRODUCT_NEXT_DEPENDENCY | #144 | NO |
| #143 | SMAG composition — engineering harness | PRODUCT_NEXT_DEPENDENCY | #143 | NO |
| #142 | SMAG composition — execution-stage evidence | ACTIVE_PRODUCT_NOW | #142 | NO |
| #141 | SMAG composition — failure causality | DEFERRED_PRODUCT_WITH_TRIGGER | #141 | NO |
| #140 | SMAG composition — Risk Governance and ExecutionBudget | ACTIVE_PRODUCT_NOW | #140 | NO |
| #71 | GitHub Actions hosted-runner pre-step blocker | BLOCKED_EXTERNAL | #71 | NO |

## 2. Dependency/Order Graph

1. **ACTIVE_PRODUCT_NOW**
   - #204: Operator UX
   - #174: ProjectContract foundations
   - #140: Risk Governance and ExecutionBudget
   - #142: Execution-stage evidence

2. **PRODUCT_NEXT_DEPENDENCY**
   - Project Discovery Expansion: #171, #172, #173
   - SMAG Engineering: #143, #144
   - Reliability: #158

3. **DEFERRED_PRODUCT_WITH_TRIGGER**
   - HA, Multi-tenant, CloudEvents, Orchestrator Failover, etc.

## 3. Explicit Separation

### PRODUCT
Issues actively being worked on for the core orchestrator and user experience (e.g., #204, #174, #140, #142).

### RESEARCH
Issues dedicated to scientific validation, donor evaluation, and long-term research (e.g., #254, #180, #205, #206).

### EXTERNAL_INFRASTRUCTURE
Issues blocked by third-party infrastructure (e.g., #71).

## 4. Top 3 Candidate Blocks

**RANK_1**: #204 Operator UX
* WHY_NOW: A powerful orchestrator is useless without an obvious entrypoint and usable execution environment.
* WHAT_IT_UNLOCKS: Real-world adoption, user feedback, and end-to-end usage of the v0.1 features.
* WHY_NOT_OTHER_CANDIDATES: Project Discovery requires the UX to be usable first.
* MINIMUM_EXECUTABLE_SLICE: Environment validation, runtime discovery, and CLI --help with basic mission submission.

**RANK_2**: #174 ProjectContract foundations
* WHY_NOW: Establishes the core data model for Project Discovery.
* WHAT_IT_UNLOCKS: The entire Project Discovery feature family (#171-#177).
* WHY_NOT_OTHER_CANDIDATES: Operator UX is more pressing for immediate usability.
* MINIMUM_EXECUTABLE_SLICE: Schema definition and basic validation for project intents.

**RANK_3**: #140 Risk Governance and ExecutionBudget
* WHY_NOW: Safety and budget constraints are necessary before executing complex autonomous missions.
* WHAT_IT_UNLOCKS: Safe execution of SMAG workloads.
* WHY_NOT_OTHER_CANDIDATES: The system can run in a trusted/local mode first while UX and Contracts are built.
* MINIMUM_EXECUTABLE_SLICE: Budget tracking data structures and enforcement during execution steps.

## 5. Next Canonical Block

**NEXT_CANONICAL_BLOCK**: #204 Operator UX
