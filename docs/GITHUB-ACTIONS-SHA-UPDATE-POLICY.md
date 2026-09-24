# GitHub Actions Immutable-SHA Update Policy

This policy defines how metaO updates GitHub Actions references after workflows have been pinned to immutable commit SHAs.

## Scope

The policy applies to every external Action reference in `.github/workflows/**`, including first-party `actions/*` repositories and third-party Actions.

Workflow `uses:` entries must resolve to immutable commit SHAs. Mutable branches, floating tags, and channels such as `@main`, `@v4`, `@stable`, or equivalent are not acceptable as the executable ref.

A human-readable release marker must remain beside the SHA when an upstream release/tag mapping exists, for example:

```yaml
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
```

The comment is informational. The commit SHA is the authority actually executed by GitHub Actions.

## 1. Source verification

Before changing an Action SHA:

1. Identify the canonical upstream repository for the Action.
2. Resolve the intended upstream release/tag to the exact commit from that repository. Do not copy a SHA from an unrelated fork, third-party blog, generated snippet, or unverified search result.
3. Record the upstream repository, human-readable release/tag, and full immutable commit SHA in the change description.
4. Use the full commit SHA rather than an abbreviated hash.
5. For third-party Actions, review the upstream ownership/repository identity and material release notes or diff before adopting the new commit.
6. If a mutable channel such as `stable` has no trustworthy release-to-commit mapping, treat the update as unresolved until a specific upstream commit has been independently identified and reviewed.

## 2. Patch construction

Action-pin updates should be isolated from functional workflow changes whenever practical.

For a pure pinning tranche:

- change only `uses:` refs and adjacent release-marker comments required to describe those refs;
- do not alter workflow triggers, permissions, runner labels, environment variables, secret names, authorization gates, provider configuration, runtime dependency versions, test commands, evidence semantics, or acceptance semantics;
- keep unrelated formatting churn out of the patch;
- compare against the exact base head and record the exact resulting head.

If functional workflow changes are necessary, they must be reviewed and qualified independently from the Action-pin update.

## 3. Review requirements

Review must verify both supply-chain identity and patch containment.

The reviewer should confirm:

- every changed executable Action ref is a full immutable SHA;
- each SHA belongs to the intended canonical upstream Action repository;
- the release marker matches the intended upstream release/tag when one exists;
- the diff contains no unrelated workflow or product changes;
- secrets, credentials, tokens, API keys, or other sensitive material are not introduced into workflow context, logs, traces, PR bodies, or artifacts;
- the exact base head and exact proposed head are recorded for reproducibility.

`MERGEABLE` is not equivalent to `MERGE_READY`. Merge readiness requires the repository's normal review and qualification gates in addition to GitHub reporting that the branch can be merged.

## 4. Rollout ordering

Roll out Action-SHA changes in increasing blast radius:

1. privileged, self-hosted, secret-bearing, or credential-backed workflows;
2. core hosted/runtime workflows;
3. special hosted workflows and non-standard third-party Actions;
4. roadmap and lower-risk hosted workflows;
5. policy/documentation normalization and residual cleanup.

Prefer separate, stacked tranches when that makes scope easier to prove. Each tranche must state its base and exact head so reviewers can distinguish inherited changes from tranche-local changes.

## 5. Execution evidence and blocker classification

Pinning a workflow is implementation evidence, not runtime acceptance.

The following distinctions remain mandatory:

```text
IMPLEMENTATION != EXECUTION
EXECUTION != ACCEPTANCE
NOT_RUN != PASS
MERGEABLE != MERGE_READY
```

If a GitHub-hosted job terminates before workflow steps execute, especially when the observed step list is empty (`steps=[]`), classify it as:

```text
EXECUTION = BLOCKED_EXTERNAL
```

Do not convert that condition into functional PASS or functional FAIL. Record the run ID, job ID, exact commit head, observed step list, and the active external blocker reference.

A functional claim requires evidence that the intended workflow steps actually executed and produced the required verification evidence.

## 6. Rollback

Every Action-SHA update must remain directly reversible.

If an update causes a verified regression after steps actually execute:

1. capture the failing run/job evidence and exact head;
2. determine whether the regression is attributable to the Action update rather than an external runner/platform blocker;
3. revert the Action ref to the previously reviewed immutable SHA;
4. preserve the human-readable release marker corresponding to the restored SHA;
5. rerun the same qualification path when execution infrastructure is available;
6. record both the reverted head and the evidence supporting the rollback.

Do not roll back merely because GitHub reports a hosted-runner failure before steps. `steps=[]` remains an external execution blocker, not proof that the Action SHA is defective.

## 7. Update record

Each pin/update tranche should record at minimum:

- tracker/issue reference;
- PR reference;
- exact base head;
- exact proposed head;
- files changed;
- old Action ref;
- new immutable SHA and release marker;
- upstream source used to resolve the SHA;
- patch-containment result;
- execution state (`NOT_RUN`, `BLOCKED_EXTERNAL`, or actually executed result);
- run/job identifiers when execution evidence exists;
- rollback SHA or prior known-good SHA.

## 8. Secrets and provider-backed workflows

Action maintenance does not authorize provider-backed, paid, secret-bearing, or credential-backed execution.

No credential, token, API key, or secret may be copied into request context, traces, PR bodies, logs, comments, or artifacts as part of Action-SHA maintenance. Existing authorization gates for paid or provider-backed pilots remain independent and must be satisfied explicitly before such execution occurs.

## 9. Periodic maintenance

Action SHAs should be reviewed periodically and when upstream security or compatibility releases warrant an update. Maintenance is an explicit reviewed change; do not automatically follow mutable upstream tags in executable workflow refs.

When a newer release is adopted, repeat source verification, patch-containment review, staged rollout, execution classification, and rollback preparation from this policy.
