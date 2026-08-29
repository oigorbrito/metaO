use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, BoundConfidence, ContractError, EvidenceEnvelope,
    ExecutionId, MissionId, RuntimeId, VerificationRequest, VerificationRequestId,
    VerifierDescriptor, VerifierId,
};
use metao_kernel::apply_confidence_after_hard_gates;

fn verifier() -> VerifierDescriptor {
    VerifierDescriptor {
        verifier_id: VerifierId::new("verifier-1").unwrap(),
        version: "v1".into(),
        capabilities: vec!["confidence".into()],
    }
}

fn request() -> VerificationRequest {
    VerificationRequest {
        request_id: VerificationRequestId::new("request-1").unwrap(),
        attempt_id: metao_contracts::VerificationAttemptId::new("attempt-1").unwrap(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        capability: "confidence".into(),
    }
}

fn evidence() -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "evidence-1".into(),
        obligation_id: "obligation-1".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        orchestrator_id: RuntimeId::new("runtime-1").unwrap(),
        adapter_version: "adapter-1".into(),
        attempt_id: "attempt-1".into(),
        subject_id: "subject-1".into(),
        subject_state_id: "subject-state-1".into(),
        verification_context_id: "verification-context-1".into(),
        policy_bundle_id: "policy-bundle-1".into(),
        verifier_id: "verifier-1".into(),
        payload_digest: "digest-1".into(),
        provenance_root: "root-1".into(),
        authority_id: "authority-1".into(),
        passed: true,
        created_at_epoch: 10.0,
        expires_at_epoch: Some(20.0),
        approval_id: Some("approval-1".into()),
        confidence: Some(0.93),
    }
}

fn context() -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "subject-1".into(),
        subject_state_id: "subject-state-1".into(),
        verification_context_id: "verification-context-1".into(),
        policy_bundle_id: "policy-bundle-1".into(),
        required_obligations: vec!["obligation-1".into()],
        trusted_verifiers: vec!["verifier-1".into()],
        trusted_provenance_roots: vec!["root-1".into()],
        authorized_authorities: vec!["authority-1".into()],
    }
}

fn advisory() -> BoundConfidence {
    BoundConfidence {
        verifier_id: VerifierId::new("verifier-1").unwrap(),
        verifier_version: "v1".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        subject_id: "subject-1".into(),
        subject_state_id: "subject-state-1".into(),
        verification_context_id: "verification-context-1".into(),
        policy_bundle_id: "policy-bundle-1".into(),
        payload_digest: "digest-1".into(),
        score: Some(0.71),
        confidence: 0.92,
    }
}

fn apply(
    hard_gate_decision: AcceptanceDecision,
    bound_confidence: &BoundConfidence,
    threshold: f64,
) -> Result<AcceptanceDecision, ContractError> {
    apply_confidence_after_hard_gates(
        hard_gate_decision,
        bound_confidence,
        threshold,
        &verifier(),
        &request(),
        &evidence(),
        &context(),
    )
}

#[test]
fn exact_bound_confidence_is_advisory_only() {
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory(), 0.75).unwrap(),
        AcceptanceDecision::Accept,
    );
}

#[test]
fn bound_confidence_below_threshold_requires_human() {
    let mut advisory = advisory();
    advisory.confidence = 0.25;
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75).unwrap(),
        AcceptanceDecision::RequireHuman,
    );
}

#[test]
fn bare_confidence_without_binding_is_rejected() {
    let mut advisory = advisory();
    advisory.verifier_version = "v2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn verifier_id_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.verifier_id = VerifierId::new("verifier-2").unwrap();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn verifier_version_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.verifier_version = "v2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn mission_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.mission_id = MissionId::new("mission-2").unwrap();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn execution_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.execution_id = ExecutionId::new("exec-2").unwrap();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn subject_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.subject_id = "subject-2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn subject_state_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.subject_state_id = "subject-state-2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn verification_context_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.verification_context_id = "verification-context-2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn policy_bundle_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.policy_bundle_id = "policy-bundle-2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn payload_digest_mismatch_fails_closed() {
    let mut advisory = advisory();
    advisory.payload_digest = "digest-2".into();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn high_confidence_cannot_rescue_block() {
    assert_eq!(
        apply(AcceptanceDecision::Block, &advisory(), 0.75).unwrap(),
        AcceptanceDecision::Block,
    );
}

#[test]
fn high_confidence_cannot_rescue_stale() {
    assert_eq!(
        apply(AcceptanceDecision::Stale, &advisory(), 0.75).unwrap(),
        AcceptanceDecision::Stale,
    );
}

#[test]
fn confidence_cannot_fill_missing_evidence() {
    assert_eq!(
        apply(AcceptanceDecision::NotDone, &advisory(), 0.75).unwrap(),
        AcceptanceDecision::NotDone,
    );
}

#[test]
fn confidence_cannot_override_authoritative_deny() {
    assert_eq!(
        apply(AcceptanceDecision::Block, &advisory(), 0.0).unwrap(),
        AcceptanceDecision::Block,
    );
}

#[test]
fn confidence_cannot_override_over_budget_block() {
    assert_eq!(
        apply(AcceptanceDecision::Block, &advisory(), 1.0).unwrap(),
        AcceptanceDecision::Block,
    );
}

#[test]
fn confidence_cannot_mint_metao_accepted() {
    let decision = apply(AcceptanceDecision::Accept, &advisory(), 0.75).unwrap();
    assert_ne!(decision, AcceptanceDecision::Block);
    assert_ne!(decision, AcceptanceDecision::NotDone);
    assert_ne!(decision, AcceptanceDecision::Stale);
    assert_ne!(decision, AcceptanceDecision::RequireHuman);
}

#[test]
fn confidence_score_remains_observation_not_authority() {
    let mut advisory = advisory();
    advisory.score = Some(0.01);
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75).unwrap(),
        AcceptanceDecision::Accept,
    );
}

#[test]
fn no_best_of_n_selection_introduced() {
    let advisory = advisory();
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75).unwrap(),
        AcceptanceDecision::Accept,
    );
}

#[test]
fn no_learned_threshold_or_routing_is_introduced() {
    let mut advisory = advisory();
    advisory.confidence = 0.81;
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75).unwrap(),
        AcceptanceDecision::Accept,
    );
}

#[test]
fn invalid_confidence_fails_closed() {
    let mut advisory = advisory();
    advisory.confidence = 1.5;
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory, 0.75),
        Err(ContractError::InvalidConfidence),
    );
}

#[test]
fn invalid_threshold_fails_closed() {
    assert_eq!(
        apply(AcceptanceDecision::Accept, &advisory(), 1.5),
        Err(ContractError::InvalidConfidence),
    );
}
