# SMAG Donor Composition for metaO

Status: PROPOSED canonical addendum under Issue #139
Parent tracking: #138
Audit date: 2026-08-26

This document records the approved composition intent for reusing the maximum relevant capabilities from SMAG without changing the frozen metaO abstraction: metaO governs whole orchestrators; it does not absorb their internal agents, tools, memory, prompts, provider APIs or workflow topology into Core.

## 1. Audit pin

```text
repository = tihotm/smag
commit = 548a2ce85acb2aeb0e2d64a0fd03cfd839763ad8
release metadata = 0.1.2
role = governance / evidence / execution-control / engineering-harness donor
foundation = NO
orchestrator = NO
replacement_for_conductor = NO
core_sdk_dependency = NO
```

This pin freezes the donor audit reference only. Every implementation Work Unit MUST re-pin the exact donor repository, commit, path and tests actually consumed.

## 2. Architecture boundary

The metaO pipeline remains:

```text
Mission
-> Strategy / Selection
-> Policy / Budget / Risk
-> OrchestratorContract
-> Runtime Adapter
-> real orchestrator
-> Evidence
-> Independent Acceptance
-> Accept / Replan / Failover / Block
```

SMAG-derived mechanisms may strengthen governance and evidence around this pipeline. They must not redefine the strategic unit from whole orchestrator to internal agent/model/tool.

## 3. SMAG reference-donor inventory

The SMAG reference manifest audited these local repositories:

| Reference donor | Historical role in SMAG | metaO composition role |
|---|---|---|
| `cline/cline` | specialized coding-agent reference | engineering-workload runtime/reference only |
| `openai/codex` | coding executor reference | engineering-workload runtime/reference only |
| `mastra-ai/mastra` | agent/workflow framework | candidate orchestrator adapter; fit required |
| `microsoft/agent-framework` | workflow/state/multi-agent/tools/approval/telemetry reference | candidate orchestrator adapter and mechanism reference |
| `open-multi-agent/open-multi-agent` | orchestration/routing/runtime analogue | runtime/orchestrator adapter and conformance donor |
| `openai/openai-agents-js` | agent SDK reference | candidate orchestrator adapter; SDK types stop at boundary |
| `OpenHands/OpenHands` | software-engineering runtime/sandbox reference | engineering-workload runtime/plugin donor |
| `tihotm/work-unit-supervisor` | WorkUnit/supervision/diff/workspace legacy internal donor | engineering plugin + selected contract/invariant donor |

Historical SMAG audit also mentioned Omnigent and GitHub Agentic Workflows as unresolved/non-local references. They are NOT approved consumed donors merely by being mentioned. Exact source/pin/path audit is required before any future use.

## 4. Maximum relevant reuse matrix

| Capability family | SMAG source area | metaO decision | Boundary |
|---|---|---|---|
| mechanism vs authority | architecture/control plane | ADOPT semantics | Core invariant |
| facts before decisions | architecture/control plane | ADOPT semantics | Core invariant |
| fail-closed/no-override | control plane/governance | ADAPT | policy/risk/budget/approval |
| explicit risk governance | `src/risk-governance.js` | ADAPT | metaO RiskDecision authority |
| execution budget | `src/budget-governance.js` | ADAPT | separate from acceptance/verifier budget |
| approval mechanics/provenance lessons | approval modules | REFERENCE/ADAPT | do not replace Roadmap 8 approval authority |
| abort/cancel/timeout taxonomy | `src/abort-governance.js` | ADAPT | runtime/replan facts |
| recovery semantics | `src/recovery-governance.js` | ADAPT | replan/recovery authority |
| retry eligibility | `src/retry-governance.js` | ADAPT | compose with authoritative A11 history |
| execution-stage evidence | `src/smag-control-plane.js` | ADAPT | compose into canonical EvidenceEnvelope |
| deterministic execution report | `src/execution-report.js` | ADAPT | projection only |
| deterministic telemetry | `src/execution-telemetry.js` | ADAPT | observation only |
| telemetry sinks / OTLP | telemetry/adapters | REFERENCE pending gap audit | external observability |
| state snapshot/restore | supervisor state | TEST-DONOR | Conductor conformance |
| checkpoint/resume | checkpoint modules | TEST-DONOR | Conductor remains mechanism |
| filesystem checkpoint store | adapter | REJECT from Core | no duplicate durability |
| cost-aware provider routing | cost-aware adapter | REFERENCE/ADAPT facts | below orchestrator selection |
| free-first/zero-credit path | routing/config/runtime | REFERENCE/ADAPT facts | runtime capability signal |
| WorkUnit lessons | WUS/SMAG boundary | ADAPT only if framework-neutral | no coding-specific Core leakage |
| diff/path admissibility | WUS adapter | PLUGIN | engineering workload only |
| workspace apply/rollback | WUS adapter | PLUGIN | engineering workload only |
| Git commit/push/PR | Git adapters | PLUGIN/REFERENCE | not generic Core |
| sandbox/process lifecycle | OpenHands/Codex/Cline refs | PLUGIN/REFERENCE | runtime owned |
| multi-agent internals | framework refs | REJECT from Core | orchestrator owned |
| tools/MCP internals | framework refs | REJECT from Core | orchestrator/runtime owned |
| provider SDK/model internals | framework refs | REJECT from Core | below metaO abstraction |
| CLI/config validation | SMAG operator surface | GAP AUDIT | preserve Python/metaO API |
| HTTP service patterns | SMAG service | GAP AUDIT | transport has no authority |
| operational status | SMAG projection | GAP AUDIT | projection only |
| .NET typed client | `clients/dotnet` | FUTURE REFERENCE | external consumer only |
| engineering Work Unit manifests | `src/harness.js`/examples | ADAPT | engineering harness |
| allowlisted deterministic gates | harness | ADAPT | engineering harness |
| baseline/evidence report | harness | ADAPT | engineering harness |
| current-state generator | harness | ADAPT | engineering continuity |
| document-drift check | harness | ADAPT | engineering continuity |
| context handoff | harness | ADAPT | engineering continuity |
| evidence-level discipline | `AGENTS.md` | ADOPT semantics | DOCUMENTED/EXECUTED/MEASURED/INFERRED/NOT_VERIFIED |
| default-deny and isolation invariants | architecture/AGENTS/runtime refs | ADAPT | policy/admission/certification; #149 |

## 5. Governance composition

### 5.1 RiskDecision

Target semantics:

```text
ALLOW
REQUIRE_HUMAN
STOP
```

Risk consumes structured facts and produces metaO-owned authority. Runtime adapters do not self-authorize based on their own risk labels.

### 5.2 Mission budget split

Do not merge execution and independent-verification accounting.

```text
MissionBudget
├── ExecutionBudget
│   ├── money
│   ├── tokens
│   ├── wall time
│   └── attempts
└── VerificationBudget
    ├── money
    ├── tokens
    ├── wall time
    └── verifier attempts
```

Roadmap 8 A18 remains authoritative for acceptance/verifier accounting. SMAG contributes execution-budget semantics.

### 5.3 No override

A later approval cannot override an earlier authoritative stop:

```text
policy DENY        -> no approval override
risk STOP          -> no approval override
execution budget STOP -> no approval override
```

Approval resolves only a valid approval requirement.

## 6. Failure causality

The following distinctions are mandatory composition targets:

```text
CANCELLED != FAILED
TIMEOUT != GENERIC_FAILED
RECOVERY_PASS != ORIGINAL_EXECUTION_PASS
RETRY_ELIGIBLE != RETRY_EXECUTED
RECOVERY != AUTOMATIC_RETRY
UNKNOWN_FAILURE != TRANSIENT_FAILURE
```

Target flow:

```text
runtime outcome
-> factual failure classification
-> mutation/recovery state
-> retry eligibility
-> metaO replan decision
   -> retry same orchestrator OR failover to another orchestrator
-> new execution lineage/evidence
-> independent acceptance
```

A11 retry history remains authoritative. SMAG semantics may not create a second historical ledger.

## 7. Execution-stage evidence

Canonical stage statuses to adapt where they fit the metaO execution path:

```text
PASS
BLOCKED
FAILED
SKIPPED
NOT_REQUESTED
```

Definitions:

- `SKIPPED`: the stage belonged to the selected control-flow path but an earlier gate prevented execution.
- `NOT_REQUESTED`: the stage was not requested for this execution.

No report may claim PASS for work that did not run.

Execution reporting and telemetry are deterministic projections over facts; they cannot own policy, risk, budget, approval, retry, recovery, replan or terminal acceptance decisions.

## 8. Durable execution boundary

Conductor remains the durable execution mechanism/foundation candidate.

SMAG checkpoint/state/resume code is reused only as an invariant/test donor unless a later measured gap proves otherwise.

Desired Conductor conformance properties include:

- authoritative persisted state on resume;
- lineage binding;
- no unrelated checkpoint substitution;
- no duplicated side effect after interruption/resume;
- approval provenance remains bound when applicable;
- unsupported crash/distributed guarantees remain explicitly NOT_PROVEN.

## 9. Engineering-workload plugin

Coding-specific capabilities remain isolated:

```text
metaO Core
-> OrchestratorContract / workload boundary
-> EngineeringWorkloadPlugin
   -> WUS diff/path/workspace safety
   -> OpenHands/Codex/Cline runtime adapters
   -> optional Git delivery
```

Core must not acquire generic concepts such as diff, worktree, commit or pull request merely because engineering workloads need them.

At least two coding runtimes should satisfy the same plugin boundary before one is treated as mandatory.

## 10. Orchestrator/runtime expansion

Candidates inherited from the SMAG audit:

- Open Multi Agent
- Microsoft Agent Framework
- OpenAI Agents
- Mastra

Decision rule:

```text
NEW RUNTIME EXISTS != METAO NEEDS IT
```

A new adapter is justified only if it proves replacement/conformance, provides a materially useful capability, or serves a concrete product path. Framework-count growth is not a goal.

For every adopted runtime:

- SDK types stop at adapter boundary;
- same mission contract remains valid;
- canonical evidence remains framework-neutral;
- runtime DONE never equals metaO ACCEPTED;
- policy/risk/budget/approval/acceptance stay metaO-owned.

## 11. Provider-routing abstraction

Keep the two levels distinct:

```text
metaO selects ORCHESTRATOR
orchestrator/runtime may select MODEL/PROVIDER internally
```

SMAG cost-aware routing may provide capability/cost facts such as estimated execution cost, zero-credit support and provider class. Those facts may inform strategy only when authoritative; they do not become metaO strategy authority.

## 12. Engineering harness

Adapt SMAG harness concepts into the existing metaO Issue-first workflow, not as a second tracker.

Target flow:

```text
Project / Roadmap
-> Issue
-> Work Unit manifest
-> Branch
-> Implementation
-> deterministic harness gates
-> Evidence Report
-> PR
-> required acceptance/release gate
-> Merge
-> Current-State / Context Handoff
```

Requirements:

- Work Unit manifests are data, not arbitrary shell programs;
- commands are referenced through an allowlist;
- generated baseline/current-state comes from repository facts;
- document drift is detectable;
- handoff excludes secrets;
- tests cannot be weakened merely to make the suite green;
- deterministic checks are preferred over LLM calls;
- harness PASS is engineering evidence, not product acceptance authority.

## 13. Security / isolation

Security-relevant SMAG semantics are tracked in #149.

Target invariants:

- default deny for destructive or sensitive operations;
- runtime/credential/workspace isolation is an explicit admission/policy requirement;
- untrusted repository/runtime content is never instruction authority;
- secrets do not enter evidence, telemetry or handoff artifacts;
- adapter-declared permissions/capabilities are facts to verify, not self-granted authority;
- insufficient isolation fails closed or quarantines the runtime;
- runtime-specific sandbox mechanisms remain outside Core.

## 14. Operational surfaces

SMAG CLI/config/service/OTLP/.NET client work must first pass a gap audit against current metaO.

Every capability is classified as one of:

```text
ALREADY_STRONGER_IN_METAO
ADOPT_SEMANTICS
ADAPT
REFERENCE_ONLY
DEFER
REJECT
```

Transport and observability never gain governance or acceptance authority.

## 15. Explicit Core exclusions

Do not import into generic metaO Core:

- Cline/Codex/OpenHands agent loops;
- agent memory, prompts or internal tool graphs;
- MCP implementation details;
- multi-agent coordination semantics;
- framework-specific provider APIs;
- model/provider routing as final strategy authority;
- Git/worktree/diff/PR semantics;
- filesystem sandbox internals;
- SMAG Node/HTTP types;
- SMAG filesystem checkpoint store;
- any whole-donor dependency merely because copying it is easy.

## 16. Roadmap 8 overlap protection

The following existing authorities remain canonical:

- A02: independent verifier;
- A08: approval authority/freshness;
- A11: authoritative retry history;
- A12: canonical cross-orchestrator evidence;
- A18: acceptance/verifier accounting.

SMAG work composes around them and must not duplicate them.

## 17. Work Units

Parent: #138

P1 direct Control Plane / engineering leverage:

- #139 donor provenance / Composition Map
- #140 Risk Governance + ExecutionBudget
- #141 failure causality / recovery / retry / failover
- #142 execution-stage evidence + deterministic reporting
- #143 engineering harness / current-state / context handoff
- #146 checkpoint/resume invariants over Conductor
- #149 security / isolation / authority-boundary invariants

P2 bounded expansion:

- #144 engineering-workload plugin
- #145 orchestrator/runtime donor expansion and conformance
- #147 operational service/config/observability/client gap audit
- #148 cost-aware provider-routing facts beneath orchestrator selection

Recommended order:

```text
#139
-> continue independent Roadmap 8 dependencies
-> #140
-> #141
-> #142
-> #143
-> #149
-> #146
-> bounded #144/#145/#147/#148 according to proven need
```

## 18. Evidence policy

```text
DONOR_EXISTS != FIT_PROVEN
DOCUMENTED != EXECUTED
EXECUTED != ACCEPTED
ADAPT != COPY_WHOLE_DONOR
```

Every implementation must record:

- exact donor repository;
- exact donor commit;
- exact consumed path/symbol;
- reuse mode;
- donor tests preserved/adapted;
- new tests;
- real-path evidence;
- reused/adapted/new LOC when practical.

## 19. Acceptance for this documentation unit

This document is documentation evidence only.

```text
PRODUCT_CODE_CHANGE = NO
NEW_RUNTIME_DEPENDENCY = NO
FOUNDATION_CHANGE = NO
ACCEPTANCE_AUTHORITY_CHANGE = NO
```

Issue #139 remains the canonical documentation Work Unit. The main `docs/COMPOSITION-MAP.md` should link or incorporate this addendum through a safe non-destructive edit before #139 is closed.
