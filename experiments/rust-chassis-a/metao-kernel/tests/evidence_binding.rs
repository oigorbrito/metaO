use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, MissionId,
    RequiredEvidenceSet, RuntimeId,
};
use metao_kernel::{aggregate_evidence, canonical_acceptance};
use std::collections::BTreeSet;

fn context() -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "s1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        required_obligations: vec!["verify".into(), "audit".into()],
        trusted_verifiers: vec!["verifier-1".into()],
        trusted_provenance_roots: vec!["root-1".into()],
        authorized_authorities: vec!["authority-1".into()],
    }
}

fn evidence(obligation_id: &str, evidence_id: &str) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: evidence_id.into(),
        obligation_id: obligation_id.into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        orchestrator_id: RuntimeId::new("orch-1").unwrap(),
        adapter_version: "1".into(),
        attempt_id: "attempt-1".into(),
        subject_id: "s1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        verifier_id: "verifier-1".into(),
        payload_digest: format!("digest-{evidence_id}"),
        provenance_root: "root-1".into(),
        authority_id: "authority-1".into(),
        passed: true,
        created_at_epoch: 10.0,
        expires_at_epoch: Some(20.0),
        approval_id: None,
        confidence: None,
    }
}

#[test]
fn subject_id_mismatch_blocks() {
    let mut item = evidence("verify", "e1");
    item.subject_id = "other".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["subject_mismatch"]);
}

#[test]
fn subject_state_mismatch_is_stale() {
    let mut item = evidence("verify", "e1");
    item.subject_state_id = "other".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Stale);
    assert_eq!(result.reasons, ["subject_state_mismatch"]);
}

#[test]
fn verification_context_mismatch_blocks() {
    let mut item = evidence("verify", "e1");
    item.verification_context_id = "other".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["verification_context_mismatch"]);
}

#[test]
fn policy_bundle_mismatch_blocks() {
    let mut item = evidence("verify", "e1");
    item.policy_bundle_id = "other".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["policy_bundle_mismatch"]);
}

#[test]
fn duplicate_evidence_id_blocks() {
    let first = evidence("verify", "same-id");
    let mut second = evidence("audit", "same-id");
    second.created_at_epoch = 11.0;
    let result = canonical_acceptance(&context(), &[first, second], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["duplicate_evidence_id"]);
}

#[test]
fn unknown_obligation_blocks() {
    let item = evidence("unexpected", "e1");
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["unknown_obligation"]);
}

#[test]
fn duplicate_or_conflicting_obligation_blocks() {
    let first = evidence("verify", "e1");
    let mut second = evidence("verify", "e2");
    second.payload_digest = "different".into();
    let result = canonical_acceptance(&context(), &[first, second], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(
        result.reasons,
        ["duplicate_or_conflicting_obligation_evidence"]
    );
}

#[test]
fn missing_obligation_is_not_done() {
    let item = evidence("verify", "e1");
    let aggregation = aggregate_evidence(
        &RequiredEvidenceSet {
            obligations: BTreeSet::from(["verify".into(), "audit".into()]),
        },
        &[item],
    );
    assert_eq!(aggregation.decision, AcceptanceDecision::NotDone);
    assert_eq!(aggregation.reasons, ["missing_obligation:audit"]);
}

#[test]
fn failed_obligation_is_not_done() {
    let mut verify = evidence("verify", "e1");
    verify.passed = false;
    let audit = evidence("audit", "e2");
    let aggregation = aggregate_evidence(
        &RequiredEvidenceSet {
            obligations: BTreeSet::from(["verify".into(), "audit".into()]),
        },
        &[verify, audit],
    );
    assert_eq!(aggregation.decision, AcceptanceDecision::NotDone);
    assert_eq!(aggregation.reasons, ["failed_obligation:verify"]);
}

#[test]
fn executor_done_without_evidence_does_not_accept() {
    let result = canonical_acceptance(&context(), &[], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::NotDone);
}

#[test]
fn valid_bound_evidence_can_accept() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("verify", "e1"), evidence("audit", "e2")],
        15.0,
    );
    assert_eq!(result.decision, AcceptanceDecision::Accept);
    assert!(result.reasons.is_empty());
    assert!(result.proof.is_some());
}
