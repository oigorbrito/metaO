from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import unittest

import metao
from metao.acceptance import EvidenceEnvelope as AcceptanceEvidenceEnvelope
from metao.adapters.crewai import normalize_evidence as normalize_crewai
from metao.adapters.langgraph import normalize_evidence as normalize_langgraph
from metao.adapters.openai_agents import normalize_evidence as normalize_openai_agents
from metao.core import (
    EvidenceEnvelope as CoreEvidenceEnvelope,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Mission,
)
from metao.evidence import EvidenceEnvelope as CanonicalEvidenceEnvelope
from metao.sqlite_store import (
    MissionStoreCorrupt,
    _SCHEMA_VERSION,
    _decode_core_evidence,
    _encode_core_evidence,
)


class Roadmap8WorkUnit01CanonicalEvidenceEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = ExecutionRequest(
            "exec-1",
            Mission("mission-1", "prove canonical evidence", frozenset({"workflow"})),
            context={
                "obligation_id": "result",
                "subject_id": "subject-1",
                "subject_state_id": "state-1",
                "verification_context_id": "verify-1",
                "policy_bundle_id": "policy-1",
                "verifier_id": "verifier-1",
                "authority_id": "authority-1",
                "created_at_epoch": 10.0,
            },
        )

    def _canonical_item(self) -> CanonicalEvidenceEnvelope:
        return CanonicalEvidenceEnvelope(
            evidence_id="e1",
            obligation_id="result",
            mission_id="mission-1",
            execution_id="exec-1",
            orchestrator_id="orch-1",
            adapter_id="adapter-1",
            adapter_version="1",
            attempt_id="attempt-1",
            subject_id="subject-1",
            subject_state_id="state-1",
            verification_context_id="verify-1",
            policy_bundle_id="policy-1",
            verifier_id="verifier-1",
            payload_digest="digest-1",
            provenance_root="root-1",
            authority_id="authority-1",
            passed=True,
            created_at_epoch=10.0,
            expires_at_epoch=20.0,
            approval_id="approval-1",
            confidence=0.9,
            verification_cost_units=3,
        )

    def test_public_core_and_acceptance_exports_are_same_class(self):
        self.assertIs(metao.EvidenceEnvelope, CanonicalEvidenceEnvelope)
        self.assertIs(CoreEvidenceEnvelope, CanonicalEvidenceEnvelope)
        self.assertIs(AcceptanceEvidenceEnvelope, CanonicalEvidenceEnvelope)

    def test_legacy_read_aliases_are_deterministic(self):
        item = self._canonical_item()
        self.assertEqual(item.adapter_id, "adapter-1")
        self.assertEqual(item.obligation_ids, frozenset({"result"}))
        self.assertEqual(item.evidence_payload_digest, "digest-1")
        self.assertEqual(item.provenance, "root-1")
        self.assertEqual(item.approval_evidence, "approval-1")

    def test_canonical_boundary_rejects_empty_required_bindings(self):
        item = self._canonical_item()
        for field in (
            "evidence_id",
            "obligation_id",
            "mission_id",
            "execution_id",
            "orchestrator_id",
            "adapter_version",
            "attempt_id",
            "subject_id",
            "subject_state_id",
            "verification_context_id",
            "policy_bundle_id",
            "verifier_id",
            "payload_digest",
            "provenance_root",
            "authority_id",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "empty required binding"
            ):
                replace(item, **{field: ""})

    def test_adapter_id_fallback_remains_nonempty_and_deterministic(self):
        item = replace(self._canonical_item(), adapter_id="")
        self.assertEqual(item.adapter_id, item.orchestrator_id)

    def test_confidence_and_opaque_cost_validation_survive_consolidation(self):
        item = self._canonical_item()
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence), self.assertRaisesRegex(
                ValueError, "confidence must be within"
            ):
                replace(item, confidence=confidence)
        with self.assertRaisesRegex(ValueError, "verification_cost_units"):
            replace(item, verification_cost_units=-1)

    def test_all_current_normalizers_return_canonical_envelope(self):
        normalizers = (
            ("langgraph", normalize_langgraph),
            ("crewai", normalize_crewai),
            ("openai-agents", normalize_openai_agents),
        )
        for orchestrator_id, normalizer in normalizers:
            with self.subTest(orchestrator_id=orchestrator_id):
                item = normalizer(
                    request=self.request,
                    orchestrator_id=orchestrator_id,
                    adapter_version="1",
                    output={"answer": "ok"},
                )
                self.assertIsInstance(item, CanonicalEvidenceEnvelope)
                self.assertEqual(item.adapter_id, orchestrator_id)

    def test_execution_result_uses_canonical_evidence_values(self):
        item = normalize_langgraph(
            request=self.request,
            orchestrator_id="langgraph",
            adapter_version="1",
            output={"answer": "ok"},
        )
        result = ExecutionResult(
            "exec-1",
            "langgraph",
            ExecutionStatus.SUCCEEDED,
            evidence=(item,),
        )
        self.assertIs(result.evidence[0], item)
        self.assertIsInstance(result.evidence[0], CanonicalEvidenceEnvelope)

    def test_sqlite_evidence_round_trip_preserves_all_acceptance_bindings(self):
        item = self._canonical_item()
        encoded = _encode_core_evidence(item)
        decoded = _decode_core_evidence(encoded)
        self.assertEqual(_SCHEMA_VERSION, 4)
        self.assertEqual(decoded, item)
        self.assertEqual(encoded["evidence_id"], "e1")
        self.assertEqual(encoded["authority_id"], "authority-1")
        self.assertIs(encoded["passed"], True)
        self.assertEqual(encoded["payload_digest"], "digest-1")
        self.assertEqual(encoded["provenance_root"], "root-1")

    def test_legacy_persisted_evidence_fails_closed_instead_of_fabricating_authority(self):
        legacy = {
            "mission_id": "mission-1",
            "execution_id": "exec-1",
            "orchestrator_id": "orch-1",
            "adapter_id": "adapter-1",
            "adapter_version": "1",
            "attempt_id": "attempt-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verify-1",
            "policy_bundle_id": "policy-1",
            "obligation_ids": ["result"],
            "evidence_payload_digest": "digest-1",
            "provenance": "root-1",
            "verifier_id": "verifier-1",
        }
        with self.assertRaisesRegex(
            MissionStoreCorrupt,
            "legacy evidence envelope cannot be safely upgraded",
        ):
            _decode_core_evidence(legacy)

    def test_canonical_boundary_has_no_orchestrator_sdk_imports(self):
        root = Path(__file__).parents[2] / "src" / "metao"
        forbidden = {"langgraph", "crewai", "openai", "autogen"}
        offenders: list[tuple[str, str]] = []
        for relative in ("evidence.py", "core.py", "acceptance.py"):
            path = root / relative
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    if name.split(".")[0] in forbidden:
                        offenders.append((relative, name))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
