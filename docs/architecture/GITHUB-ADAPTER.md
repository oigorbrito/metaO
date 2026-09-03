# Governed GitHub repository adapter

The first operational GitHub slice lives in `metao.github_adapter`.

It separates GitHub transport from metaO governance and provides read operations plus explicitly authorized mutations. A mutation authorization is bound to the repository, exact operation, execution, policy bundle, and actor. Missing or mismatched authority fails closed before transport is called.

Supported operations in this slice:

- repository, issue, pull-request, and workflow-run reads;
- issue creation;
- branch creation;
- file creation;
- pull-request creation;
- pull-request comments;
- pull-request merge with an expected head SHA.

The normalized result intentionally exposes only audit-useful resource fields. Credentials are transport concerns and are never returned as evidence.

This is an adapter, not permission by itself. The caller remains responsible for deciding whether an execution is authorized and for supplying the corresponding `MutationAuthorization`. Merge is guarded by the expected head SHA so a moved PR head causes GitHub to reject the mutation rather than silently merging a different revision.

The next hardening layer should add governed update/delete operations, review submission/thread operations, CI/status inspection, idempotency keys for retriable writes, and integration with the existing metaO execution/evidence ledger. These are deliberately not implied by this first slice.
