# Agent Instructions

## 1. Authority and context loading

Treat this file as the repository entrypoint for agent execution, not as a replacement for canonical project documentation.

Before material architecture, runtime, governance, benchmark, evidence, release, or Acceptance work, consult the applicable owner documents in:

- `docs/DOCUMENT-AUTHORITY-MAP.md`
- `docs/AGENT-HARNESS-ENGINEERING-GUIDE.md`
- `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`

Load only the task-relevant canonical documents rather than treating the entire historical documentation corpus as current instruction context.

Non-negotiable distinctions:

```text
DOCUMENTED != IMPLEMENTED
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
TASK_SUCCESS != INSTRUCTION_COMPLIANCE
PAPER_RESULT != METAO_RESULT
BENCHMARK_EVIDENCE != METAO_ACCEPTANCE
ISSUE_CLOSED != PROJECT_CLOSED
PR_MERGED != PROJECT_CLOSED
BLOCKED != PASS
NOT_EXECUTED != PASS
```

If instructions conflict, the canonical owner document identified by `docs/DOCUMENT-AUTHORITY-MAP.md` governs. This file does not override frozen architecture, governance, evidence, or Acceptance contracts.

## 2. Engineering workflow

Use the repository's Issue-first workflow for material changes. `docs/GITHUB-WORKFLOW.md` owns the complete lifecycle and merge rules.

Agent/harness or documentation changes must avoid duplicating normative rules across files. Prefer one authoritative rule plus references.

Material agent/harness changes must be evaluated according to `docs/AGENT-HARNESS-ENGINEERING-GUIDE.md` and empirical claims must follow `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.

Benchmark or paper evidence may inform design and selection only. It never bypasses capability eligibility, health/capacity/quarantine/certification, policy/budget/approval, verification, or final Acceptance.

## 3. Project closure checklist activation

The repository contains a reusable project-closure template at:

`.project/closure/PROJECT-CLOSURE-DOCUMENTATION-TEMPLATE.md`

Do **not** instantiate, execute, or populate that checklist merely because the file exists.

Activate it only when the user explicitly requests project closure, release/readiness closure, a final checklist, a closure audit, or an equivalent assessment.

Before using the template, the responsible agent must perform an applicability review:

1. Read the template and the repository's current authoritative documentation.
2. State whether the template is `VALID_AS_IS`, `NEEDS_ADAPTATION`, or `NOT_APPLICABLE` for the requested closure scope.
3. Identify concrete project changes, requirements, risks, evidence types, or scope facts that justify adding, removing, or modifying checklist criteria.
4. Present those proposed adaptations explicitly; do not silently rewrite the template to fit the desired outcome.
5. Only after the closure scope and template applicability are established may the agent instantiate a working project-specific checklist and collect or request evidence.
6. Do not execute tests, create issues, close issues, merge PRs, or perform implementation work solely because the closure template exists. Such actions require an explicit user request or a separate authorized workflow.

Issue and PR state may provide traceability, but they are not project-closure evidence by themselves.
