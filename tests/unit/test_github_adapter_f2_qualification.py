from __future__ import annotations

import io
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from metao.github_adapter import GitHubAdapterError, GitHubRepositoryAdapter, UrllibGitHubTransport


REPOSITORY = "tihotm/metaO"
RUN_ID = 33760147938
JOB_ID = 100665907672
HEAD_SHA = "b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437"

RUN_PAYLOAD = {
    "id": RUN_ID,
    "head_sha": HEAD_SHA,
    "status": "completed",
    "conclusion": "failure",
    "run_attempt": 6,
}

JOBS_PAYLOAD = {
    "total_count": 1,
    "jobs": [
        {
            "id": JOB_ID,
            "run_id": RUN_ID,
            "head_sha": HEAD_SHA,
            "status": "completed",
            "conclusion": "failure",
            "name": "test",
            "steps": [],
            "runner_id": 0,
            "runner_name": "",
            "runner_group_id": 0,
            "runner_group_name": "",
        }
    ],
}


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object | None]] = []

    def request(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        if path == f"repos/{REPOSITORY}/actions/runs/{RUN_ID}":
            return RUN_PAYLOAD
        if path == f"repos/{REPOSITORY}/actions/runs/{RUN_ID}/jobs?filter=latest&per_page=100":
            return JOBS_PAYLOAD
        raise AssertionError(f"unexpected route: {path}")


def classify_f2(run_payload: dict, jobs_payload: dict, job_id: int) -> dict[str, str]:
    """Test oracle for the already-frozen F2 semantics; not product authority."""
    jobs = [job for job in jobs_payload.get("jobs", []) if job.get("id") == job_id]
    if len(jobs) != 1:
        raise AssertionError("exact target job not found exactly once")
    job = jobs[0]

    if run_payload.get("id") != RUN_ID or run_payload.get("head_sha") != HEAD_SHA:
        raise AssertionError("workflow-run identity mismatch")
    if job.get("run_id") != RUN_ID or job.get("head_sha") != HEAD_SHA:
        raise AssertionError("workflow-job identity mismatch")

    steps = job.get("steps")
    steps_executed = "NO" if steps == [] else "NOT_TESTED"
    runner_allocated = "NO" if job.get("runner_id") == 0 and job.get("runner_name") == "" else "NOT_TESTED"

    return {
        "WORKFLOW_JOB": "FAIL" if job.get("status") == "completed" and job.get("conclusion") == "failure" else "NOT_TESTED",
        "RUNNER_ALLOCATED": runner_allocated,
        "CONFIGURED_STEPS_EXECUTED": steps_executed,
        "REPOSITORY_TESTS": "NOT_TESTED",
        "HOSTED_EXECUTION": "BLOCKED_EXTERNAL_PRE_STEP" if runner_allocated == "NO" and steps_executed == "NO" else "NOT_TESTED",
        "PRODUCT_FUNCTIONAL_FAILURE": "NOT_PROVEN",
    }


class GitHubAdapterF2QualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.adapter = GitHubRepositoryAdapter(self.transport)

    def test_exact_two_request_f2_path_reproduces_frozen_classification(self) -> None:
        run_payload = self.adapter.workflow_run(REPOSITORY, RUN_ID)
        jobs_payload = self.adapter.list_workflow_jobs(REPOSITORY, RUN_ID)

        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(
            self.transport.calls,
            [
                ("GET", f"repos/{REPOSITORY}/actions/runs/{RUN_ID}", None),
                ("GET", f"repos/{REPOSITORY}/actions/runs/{RUN_ID}/jobs?filter=latest&per_page=100", None),
            ],
        )

        classification = classify_f2(run_payload, jobs_payload, JOB_ID)
        self.assertEqual(classification["WORKFLOW_JOB"], "FAIL")
        self.assertEqual(classification["RUNNER_ALLOCATED"], "NO")
        self.assertEqual(classification["CONFIGURED_STEPS_EXECUTED"], "NO")
        self.assertEqual(classification["REPOSITORY_TESTS"], "NOT_TESTED")
        self.assertEqual(classification["HOSTED_EXECUTION"], "BLOCKED_EXTERNAL_PRE_STEP")
        self.assertEqual(classification["PRODUCT_FUNCTIONAL_FAILURE"], "NOT_PROVEN")

    def test_job_failure_never_becomes_repository_test_failure_without_step_evidence(self) -> None:
        classification = classify_f2(RUN_PAYLOAD, JOBS_PAYLOAD, JOB_ID)
        self.assertEqual(classification["WORKFLOW_JOB"], "FAIL")
        self.assertEqual(classification["REPOSITORY_TESTS"], "NOT_TESTED")

    def test_wrong_job_identity_fails_instead_of_silently_passing(self) -> None:
        with self.assertRaises(AssertionError):
            classify_f2(RUN_PAYLOAD, JOBS_PAYLOAD, JOB_ID + 1)

    def test_wrong_sha_fails_instead_of_silently_passing(self) -> None:
        wrong = dict(RUN_PAYLOAD)
        wrong["head_sha"] = "0" * 40
        with self.assertRaises(AssertionError):
            classify_f2(wrong, JOBS_PAYLOAD, JOB_ID)

    def test_missing_steps_remains_not_tested(self) -> None:
        jobs_payload = {
            "jobs": [
                {
                    **JOBS_PAYLOAD["jobs"][0],
                    "steps": None,
                }
            ]
        }
        classification = classify_f2(RUN_PAYLOAD, jobs_payload, JOB_ID)
        self.assertEqual(classification["CONFIGURED_STEPS_EXECUTED"], "NOT_TESTED")
        self.assertEqual(classification["REPOSITORY_TESTS"], "NOT_TESTED")

    def test_invalid_input_is_rejected_before_transport(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.workflow_run("", RUN_ID)
        with self.assertRaises(ValueError):
            self.adapter.workflow_run(REPOSITORY, 0)
        with self.assertRaises(ValueError):
            self.adapter.list_workflow_jobs(REPOSITORY, RUN_ID, filter="bad")
        with self.assertRaises(ValueError):
            self.adapter.list_workflow_jobs(REPOSITORY, RUN_ID, per_page=101)
        self.assertEqual(self.transport.calls, [])

    def test_real_urllib_transport_rejects_mutation_before_network(self) -> None:
        transport = UrllibGitHubTransport("qualification-token")
        with self.assertRaises(GitHubAdapterError):
            transport.request("POST", "repos/tihotm/metaO/issues", {"title": "x"})

    def test_real_urllib_transport_rejects_get_body_before_network(self) -> None:
        transport = UrllibGitHubTransport("qualification-token")
        with self.assertRaises(GitHubAdapterError):
            transport.request("GET", f"repos/{REPOSITORY}", {"unexpected": True})

    def test_real_urllib_transport_converts_http_error_and_preserves_cause(self) -> None:
        transport = UrllibGitHubTransport("qualification-token")
        error = HTTPError(
            url=f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{RUN_ID}",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"denied"}'),
        )

        with patch("metao.github_adapter.urlopen", side_effect=error):
            with self.assertRaises(GitHubAdapterError) as caught:
                transport.request("GET", f"repos/{REPOSITORY}/actions/runs/{RUN_ID}")

        self.assertIn("GitHub API 403", str(caught.exception))
        self.assertIn('{"message":"denied"}', str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, HTTPError)


if __name__ == "__main__":
    unittest.main()
