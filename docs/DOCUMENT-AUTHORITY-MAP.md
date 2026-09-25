# Document Authority Map

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Last reconciled commit: `7c8fef9a841dbc454cabc6a0b5b1bed49afbda02`

## Canonical documents

- `docs/POST-MVP-OPERATIONAL-BASELINE-V1.md`
- `docs/ARCHITECTURE.md`
- `docs/REQUIREMENTS.md`
- `docs/QUALITY-MODEL.md`
- `docs/CAPABILITY-MAP.md`
- `docs/VERIFICATION-AND-VALIDATION.md`
- `docs/OPERATIONS.md`
- `docs/CLOSURE-PLAN.md`
- `docs/TRACEABILITY.md`
- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`
- `docs/AGENT-HARNESS-ENGINEERING-GUIDE.md`
- `docs/CHASSIS-SCORECARD-SCHEMA-2026-08-26.md`
- `docs/CANONICAL-DONOR-EVALUATION-MATRIX.md`

## Operational documents

- `docs/RELEASE-READINESS.md`
- `docs/LOCAL-RELEASE-GATE.md`
- `docs/GITHUB-WORKFLOW.md`
- `docs/LOCAL-WORK-COMMIT-REMOTE-SYNC-POLICY.md`
- `docs/GITHUB-LABEL-TAXONOMY.md`
- `docs/GITHUB-ACTIONS-SUPPORT-PACKET.md`
- `docs/RELEASE-EVIDENCE-VALIDATOR.md`
- `docs/EMPIRICAL-EVIDENCE-AUDIT.md`

## Reference / historical documents

- `docs/EMPIRICAL-RESEARCH-AND-REPRODUCIBILITY.md` — superseded for formal reproduction/replication terminology; retained as a non-conflicting historical/domain-specific reference.
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

## Governance rules

- canonical documents own current authority;
- `EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md` owns current empirical-claim documentation and formal reproduction/replication terminology;
- `EMPIRICAL-RESEARCH-AND-REPRODUCIBILITY.md` is superseded for formal reproduction/replication terminology and remains reference-only for non-conflicting historical/domain-specific rules;
- empirical-method documents do not mint architecture, policy, score/weight, evidence, or acceptance authority;
- `AGENT-HARNESS-ENGINEERING-GUIDE.md` owns agent/harness authoring, progressive-disclosure, anti-redundancy, and evaluation guidance; it does not override architecture, governance, benchmark identity, verification, or Acceptance authority;
- `AGENTS.md` is an execution entrypoint/router and must remain subordinate to canonical owner documents rather than becoming a parallel source of project truth;
- `CHASSIS-SCORECARD-SCHEMA-2026-08-26.md` owns the frozen chassis comparison contract; methodological guidance must not silently change its hard gates or weights;
- `CANONICAL-DONOR-EVALUATION-MATRIX.md` owns current donor research dispositions; donor claims remain bounded by their recorded evidence grade;
- operational documents own execution/run-state and blocker descriptions;
- `LOCAL-WORK-COMMIT-REMOTE-SYNC-POLICY.md` owns worktree/commit/branch/remote synchronization, change classification, review budgets, decomposition, and large-change exception rules; its thresholds are repository governance triggers rather than empirical quality scores;
- `EMPIRICAL-EVIDENCE-AUDIT.md` records traceability/reproducibility gaps and must not silently rewrite historical evidence or architecture decisions;
- reference documents may be used as evidence but not as mutable authority for current status;
- historical documents are immutable except for pointer updates and supersession notices;
- closure-plan status does not silently redefine requirements.
