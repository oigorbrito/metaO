# Agent Instructions

## Project closure checklist activation

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

Maintain these distinctions:

```text
DOCUMENTED != IMPLEMENTED
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
ISSUE_CLOSED != PROJECT_CLOSED
PR_MERGED != PROJECT_CLOSED
BLOCKED != PASS
NOT_EXECUTED != PASS
```

Issue and PR state may provide traceability, but they are not project-closure evidence by themselves.