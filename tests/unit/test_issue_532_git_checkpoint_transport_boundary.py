from __future__ import annotations

import unittest

from metao.git_checkpoint_transport import (
    EndpointGitCheckpointPort,
    GitRepositoryEndpoint,
)
from metao.project_supervision import (
    ProjectObjective,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)


SHA0 = "0" * 40
SHA1 = "1" * 40


class FakeTransport:
    def __init__(self):
        self.heads = {"host": SHA0, "a": SHA1, "c": SHA0}
        self.commits = {
            "host": {SHA0},
            "a": {SHA0, SHA1},
            "c": {SHA0},
        }
        self.transfers: list[tuple[str, str, str]] = []

    def observe_clean_head(self, endpoint):
        return self.heads[endpoint.endpoint_id]

    def require_commit(self, endpoint, commit_id):
        if commit_id not in self.commits[endpoint.endpoint_id]:
            raise ValueError("missing commit")

    def transfer_exact(self, source, destination, commit_id):
        self.require_commit(source, commit_id)
        self.transfers.append((source.endpoint_id, destination.endpoint_id, commit_id))
        self.commits[destination.endpoint_id].add(commit_id)
        self.heads[destination.endpoint_id] = commit_id


class EndpointGitCheckpointPortTests(unittest.TestCase):
    def _port(self):
        transport = FakeTransport()
        port = EndpointGitCheckpointPort(
            initial_endpoint=GitRepositoryEndpoint("host", "host://repo"),
            executor_endpoints={
                "executor-a": GitRepositoryEndpoint("a", "executor://a/repo"),
                "executor-c": GitRepositoryEndpoint("c", "executor://c/repo"),
            },
            repository_id="repo-metao",
            transport=transport,
        )
        return port, transport

    def test_initial_materialization_uses_configured_endpoint_not_executor_metadata(self):
        port, transport = self._port()
        checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))

        materialized = port.materialize(checkpoint, to_executor_id="executor-a")

        self.assertEqual(materialized, checkpoint)
        self.assertEqual(transport.heads["a"], SHA0)
        self.assertEqual(transport.transfers, [("host", "a", SHA0)])

    def test_handoff_requires_source_at_exact_authoritative_checkpoint(self):
        port, transport = self._port()
        checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))
        transport.heads["a"] = SHA1

        with self.assertRaisesRegex(ValueError, "authoritative checkpoint"):
            port.handoff(
                checkpoint,
                from_executor_id="executor-a",
                to_executor_id="executor-c",
            )

        self.assertEqual(transport.transfers, [])

    def test_capture_binds_executor_claim_to_host_observed_endpoint_head(self):
        port, transport = self._port()
        transport.heads["a"] = SHA1
        execution = WorkExecutionResult(
            "wu-1",
            "executor-a",
            "provider-x",
            WorkExecutionStatus.SUCCEEDED,
            SHA1,
            f"git://repo-metao/{SHA1}",
        )

        checkpoint = port.capture(
            ProjectObjective("project-360", "req-360", "deliver"),
            WorkUnit("wu-1", "work"),
            execution,
        )

        self.assertEqual(checkpoint.state_id, SHA1)
        self.assertEqual(checkpoint.artifact_ref, f"git://repo-metao/{SHA1}")

    def test_unknown_executor_endpoint_fails_closed(self):
        port, _ = self._port()
        checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))

        with self.assertRaisesRegex(ValueError, "unknown executor Git endpoint"):
            port.materialize(checkpoint, to_executor_id="executor-unknown")


if __name__ == "__main__":
    unittest.main()
