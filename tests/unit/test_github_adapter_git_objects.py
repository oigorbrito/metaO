from __future__ import annotations

import unittest

from metao.github_adapter import GitHubRepositoryAdapter, MutationAuthorization, MutationDenied


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.responses: list[dict] = []

    def queue(self, *payloads: dict) -> None:
        self.responses.extend(payloads)

    def request(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        if self.responses:
            return self.responses.pop(0)
        return {"sha": "default-sha"}


def auth(operation: str) -> MutationAuthorization:
    return MutationAuthorization(
        repository="oigorbrito/metaO",
        operation=operation,
        execution_id="exec-363",
        policy_bundle_id="policy-363",
        actor_id="operator-363",
    )


class GitHubGitObjectOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.adapter = GitHubRepositoryAdapter(self.transport)
        self.repository = "oigorbrito/metaO"

    def test_blob_tree_and_commit_require_exact_authority_before_transport(self) -> None:
        cases = (
            lambda authorization: self.adapter.create_blob(
                self.repository,
                content="hello",
                authorization=authorization,
            ),
            lambda authorization: self.adapter.create_tree(
                self.repository,
                tree=[{"path": "hello.txt", "mode": "100644", "type": "blob", "sha": "blob-1"}],
                authorization=authorization,
            ),
            lambda authorization: self.adapter.create_commit(
                self.repository,
                message="governed commit",
                tree_sha="tree-1",
                parents=["parent-1"],
                authorization=authorization,
            ),
        )
        for operation in cases:
            with self.assertRaises(MutationDenied):
                operation(None)
            with self.assertRaises(MutationDenied):
                operation(auth("issue.create"))
        self.assertEqual(self.transport.calls, [])

    def test_blob_tree_and_commit_use_git_data_endpoints_and_normalize_sha(self) -> None:
        self.transport.queue(
            {"sha": "blob-1", "url": "https://api.github.com/blob/1"},
            {"sha": "tree-1", "url": "https://api.github.com/tree/1"},
            {"sha": "commit-1", "url": "https://api.github.com/commit/1"},
        )

        blob = self.adapter.create_blob(
            self.repository,
            content="hello",
            authorization=auth("git.blob.create"),
        )
        tree = self.adapter.create_tree(
            self.repository,
            tree=[{"path": "hello.txt", "mode": "100644", "type": "blob", "sha": blob.evidence["sha"]}],
            base_tree="base-tree",
            authorization=auth("git.tree.create"),
        )
        commit = self.adapter.create_commit(
            self.repository,
            message="governed commit",
            tree_sha=tree.evidence["sha"],
            parents=["parent-1"],
            authorization=auth("git.commit.create"),
        )

        self.assertEqual(blob.evidence["sha"], "blob-1")
        self.assertEqual(tree.evidence["sha"], "tree-1")
        self.assertEqual(commit.evidence["sha"], "commit-1")
        self.assertEqual(
            self.transport.calls,
            [
                ("POST", "repos/oigorbrito/metaO/git/blobs", {"content": "hello", "encoding": "utf-8"}),
                (
                    "POST",
                    "repos/oigorbrito/metaO/git/trees",
                    {
                        "tree": [{"path": "hello.txt", "mode": "100644", "type": "blob", "sha": "blob-1"}],
                        "base_tree": "base-tree",
                    },
                ),
                (
                    "POST",
                    "repos/oigorbrito/metaO/git/commits",
                    {"message": "governed commit", "tree": "tree-1", "parents": ["parent-1"]},
                ),
            ],
        )

    def test_git_object_inputs_fail_closed_before_transport(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.create_blob(
                self.repository,
                content="hello",
                encoding="hex",
                authorization=auth("git.blob.create"),
            )
        with self.assertRaises(ValueError):
            self.adapter.create_tree(
                self.repository,
                tree=[],
                authorization=auth("git.tree.create"),
            )
        with self.assertRaises(ValueError):
            self.adapter.create_commit(
                self.repository,
                message="",
                tree_sha="tree-1",
                parents=["parent-1"],
                authorization=auth("git.commit.create"),
            )
        self.assertEqual(self.transport.calls, [])

    def test_governed_issue_branch_file_pr_review_comment_merge_sequence(self) -> None:
        self.transport.queue(
            {"number": 91, "html_url": "https://github.com/oigorbrito/metaO/issues/91"},
            {"ref": "refs/heads/feat/91", "url": "https://api.github.com/ref/91"},
            {"content": {"sha": "blob-91"}, "commit": {"sha": "commit-91", "html_url": "https://github.com/oigorbrito/metaO/commit/commit-91"}},
            {"number": 92, "html_url": "https://github.com/oigorbrito/metaO/pull/92"},
            {"id": 93, "html_url": "https://github.com/oigorbrito/metaO/pull/92#issuecomment-93"},
            {"id": 94, "html_url": "https://github.com/oigorbrito/metaO/pull/92#pullrequestreview-94"},
            {"merged": True, "sha": "merge-92", "message": "Pull Request successfully merged"},
        )

        issue = self.adapter.create_issue(
            self.repository,
            title="governed work",
            authorization=auth("issue.create"),
        )
        branch = self.adapter.create_branch(
            self.repository,
            branch="feat/91",
            sha="base-head",
            authorization=auth("branch.create"),
        )
        commit = self.adapter.create_file(
            self.repository,
            path="evidence.txt",
            content="governed",
            message="governed commit",
            branch="feat/91",
            authorization=auth("file.create"),
        )
        pr = self.adapter.create_pr(
            self.repository,
            head="feat/91",
            base="main",
            title="governed PR",
            authorization=auth("pull_request.create"),
        )
        comment = self.adapter.comment_pr(
            self.repository,
            number=pr.evidence["number"],
            body="qualification evidence",
            authorization=auth("pull_request.comment"),
        )
        review = self.adapter.submit_review(
            self.repository,
            number=pr.evidence["number"],
            body="reviewed",
            event="COMMENT",
            authorization=auth("pull_request.review.submit"),
        )
        merged = self.adapter.merge_pr(
            self.repository,
            number=pr.evidence["number"],
            expected_head_sha=commit.evidence["sha"],
            authorization=auth("pull_request.merge"),
        )

        self.assertEqual(issue.evidence["number"], 91)
        self.assertEqual(branch.evidence["ref"], "refs/heads/feat/91")
        self.assertEqual(commit.evidence["sha"], "commit-91")
        self.assertEqual(comment.evidence["id"], 93)
        self.assertEqual(review.evidence["id"], 94)
        self.assertTrue(merged.evidence["merged"])
        self.assertEqual(self.transport.calls[-1][2]["sha"], "commit-91")


if __name__ == "__main__":
    unittest.main()
