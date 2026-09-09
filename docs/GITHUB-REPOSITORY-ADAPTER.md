# Governed GitHub Repository Adapter

## Purpose

`metao.github_adapter.GitHubRepositoryAdapter` is the provider-isolated GitHub repository integration surface for metaO. It translates explicitly authorized repository operations into GitHub REST calls and returns normalized evidence suitable for audit.

The adapter does not decide policy, invent authorization, or grant repository authority. Reads are transport operations; every mutation is fail-closed unless the caller supplies a `MutationAuthorization` bound to the exact repository and operation plus non-empty execution, policy-bundle, and actor identities.

## Supported reads

- repository metadata;
- issue lookup;
- pull-request lookup;
- pull-request reviews and review comments;
- workflow-run lookup and filtered workflow-run listing;
- workflow-job listing.

## Supported mutations

- issue creation — `issue.create`;
- branch creation — `branch.create`;
- file creation through the Contents API — `file.create`;
- Git blob creation — `git.blob.create`;
- Git tree creation — `git.tree.create`;
- Git commit-object creation — `git.commit.create`;
- pull-request creation — `pull_request.create`;
- pull-request comments — `pull_request.comment`;
- pull-request review submission — `pull_request.review.submit`;
- pull-request merge — `pull_request.merge`.

Each mutating method checks authority before transport invocation. An absent authorization or a repository/operation mismatch raises `MutationDenied` without sending a request.

## Evidence boundary

Mutation calls return `GitHubOperationResult` with the operation name, repository, a resource locator, and a normalized evidence map. The adapter retains only supported GitHub result identifiers such as `id`, `number`, `sha`, `ref`, `merged`, `message`, and `html_url`; credentials are never copied into operation evidence.

## Expected-head protection

Governed merge requires an explicit `expected_head_sha`; the adapter sends it as GitHub's merge `sha` precondition. A stale head is therefore rejected by GitHub rather than silently merging a different revision.

Low-level Git-object creation does not move branch refs by itself. Callers that need a branch-attached commit may use `create_file` through the Contents API or separately perform a governed ref-update capability when such a capability is introduced. The current adapter intentionally does not expose arbitrary ref mutation beyond branch creation.

## Current boundaries

- The adapter is framework-neutral and depends only on the `GitHubTransport` protocol.
- `UrllibGitHubTransport` is the concrete dependency-free GitHub REST transport.
- Core governance remains outside this module; the adapter consumes authority but never creates it.
- Deterministic unit tests use fake transports and perform no live repository mutation.
- Passing fake-transport tests proves request construction and governance boundaries, not live GitHub credentials, network availability, repository permissions, or provider-side behavior.
- Hosted GitHub Actions execution remains independently subject to the external runner blocker tracked in #71.
