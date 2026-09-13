# GitHub Action SHA Pinning Policy

## Purpose

All external GitHub Actions used by metaO workflows MUST be pinned to an immutable full 40-character commit SHA. Mutable tags and branches such as `@v4`, `@v5`, `@main`, and `@stable` are not permitted in committed workflows.

Local actions referenced through `./...` and `docker://...` references are outside this rule because they do not resolve through a mutable repository ref.

## Required form

Use the immutable SHA and retain a human-readable release/ref marker as a comment when one exists:

```yaml
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
```

The comment is informational. The SHA is the execution authority.

## Resolving a new pin

1. Resolve the desired upstream release/tag/branch directly from the official upstream repository.
2. Record the exact upstream commit SHA and the human-readable release/ref it represents.
3. For third-party Actions, confirm repository identity and ownership before accepting the SHA.
4. Do not infer a SHA from mirrors, blog posts, examples, or copied workflow snippets.
5. Keep the change scoped to `uses:` references unless the Action upgrade requires a separately reviewed semantic change.

## Review requirements

Every Action pin update MUST be reviewed as a supply-chain change. Review must verify:

- upstream repository identity;
- old SHA and new SHA;
- release/tag/ref being represented;
- upstream release notes or diff when moving between releases;
- whether Action inputs, permissions, runtime requirements, or outputs changed;
- whether the workflow has access to repository secrets or a self-hosted runner;
- whether the patch changes anything other than intended Action references.

Privileged, self-hosted, and secret-bearing workflows receive highest review priority and should be updated before lower-risk hosted workflows when a security update is required.

## Rollout order

For planned updates, use this order unless a security incident requires immediate coordinated rollout:

1. non-secret hosted workflows;
2. core hosted/runtime workflows;
3. privileged/self-hosted readiness workflows;
4. secret-bearing/provider workflows.

Each stage should retain an exact-head evidence boundary. A red GitHub Actions conclusion with no executed steps is not a functional regression and must be classified separately from code/test failure.

## Validation

Run:

```bash
python scripts/validate_github_action_pins.py
```

The validator scans `.github/workflows/*.yml` and `.yaml` files and fails when an external `uses:` reference is not a full 40-character hexadecimal SHA.

CI SHOULD run this validator before the unit suite. A passing static pin validator proves only that refs are immutable; it does not prove the Action itself is trustworthy or that workflow execution succeeded.

## Rollback

Rollback is an explicit pin change to the previously reviewed commit SHA. Do not restore a mutable tag as a shortcut.

A rollback PR should record:

- failing or suspect new SHA;
- previous known pin;
- evidence that triggered rollback;
- affected workflows;
- whether any secret-bearing/self-hosted workflow executed the suspect pin;
- exact head used for post-rollback qualification.

If a suspect Action ran with repository secrets or on a persistent self-hosted runner, treat that as a security review boundary rather than only a CI regression.

## Emergency response

If an upstream Action compromise or suspicious tag movement is suspected:

1. stop updating to the affected ref;
2. identify every workflow using the affected Action SHA;
3. determine whether secret-bearing or self-hosted jobs executed it;
4. pin or rollback to a reviewed known-good SHA;
5. rotate credentials when exposure cannot be ruled out;
6. document exact runs, SHAs, and resulting disposition.

## Evidence semantics

`PINNED` means the workflow contains an immutable Action SHA.

`VALIDATOR_PASS` means the static repository scan found no mutable external `uses:` refs.

Neither state implies workflow execution, functional PASS, merge readiness, provider success, or `#360_OPERATIONAL_PASS`.
