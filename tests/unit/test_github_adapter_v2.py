from __future__ import annotations

import unittest

from metao.github_adapter import GitHubRepositoryAdapter, MutationAuthorization, MutationDenied


class FakeTransport:
    def __init__(self) -> None:
        self.calls = []
        self.next_payload = {"id": 7, "number": 12, "sha": "abc", "html_url": "https://github.com/tihotm/metaO/pull/12", "merged": True}

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.next_payload


class GitHubRepositoryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.adapter = GitHubRepositoryAdapter(self.transport)
        self.auth = MutationAuthorization("tihotm/metaO", "issue.create", "exec-1", "policy-1", "operator-1")

    def test_read_without_mutation_authority(self):
        self.adapter.repository("tihotm/metaO")
        self.assertEqual(self.transport.calls[0][:2], ("GET", "repos/tihotm/metaO"))

    def test_review_reads_do_not_require_mutation_authority(self):
        self.adapter.pull_request_reviews("tihotm/metaO", 12)
        self.adapter.pull_request_review_comments("tihotm/metaO", 12)
        self.assertEqual(self.transport.calls[0][:2], ("GET", "repos/tihotm/metaO/pulls/12/reviews"))
        self.assertEqual(self.transport.calls[1][:2], ("GET", "repos/tihotm/metaO/pulls/12/comments"))

    def test_mutation_fails_closed_without_authority(self):
        with self.assertRaises(MutationDenied):
            self.adapter.create_issue("tihotm/metaO", title="x")
        self.assertEqual(self.transport.calls, [])

    def test_wrong_operation_binding_is_denied(self):
        auth = MutationAuthorization("tihotm/metaO", "branch.create", "exec-1", "policy-1", "operator-1")
        with self.assertRaises(MutationDenied):
            self.adapter.create_issue("tihotm/metaO", title="x", authorization=auth)
        self.assertEqual(self.transport.calls, [])

    def test_evidence_is_normalized_without_credentials(self):
        result = self.adapter.create_issue("tihotm/metaO", title="x", authorization=self.auth)
        self.assertEqual(result.operation, "issue.create")
        self.assertEqual(result.evidence["number"], 12)
        self.assertNotIn("token", result.evidence)

    def test_review_submission_requires_exact_authority(self):
        with self.assertRaises(MutationDenied):
            self.adapter.submit_review("tihotm/metaO", number=12, event="COMMENT", authorization=self.auth)
        self.assertEqual(self.transport.calls, [])

    def test_review_submission_sends_allowed_event(self):
        auth = MutationAuthorization("tihotm/metaO", "pull_request.review.submit", "exec-1", "policy-1", "operator-1")
        result = self.adapter.submit_review("tihotm/metaO", number=12, body="validation", event="COMMENT", authorization=auth)
        self.assertEqual(result.operation, "pull_request.review.submit")
        self.assertEqual(self.transport.calls[0][0:2], ("POST", "repos/tihotm/metaO/pulls/12/reviews"))
        self.assertEqual(self.transport.calls[0][2]["event"], "COMMENT")

    def test_review_submission_rejects_unsupported_event_before_transport(self):
        auth = MutationAuthorization("tihotm/metaO", "pull_request.review.submit", "exec-1", "policy-1", "operator-1")
        with self.assertRaises(ValueError):
            self.adapter.submit_review("tihotm/metaO", number=12, event="MERGE", authorization=auth)
        self.assertEqual(self.transport.calls, [])

    def test_merge_binds_expected_head_sha(self):
        auth = MutationAuthorization("tihotm/metaO", "pull_request.merge", "exec-1", "policy-1", "operator-1")
        result = self.adapter.merge_pr("tihotm/metaO", number=12, expected_head_sha="head-1", authorization=auth)
        self.assertTrue(result.evidence["merged"])
        self.assertEqual(self.transport.calls[0][2]["sha"], "head-1")


if __name__ == "__main__":
    unittest.main()
