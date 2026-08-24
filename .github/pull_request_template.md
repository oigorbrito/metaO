## Related Issue

<!-- Every relevant implementation PR must be governed by an Issue created first. -->

- Tracks: #
- Parent / roadmap Issue (if applicable): #

## Outcome

<!-- What concrete repository outcome does this PR deliver? -->

## Scope

### In scope

-

### Out of scope

-

## Architecture / safety invariants

<!-- Keep only the applicable invariants and add others from the governing Issue. -->

- [ ] `ORCHESTRATOR_DONE != METAO_ACCEPTED` remains true.
- [ ] `ADOPT > ADAPT > BUILD` was respected.
- [ ] No framework SDK authority leaked into metaO Core/control-plane.
- [ ] No silent scope expansion was introduced beyond the governing Issue.

## Change surface

- Production/Core:
- Adapter/plugin:
- Tests:
- Workflows/harness:
- Documentation:
- Persistence/schema:

## Validation / evidence

<!-- Do not convert prepared tests or static review into PASS. Record exact commands, workflow runs, job IDs, and/or evidence artifacts. -->

```text
IMPLEMENTATION = PREPARED | COMPLETE
EXECUTION = NOT_RUN | PASS | TEST_FAIL | BOOTSTRAP_FAIL | HARNESS_FAIL | BLOCKED_EXTERNAL
FUNCTIONAL_PASS = YES | NO
```

### Focused tests

```text
NOT_RUN
```

### Regression

```text
NOT_RUN
```

### Real runtime / sandbox / integration evidence

```text
NOT_APPLICABLE | NOT_RUN
```

### Exact evidence binding

- Branch:
- Commit SHA:
- Clean worktree required: YES / NO / N/A
- Workflow/run/job IDs:
- Evidence artifact/path:

## Failure classification

- [ ] Any observed failure is classified as product/test failure vs bootstrap/harness/external infrastructure.
- [ ] A job that never reached executable steps is not reported as a functional code failure.
- [ ] PASS is claimed only for tests/gates that actually executed successfully.

## Merge gate

- [ ] Governing Issue acceptance criteria are satisfied or explicitly updated.
- [ ] Required executable evidence is green.
- [ ] No unresolved review thread remains.
- [ ] Dependency/base PR state is valid.
- [ ] Documentation/evidence is current for this exact head SHA.

```text
MERGE_READY = NO
```

<!-- Keep draft/unmerged while MERGE_READY = NO. Close the Issue only after the accepted change is merged or explicitly dispositioned. -->
