# Issue 523 — trusted Git bridge for project supervision

This slice replaces the synthetic repository boundary in the #360-oriented project supervision integration with `GitRepositoryCheckpointPort`.

Authority path:

```text
project scheduler target
-> mission runner exact executor
-> executor mutates local Git worktree
-> host-side GitRepositoryCheckpointPort observes clean HEAD
-> executor-reported repository state must match trusted HEAD
-> provider-diverse capacity failover revalidates unchanged checkpoint
-> downstream work receives the accepted trusted checkpoint state
```

Evidence boundary:

```text
REAL_LOCAL_GIT_WORKTREE = PREPARED
HOST_OBSERVED_HEAD = PREPARED
EXECUTOR_SHA_DRIFT_REJECTION = PREPARED
PROVIDER_DIVERSE_HANDOFF_REVALIDATION = PREPARED
REMOTE_GIT_TRANSFER = NOT_IMPLEMENTED
CROSS_HOST_TRANSPORT = NOT_IMPLEMENTED
CREDENTIAL_BACKED_PROVIDER_EXECUTION = NOT_RUN
FUNCTIONAL_PASS = NO
MERGE_READY = NO
```

No PASS is claimed without execution on the exact head.
