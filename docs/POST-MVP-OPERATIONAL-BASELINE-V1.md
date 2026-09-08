# POST_MVP_OPERATIONAL_BASELINE_V1

Status: CANONICAL BASELINE DRAFT FOR POST-MVP OPERATIONALIZATION
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Qualified executable commit: `366a835923a814fcabe65bf7cc0763f56d456108`
Date: 2026-09-08

A later documentation-only merge may advance repository `HEAD` without invalidating the executable evidence bound to the qualified commit above. Any later change to product code, packaging, executable tests, or workflows must be requalified before inheriting these PASS claims.

## 1. Repository identity

metaO is a framework-neutral meta-orchestrator / control plane for selecting, governing, supervising, and independently accepting pluggable orchestrators.

The current repository state is a Python package under `src/metao/` with Rust-native product direction preserved by the post-v0.1 architecture and acceptance docs. Python remains the executable repository language in this checkout; Rust is the canonical product direction for the long-term implementation track.

## 2. Current lifecycle phase

Current actual phase:

- post-MVP operational baseline reconstruction;
- post-v0.1 operationalization;
- the canonical Python operator initialization path is integrated and qualified locally on the exact executable state above;
- the clean-room qualification produced `487/487` unit PASS, README quickstart E2E PASS, installed-console negative-bootstrap E2E PASS, and canonical initialization E2E PASS;
- the documented first-use path reaches mission `ACCEPTED` and separate-process inspection from a fresh clone with an isolated venv;
- first-run failure paths fail early without partial mission persistence for the covered cases;
- hosted CI remains externally blocked before configured steps under #71.

This is not final project closure.

Initialization/onboarding-specific state:

```text
CANONICAL_ENTRYPOINT_IDENTIFIED = YES
BOOTSTRAP_PATH_IMPLEMENTED = YES
INSTALLED_CLI = YES
README_QUICKSTART_E2E_EXECUTED = YES
README_QUICKSTART_E2E_PASSES = YES
NEGATIVE_BOOTSTRAP_E2E_EXECUTED = YES
NEGATIVE_BOOTSTRAP_E2E_PASSES = YES
E2E_INIT_TEST_EXISTS = YES
E2E_INIT_TEST_EXECUTED = YES
E2E_INIT_TEST_PASSES = YES
INTEGRATED_INTO_MAIN = YES
E2E_PASSES_ON_INTEGRATED_PATH = YES
INITIALIZATION_RESOLVED = YES
HOSTED_CI_PASS = NO / BLOCKED_EXTERNAL (#71)
```

The initialization/onboarding conclusion is bounded to the qualified integrated executable path. It does not imply final project closure, hosted-CI PASS, or real external-provider success.

## 3. Frozen architecture

Frozen control-plane chain:

`Mission -> Strategy / Selection -> Policy / Budget -> OrchestratorContract -> Runtime Adapter -> Orchestrator -> Evidence -> Independent Acceptance -> Accept / Replan / Failover / Block`

Frozen invariant:

`Replacing an entire orchestrator, including its internal agents, tools, memory, and workflows, must not require changing metaO Core.`

Secondary invariant:

`ORCHESTRATOR_DONE != METAO_ACCEPTED`

## 4. Canonical implementation status

- Canonical repository language today: Python.
- Canonical product direction: Rust-native Core and contracts.
- Python role: product implementation plus semantic oracle/reference for slices that are not yet fully proven in Rust parity.
- Historical runtime evidence: OpenAI Agents, CrewAI, LangGraph, and local deterministic test seams.
- Current canonical operator initialization evidence uses the installed Python `metao` CLI and a real LangGraph runtime through declarative catalog, certification, admission, mission execution, independent acceptance, persistence, and separate-process inspection.
- Current README onboarding evidence additionally uses a committed deterministic local runtime/catalog example so a clean clone can reach `ACCEPTED` without hidden application modules, credentials, or external providers.

## 5. Authoritative documents

NORMATIVE_FOR_PROJECT:

- `docs/POST-MVP-OPERATIONAL-BASELINE-V1.md`
- `docs/ARCHITECTURE.md`
- `docs/REQUIREMENTS.md`
- `docs/CAPABILITY-MAP.md`
- `docs/QUALITY-MODEL.md`
- `docs/VERIFICATION-AND-VALIDATION.md`
- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`
- `docs/OPERATIONS.md`
- `docs/CLOSURE-PLAN.md`
- `docs/TRACEABILITY.md`
- `docs/DOCUMENT-AUTHORITY-MAP.md`

OPERATIONAL:

- `docs/RELEASE-READINESS.md`
- `docs/LOCAL-RELEASE-GATE.md`
- `docs/GITHUB-WORKFLOW.md`
- `docs/GITHUB-LABEL-TAXONOMY.md`
- `docs/GITHUB-ACTIONS-SUPPORT-PACKET.md`

EVIDENCE:

- `docs/RELEASE-EVIDENCE-VALIDATOR.md`
- `docs/RECONCILIATION-REPORT-228-271.md`
- `docs/FOUNDATION-FIT.md`
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md`

REFERENCE / HISTORICAL:

- `docs/POST-V0.1-PRODUCT-ROADMAP.md`
- `docs/ROADMAP-2-CLOSEOUT.md`
- `docs/ROADMAP-2-WU01-SECOND-REAL-RUNTIME.md`
- `docs/ROADMAP-2-WU02-DECLARATIVE-RUNTIME-CATALOG.md`
- `docs/ROADMAP-2-WU03-DURABLE-RUNTIME-QUARANTINE.md`
- `docs/ROADMAP-2-WU04-RUNTIME-CONTROL-CLI.md`
- `docs/ROADMAP-2-WU05-DETERMINISTIC-RUNTIME-FEEDBACK.md`
- `docs/ROADMAP-3-WU01-RUNTIME-CONFORMANCE-HARNESS.md`
- `docs/ROADMAP-3-WU02-RUNTIME-ADMISSION-GATE.md`
- `docs/ROADMAP-3-WU03-DURABLE-RUNTIME-CERTIFICATION.md`
- `docs/ROADMAP-3-WU04-REAL-RUNTIME-CERTIFICATION.md`
- `docs/ROADMAP-3-WU05-CLOSEOUT.md`
- `docs/ROADMAP-4-WU01-DECLARATIVE-CERTIFIED-ONBOARDING.md`
- `docs/ROADMAP-4-WU02-PASSED-CERTIFICATE-REUSE.md`
- `docs/ROADMAP-4-WU03-REAL-DECLARATIVE-CERTIFIED-RUNTIMES.md`
- `docs/ROADMAP-4-WU04-CLOSEOUT.md`
- `docs/ROADMAP-5-WU01-CERTIFICATE-FRESHNESS.md`
- `docs/ROADMAP-5-WU02-DURABLE-CERTIFICATE-REVOCATION.md`
- `docs/ROADMAP-5-WU03-CERTIFICATION-LIFECYCLE-CLI.md`
- `docs/ROADMAP-5-WU04-REAL-CERTIFICATE-LIFECYCLE.md`
- `docs/ROADMAP-5-WU05-LATEST-CERTIFICATION-VERDICT.md`
- `docs/ROADMAP-5-WU06-CLOSEOUT.md`
- `docs/ROADMAP-6-WU01-STACKED-INTEGRATION-AUDIT.md`
- `docs/ROADMAP-6-WU02-CANONICAL-INTEGRATION-CANDIDATE.md`
- `docs/ROADMAP-6-WU03-THIRD-RUNTIME-EVALUATION.md`
- `docs/ROADMAP-6-WU04-OPENAI-AGENTS-RUNTIME-ADAPTER.md`
- `docs/ROADMAP-6-WU05-THREE-RUNTIME-DECLARATIVE-REGRESSION.md`
- `docs/ROADMAP-6-WU06-CLOSEOUT.md`
- `docs/ROADMAP-7-WU01-FAILURE-AWARE-REPLAN-AUTHORITY.md`
- `docs/ROADMAP-7-WU02-DURABLE-REPLAN-ESCALATION.md`
- `docs/ROADMAP-7-WU03-THREE-RUNTIME-RECOVERY-REGRESSION.md`
- `docs/ROADMAP-7-WU04-CLOSEOUT.md`
- `docs/ROADMAP-7-INTEGRATION-CANDIDATE.md`
- `docs/ROADMAP-8-ACCEPTANCE-GAP-AUDIT.md`
- `docs/ROADMAP-8-A02-INDEPENDENT-VERIFIER-DONOR-FIT.md`
- `docs/ROADMAP-8-A05-A07-A09-AUTHORITATIVE-TERMINAL-SOURCES-FIT.md`
- `docs/ROADMAP-8-A08-A04-A06-TRUST-DONOR-FIT.md`
- `docs/ROADMAP-8-A11-AUTHORITATIVE-RETRY-HISTORY-FIT.md`
- `docs/ROADMAP-8-A14-BOUND-CONFIDENCE-ADVISORY-FIT.md`
- `docs/ROADMAP-8-A16-A19-TERMINAL-PROOF-ADVERSARIAL-CLOSURE-FIT.md`

## 6. Capability summary

Current capability truth is captured in `docs/CAPABILITY-MAP.md`. Short form:

- the canonical operator initialization/bootstrap path has current integrated local L6-style integration evidence: installed CLI, doctor, factory/runtime composition, required certification/admission, mission `ACCEPTED`, and cross-process inspect all executed successfully on the qualified executable state;
- the documented clean-room README quickstart is executable without hidden `my_app` modules or external credentials;
- installed-console negative bootstrap paths are integration-tested to fail early for the covered configuration/input errors without partial mission persistence;
- current executable evidence exists for the acceptance boundary, runtime invariants, governance budget/approval, replay/fencing, release validator, and several integration/runtime slices;
- some slices are only specified or partially composed;
- cross-orchestrator and hostile-boundary claims remain partitioned by evidence level and should not be collapsed into a single PASS bucket;
- hosted GitHub Actions remains externally blocked and is not product proof.

## 7. Evidence-level definitions

L0 `CONCEPT_ONLY`

L1 `SPECIFIED`

L2 `IMPLEMENTED`

L3 `WIRED`

L4 `FOCUSED_TESTED`

L5 `REGRESSION_TESTED`

L6 `INTEGRATION_TESTED`

L7 `OPERATIONAL_EVIDENCE`

Operational dimensions may include:

- `MULTIPROCESS`
- `REAL_RUNTIME`
- `REAL_EXTERNAL_SYSTEM`
- `FAULT_INJECTION`
- `ADVERSARIAL`
- `HOSTED_CI`

Rules:

- do not infer a higher level from a lower level;
- simulated evidence is not real runtime evidence;
- unit tests are not integration evidence;
- evidence from an older executable surface is not automatically evidence for a later changed executable surface;
- documentation-only commits may reference a prior exact qualified executable commit when the distinction is explicit.

Empirical claims at evidence-bearing levels are additionally governed by `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`; that protocol constrains documentation of evidence but does not redefine L0-L7.

## 8. Current capability / evidence matrix

See `docs/CAPABILITY-MAP.md` for the consolidated matrix.

Operational/onboarding closure slice at the qualified executable commit:

```text
CLEAN_CLONE_INSTALL = PASS
CLI_HELP = PASS
README_QUICKSTART = PASS
DOCTOR = PASS
RUNTIME_BOOTSTRAP = PASS
CERTIFICATION = PASS
FIRST_MISSION = ACCEPTED
CROSS_PROCESS_INSPECT = PASS
NEGATIVE_BOOTSTRAP_CASES = PASS
UNIT_REGRESSION = 487/487 PASS
WORKTREE_HYGIENE = PASS
HOSTED_CI = BLOCKED_EXTERNAL (#71)
```

## 9. Known blockers

- hosted GitHub Actions pre-step blocker remains external under #71; this no longer blocks the factual local conclusion that canonical initialization/onboarding is resolved on the qualified integrated executable state;
- exact JSON re-validation of historical release evidence was separately blocked by file availability in prior reconciliation;
- Rust canonical parity is still the product direction but not the only live implementation language in this checkout;
- independent numeric hard-gate audit items #420/#421 through #428/#429 remain separate work and must not be collapsed into initialization/onboarding status;
- remote branch-reference cleanup is repository hygiene, not product correctness, and may require a Git client because the connected repository API does not expose branch deletion.

## 10. Operational readiness

`POST_MVP_OPERATIONAL_READY` requires:

- canonical Rust workspace green on the exact accepted candidate path when that path is used;
- critical modules wired to the frozen architecture;
- Project Discovery end-to-end path available or explicitly deferred with evidence;
- policy, risk, budget, and independent acceptance enforced;
- durable execution state and recovery behavior present;
- real runtime and integration evidence for the required operational slice;
- external blockers separated from product correctness.

The canonical Python operator initialization/onboarding requirement is satisfied for executable `main@366a835923a814fcabe65bf7cc0763f56d456108`. That prerequisite must not be re-opened merely because hosted CI is blocked, but it also must not be used as a substitute for the remaining readiness requirements above.

## 11. Final closure

Final closure requires:

- documentation baseline completed;
- requirements traceable to architecture, tests, and evidence;
- architecture integrity preserved;
- implementation completeness for the closure target;
- integration and runtime diversity covered by evidence where required;
- reliability, security, operational fault, and validation gates met;
- repository/GitHub convergence completed;
- release/operations evidence captured for the exact authoritative state.

Current conclusion:

```text
INITIALIZATION = RESOLVED
README_ONBOARDING = QUALIFIED
NEGATIVE_BOOTSTRAP = QUALIFIED
POST_MVP_OPERATIONAL_READY = NOT_YET_CLAIMED
FINAL_PROJECT_CLOSURE = NO
```

## 12. Change control

Rules:

- historical handoffs remain historical evidence;
- status belongs in canonical baseline and capability map, not in every roadmap;
- architecture changes require an ADR/decision record;
- requirements changes require baseline revision;
- evidence claims must bind exact commit/test identity;
- documentation-only reconciliation must identify the executable commit it is describing instead of treating the documentation merge SHA as executed evidence;
- this baseline supersedes prior mixed-purpose roadmap authority for current operational planning.
