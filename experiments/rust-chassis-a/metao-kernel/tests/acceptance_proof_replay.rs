use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, MissionId, RuntimeId,
};
use metao_kernel::canonical_acceptance;
use metao_kernel::replay_acceptance_decision;

fn context() -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "subject-l5".into(),
        subject_state_id: "state-l5".into(),
        verification_context_id: "verify-l5".into(),
        policy_bundle_id: "policy-l5".into(),
        required_obligations: vec!["a".into(), "b".into()],
        trusted_verifiers: vec!["verifier-l5".into()],
        trusted_provenance_roots: vec!["root-l5".into()],
        authorized_authorities: vec!["authority-l5".into()],
    }
}

fn evidence(obligation: &str, evidence_id: &str, created_at: f64) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: evidence_id.into(),
        obligation_id: obligation.into(),
        mission_id: MissionId::new("mission-l5").unwrap(),
        execution_id: ExecutionId::new("exec-l5").unwrap(),
        orchestrator_id: RuntimeId::new("runtime-l5").unwrap(),
        adapter_version: "1".into(),
        attempt_id: "attempt-l5".into(),
        subject_id: "subject-l5".into(),
        subject_state_id: "state-l5".into(),
        verification_context_id: "verify-l5".into(),
        policy_bundle_id: "policy-l5".into(),
        verifier_id: "verifier-l5".into(),
        payload_digest: format!("digest-{evidence_id}"),
        provenance_root: "root-l5".into(),
        authority_id: "authority-l5".into(),
        passed: true,
        created_at_epoch: created_at,
        expires_at_epoch: Some(100.0),
        approval_id: None,
        confidence: None,
    }
}

#[test]
fn valid_proof_replays_decision() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let proof = result.proof.as_ref().expect("proof present");
    assert_eq!(
        replay_acceptance_decision(proof).unwrap(),
        AcceptanceDecision::Accept
    );
}

#[test]
fn repeated_replay_is_deterministic() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let proof = result.proof.as_ref().expect("proof present");
    assert_eq!(
        replay_acceptance_decision(proof).unwrap(),
        AcceptanceDecision::Accept
    );
    assert_eq!(
        replay_acceptance_decision(proof).unwrap(),
        AcceptanceDecision::Accept
    );
}

#[test]
fn tampered_evidence_ids_fail() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let mut proof = result.proof.as_ref().expect("proof present").clone();
    proof.evidence_ids = vec!["forged".into()];
    assert_eq!(
        replay_acceptance_decision(&proof),
        Err(metao_contracts::ContractError::AcceptanceProofDigestMismatch)
    );
}

#[test]
fn tampered_decision_fail() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let mut proof = result.proof.as_ref().expect("proof present").clone();
    proof.decision = AcceptanceDecision::Block;
    assert!(replay_acceptance_decision(&proof).is_err());
}

#[test]
fn tampered_reasons_fail() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let mut proof = result.proof.as_ref().expect("proof present").clone();
    proof.reasons = vec!["forged".into()];
    assert!(replay_acceptance_decision(&proof).is_err());
}

#[test]
fn tampered_digest_fail() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let mut proof = result.proof.as_ref().expect("proof present").clone();
    proof.digest = "deadbeef".repeat(8);
    assert!(matches!(
        replay_acceptance_decision(&proof),
        Err(metao_contracts::ContractError::AcceptanceProofDigestMismatch)
    ));
}

#[test]
fn evidence_order_does_not_change_valid_proof() {
    let chronological = canonical_acceptance(
        &context(),
        &[evidence("b", "e-b", 10.0), evidence("a", "e-a", 20.0)],
        30.0,
    );
    let out_of_order = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    assert_eq!(chronological.decision, AcceptanceDecision::Accept);
    assert_eq!(out_of_order.decision, AcceptanceDecision::Accept);
    assert_eq!(chronological.proof, out_of_order.proof);
}

#[test]
fn rust_python_digest_matches() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let proof = result.proof.as_ref().expect("proof present");
    assert_eq!(
        proof.digest,
        "2b5141224ba355cfae3298bc7d1faaf0f4b685c693ec4119e9ef42c626bdabd2"
    );
}

#[test]
fn proof_contains_sorted_evidence_ids() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("b", "e-b", 10.0), evidence("a", "e-a", 20.0)],
        30.0,
    );
    let proof = result.proof.expect("proof present");
    assert_eq!(
        proof.evidence_ids,
        vec!["e-a".to_string(), "e-b".to_string()]
    );
}

#[test]
fn proof_replay_does_not_create_new_acceptance_authority() {
    let result = canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    );
    let proof = result.proof.as_ref().expect("proof present");
    assert_eq!(replay_acceptance_decision(proof).unwrap(), proof.decision);
    assert_eq!(replay_acceptance_decision(proof).unwrap(), proof.decision);
}
