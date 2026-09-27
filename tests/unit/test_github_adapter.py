from __future__ import annotations

import unittest

from metao.github_adapter import (
    GitHubRepositoryAdapter,
    MutationAuthorization,
    MutationDenied,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.next_payload = {"id": 7, "number": 12, "sha": "abc", "html_url": "https://github.com/tihotm/metaO/pull/12", "merged": True}

    def request(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        return self.next_payload


class GitHubRepositoryAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.adapter = GitHubRepositoryAdapter(self.transport)
        self.auth = MutationAuthorization("tihotm/metaO", "issue.create", "exec-1", "policy-1", "operator-1")

    def test_reads_do_not_require_mutation_authority(self) -> None:
        self.adapter.repository("tihotm/metaO")
        self.assertEqual(self.transport.calls[0][0:2], ("GET", "repos/tihotm/metaO"))

    def test_mutation_fails_closed_without_authority(self) -> None:
        with self.assertRaises(MutationDenied):
            self.adapter.create_issue("tihotm/metaO", title="x")
        self.assertEqual(self.transport.calls, [])

    def test_mutation_rejects_wrong_operation_binding(self) -> None:
        with self.assertRaises(MutationDenied):
            self.adapter.create_issue(
                "tihotm/metaO", title="x",
                authorization=MutationAuthorization("tihotm/metaO", "branch.create", "exec-1", "policy-1", "operator-1"),
            )
        self.assertEqual(self.transport.calls, [])

    def test_mutation_returns_normalized_evidence(self) -> None:
        result = self.adapter.create_issue("tihotm/metaO", title="x", authorization=self.auth)
        self.assertEqual(result.operation, "issue.create")
        self.assertEqual(result.evidence["number"], 12)
        self.assertNotIn("token", result.evidence)
        self.assertEqual(self.transport.calls[0][0:2], ("POST", "repos/tihotm/metaO/issues"))

    def test_merge_requires_expected_head_sha_and_uses_it(self) -> None:
        auth = MutationAuthorization("tihotm/metaO", "pull_request.merge", "exec-1", "policy-1", "operator-1")
        result = self.adapter.merge_pr("tihotm/metaO", number=12, expected_head_sha="head-1", authorization=auth)
        self.assertTrue(result.evidence["merged"])
        self.assertEqual(self.transport.calls[0][2]["sha"], "head-1")


if __name__ == "__main__":
    unittest.main()
