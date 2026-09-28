use std::collections::BTreeSet;

use metao_contracts::{
    AcceptanceBudget, AcceptanceContext, AcceptanceDecision, AcceptanceResult,
    AuthoritativeAuthorityDecision, AuthoritativePolicyBundle, AuthoritativeSubjectState,
    ContractError, EvidenceEnvelope, ExecutionId, MissionId, PolicyDecision, PolicyEffect,
    RetryHistoryKind, RetryHistoryRecord, RuntimeId, TerminalDecisionProof, TerminalObservation,
    TerminalObservationEntry, TerminalObservationKind, TerminalValidationProfile,
    VerificationAttemptId, VerificationAttemptStarted, VerificationRequestId, VerificationUsage,
    VerifierId, VerifierResult,
};
use metao_kernel::{
    build_terminal_decision_proof, canonical_acceptance, replay_terminal_decision_proof,
};

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

fn accepted_result() -> AcceptanceResult {
    canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("b", "e-b", 10.0)],
        30.0,
    )
}

fn duplicate_evidence_result() -> AcceptanceResult {
    canonical_acceptance(
        &context(),
        &[evidence("a", "e-a", 20.0), evidence("a", "e-a", 10.0)],
        30.0,
    )
}

fn unknown_obligation_result() -> AcceptanceResult {
    canonical_acceptance(&context(), &[evidence("x", "e-x", 20.0)], 30.0)
}

fn validation_profile_all() -> TerminalValidationProfile {
    use std::iter::FromIterator;
    TerminalValidationProfile {
        required_kinds: BTreeSet::from_iter([
            TerminalObservationKind::SubjectState,
            TerminalObservationKind::AuthorityResolution,
            TerminalObservationKind::PolicyBundle,
            TerminalObservationKind::RetryHistory,
            TerminalObservationKind::VerificationUsage,
            TerminalObservationKind::Approval,
            TerminalObservationKind::Provenance,
            TerminalObservationKind::Confidence,
            TerminalObservationKind::VerifierResult,
        ]),
    }
}

fn terminal_observations() -> Vec<TerminalObservationEntry> {
    let mission_id = MissionId::new("mission-l5").unwrap();
    let execution_id = ExecutionId::new("exec-l5").unwrap();
    let verifier_id = VerifierId::new("verifier-l5").unwrap();

    vec![
        TerminalObservationEntry {
            observation_id: "obs-subject".into(),
            sequence: 0,
            observation: TerminalObservation::SubjectState(AuthoritativeSubjectState {
                subject_id: "subject-l5".into(),
                subject_state_id: "state-l5".into(),
                state_epoch: 10,
            }),
        },
        TerminalObservationEntry {
            observation_id: "obs-authority".into(),
            sequence: 1,
            observation: TerminalObservation::AuthorityResolution(AuthoritativeAuthorityDecision {
                authority_context_id: "authority-context-l5".into(),
                authority_id: "authority-l5".into(),
                authority_epoch: 11,
                capability_id: Some("cap-l5".into()),
                reason: "authority-ok".into(),
                evidence_root: "evidence-root-l5".into(),
            }),
        },
        TerminalObservationEntry {
            observation_id: "obs-policy".into(),
            sequence: 2,
            observation: TerminalObservation::PolicyBundle(AuthoritativePolicyBundle {
                policy_bundle_id: "policy-l5".into(),
                policy_bundle_root: "policy-root-l5".into(),
                bundle_epoch: 12,
                decision: PolicyDecision {
                    effect: PolicyEffect::Allow,
                    policy_bundle_id: "policy-l5".into(),
                    reason: "policy-ok".into(),
                },
            }),
        },
        TerminalObservationEntry {
            observation_id: "obs-retry".into(),
            sequence: 3,
            observation: TerminalObservation::RetryHistory(vec![RetryHistoryRecord {
                record_id: "retry-record-l5".into(),
                mission_id: mission_id.clone(),
                execution_id: execution_id.clone(),
                attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                sequence: 0,
                kind: RetryHistoryKind::AttemptStarted,
                attempt_started: Some(VerificationAttemptStarted {
                    request_id: VerificationRequestId::new("request-l5").unwrap(),
                    attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                    mission_id: mission_id.clone(),
                    execution_id: execution_id.clone(),
                    verifier_id: verifier_id.clone(),
                    verifier_version: "1.0".into(),
                    started_at_epoch: 13.0,
                }),
                recovery_from_attempt_id: None,
                recovery_outcome: None,
                usage: Some(VerificationUsage {
                    attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                    money: Some(1.5),
                    tokens: Some(2),
                    wall_time_s: Some(3.0),
                    verifier_attempts: Some(1),
                }),
            }]),
        },
        TerminalObservationEntry {
            observation_id: "obs-usage".into(),
            sequence: 4,
            observation: TerminalObservation::VerificationUsage {
                usage: VerificationUsage {
                    attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                    money: Some(1.5),
                    tokens: Some(2),
                    wall_time_s: Some(3.0),
                    verifier_attempts: Some(1),
                },
                budget: AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
            },
        },
        TerminalObservationEntry {
            observation_id: "obs-approval".into(),
            sequence: 5,
            observation: TerminalObservation::Approval(metao_contracts::ApprovalAuthorityTicket {
                approval_id: "approval-l5".into(),
                mission_id: mission_id.clone(),
                execution_id: execution_id.clone(),
                subject_state_id: "state-l5".into(),
                policy_bundle_id: "policy-l5".into(),
                approver_id: "approver-l5".into(),
                capability_id: "cap-l5".into(),
                action: "approve".into(),
                target: "target-l5".into(),
                scope: "scope-l5".into(),
                authority_epoch: 14,
                not_before_epoch: Some(0.0),
                expires_at_epoch: Some(100.0),
                revoked: false,
            }),
        },
        TerminalObservationEntry {
            observation_id: "obs-provenance".into(),
            sequence: 6,
            observation: TerminalObservation::Provenance(
                metao_contracts::ProvenanceVerificationObservation {
                    status: metao_contracts::ProvenanceVerificationStatus::Verified,
                    evidence_id: "evidence-l5".into(),
                    mission_id: mission_id.clone(),
                    execution_id: execution_id.clone(),
                    subject_id: "subject-l5".into(),
                    subject_state_id: "state-l5".into(),
                    verification_context_id: "verify-l5".into(),
                    policy_bundle_id: "policy-l5".into(),
                    payload_digest: "payload-l5".into(),
                    provenance_root: "root-l5".into(),
                    verifier_id: verifier_id.clone(),
                    issuer_id: "authority-l5".into(),
                    observed_at_epoch: 15.0,
                    expires_at_epoch: Some(100.0),
                    reason: "verified".into(),
                },
            ),
        },
        TerminalObservationEntry {
            observation_id: "obs-confidence".into(),
            sequence: 7,
            observation: TerminalObservation::Confidence(metao_contracts::BoundConfidence {
                verifier_id: verifier_id.clone(),
                verifier_version: "1.0".into(),
                mission_id: mission_id.clone(),
                execution_id: execution_id.clone(),
                subject_id: "subject-l5".into(),
                subject_state_id: "state-l5".into(),
                verification_context_id: "verify-l5".into(),
                policy_bundle_id: "policy-l5".into(),
                payload_digest: "payload-l5".into(),
                score: Some(0.95),
                confidence: 0.95,
            }),
        },
        TerminalObservationEntry {
            observation_id: "obs-verifier-result".into(),
            sequence: 8,
            observation: TerminalObservation::VerifierResult(VerifierResult {
                request_id: VerificationRequestId::new("request-l5").unwrap(),
                attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                verifier_id: verifier_id.clone(),
                verifier_version: "1.0".into(),
                passed: true,
                reason: "verified".into(),
                score: Some(0.95),
                confidence: Some(0.95),
                usage: VerificationUsage {
                    attempt_id: VerificationAttemptId::new("attempt-l5").unwrap(),
                    money: Some(1.5),
                    tokens: Some(2),
                    wall_time_s: Some(3.0),
                    verifier_attempts: Some(1),
                },
            }),
        },
    ]
}

fn renumber_observations(observations: &mut [TerminalObservationEntry]) {
    for (sequence, entry) in observations.iter_mut().enumerate() {
        entry.sequence = sequence as u64;
    }
}

fn terminal_proof(
    result: &AcceptanceResult,
    observations: Vec<TerminalObservationEntry>,
) -> TerminalDecisionProof {
    build_terminal_decision_proof(
        result,
        &MissionId::new("mission-l5").unwrap(),
        &ExecutionId::new("exec-l5").unwrap(),
        validation_profile_all(),
        observations,
    )
    .unwrap()
}

fn proof_result_accept() -> TerminalDecisionProof {
    terminal_proof(&accepted_result(), terminal_observations())
}

#[test]
fn deterministic_proof_generation() {
    let left = proof_result_accept();
    let right = proof_result_accept();
    assert_eq!(left, right);
    assert_eq!(left.digest, right.digest);
}

#[test]
fn identical_input_same_digest() {
    let left = proof_result_accept();
    let right = proof_result_accept();
    assert_eq!(left.digest, right.digest);
}

#[test]
fn changed_decision_changes_digest() {
    let accept = terminal_proof(&accepted_result(), terminal_observations());
    let block = terminal_proof(&duplicate_evidence_result(), terminal_observations());
    assert_ne!(accept.digest, block.digest);
}

#[test]
fn changed_reasons_changes_digest() {
    let duplicate = terminal_proof(&duplicate_evidence_result(), terminal_observations());
    let unknown = terminal_proof(&unknown_obligation_result(), terminal_observations());
    assert_ne!(duplicate.digest, unknown.digest);
}

#[test]
fn subject_omission_detected() {
    let mut observations = terminal_observations();
    observations.retain(|entry| entry.observation.kind() != TerminalObservationKind::SubjectState);
    renumber_observations(&mut observations);
    let err = build_terminal_decision_proof(
        &accepted_result(),
        &MissionId::new("mission-l5").unwrap(),
        &ExecutionId::new("exec-l5").unwrap(),
        validation_profile_all(),
        observations,
    )
    .unwrap_err();
    assert!(matches!(
        err,
        ContractError::TerminalProofMissingObservation("subject_state")
    ));
}

#[test]
fn subject_mutation_detected() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::SubjectState(subject_state) = &mut proof.observations[0].observation
    {
        subject_state.subject_state_id = "state-forged".into();
    }
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn authority_omission_detected() {
    let mut observations = terminal_observations();
    observations
        .retain(|entry| entry.observation.kind() != TerminalObservationKind::AuthorityResolution);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation(
            "authority_resolution"
        ))
    ));
}

#[test]
fn authority_mutation_detected() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::AuthorityResolution(authority) =
        &mut proof.observations[1].observation
    {
        authority.authority_id = "authority-forged".into();
    }
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn policy_omission_detected() {
    let mut observations = terminal_observations();
    observations.retain(|entry| entry.observation.kind() != TerminalObservationKind::PolicyBundle);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation(
            "policy_bundle"
        ))
    ));
}

#[test]
fn policy_mutation_detected() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::PolicyBundle(policy) = &mut proof.observations[2].observation {
        policy.policy_bundle_root = "policy-root-forged".into();
    }
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn retry_fact_omission_detected() {
    let mut observations = terminal_observations();
    observations.retain(|entry| entry.observation.kind() != TerminalObservationKind::RetryHistory);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation(
            "retry_history"
        ))
    ));
}

#[test]
fn accounting_fact_omission_detected() {
    let mut observations = terminal_observations();
    observations
        .retain(|entry| entry.observation.kind() != TerminalObservationKind::VerificationUsage);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation(
            "verification_usage"
        ))
    ));
}

#[test]
fn approval_omission_detected() {
    let mut observations = terminal_observations();
    observations.retain(|entry| entry.observation.kind() != TerminalObservationKind::Approval);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation("approval"))
    ));
}

#[test]
fn provenance_omission_detected() {
    let mut observations = terminal_observations();
    observations.retain(|entry| entry.observation.kind() != TerminalObservationKind::Provenance);
    renumber_observations(&mut observations);
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofMissingObservation("provenance"))
    ));
}

#[test]
fn verifier_binding_drift_detected() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::VerifierResult(result) = &mut proof.observations[8].observation {
        result.verifier_version = "forged".into();
    }
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn mission_execution_drift_detected() {
    let mut proof = proof_result_accept();
    proof.mission_id = MissionId::new("mission-forged").unwrap();
    assert!(replay_terminal_decision_proof(&proof).is_err());
}

#[test]
fn payload_digest_drift_detected() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::Provenance(observation) = &mut proof.observations[6].observation {
        observation.payload_digest = "payload-forged".into();
    }
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn order_drift_detected() {
    let mut proof = proof_result_accept();
    proof.observations[1].sequence = 99;
    assert!(replay_terminal_decision_proof(&proof).is_err());
}

#[test]
fn duplicate_observation_detected() {
    let mut observations = terminal_observations();
    let duplicate = observations[0].clone();
    observations.push(TerminalObservationEntry {
        observation_id: duplicate.observation_id,
        sequence: 9,
        observation: duplicate.observation,
    });
    assert!(matches!(
        build_terminal_decision_proof(
            &accepted_result(),
            &MissionId::new("mission-l5").unwrap(),
            &ExecutionId::new("exec-l5").unwrap(),
            validation_profile_all(),
            observations,
        ),
        Err(ContractError::TerminalProofDuplicateObservation(_))
    ));
}

#[test]
fn proof_digest_mismatch_detected() {
    let mut proof = proof_result_accept();
    proof.digest = "deadbeef".repeat(8);
    assert!(matches!(
        replay_terminal_decision_proof(&proof),
        Err(ContractError::TerminalProofDigestMismatch)
    ));
}

#[test]
fn replay_deterministic() {
    let proof = proof_result_accept();
    assert_eq!(
        replay_terminal_decision_proof(&proof).unwrap(),
        replay_terminal_decision_proof(&proof).unwrap()
    );
}

#[test]
fn local_root_alone_does_not_prove_hostile_authenticity() {
    let mut proof = proof_result_accept();
    if let TerminalObservation::Provenance(observation) = &mut proof.observations[6].observation {
        observation.provenance_root = "known-local-root".into();
    }
    assert!(replay_terminal_decision_proof(&proof).is_err());
}

#[test]
fn runtime_self_report_cannot_mint_proof_authority() {
    let result = duplicate_evidence_result();
    let mut proof = terminal_proof(&result, terminal_observations());
    if let TerminalObservation::VerifierResult(verifier_result) =
        &mut proof.observations[8].observation
    {
        verifier_result.passed = true;
    }
    assert_eq!(
        replay_terminal_decision_proof(&proof).unwrap(),
        AcceptanceDecision::Block
    );
}

#[test]
fn verifier_pass_cannot_mint_proof_authority() {
    let result = duplicate_evidence_result();
    let mut proof = terminal_proof(&result, terminal_observations());
    if let TerminalObservation::VerifierResult(verifier_result) =
        &mut proof.observations[8].observation
    {
        verifier_result.passed = true;
        verifier_result.reason = "verified".into();
    }
    assert_eq!(
        replay_terminal_decision_proof(&proof).unwrap(),
        AcceptanceDecision::Block
    );
}

#[test]
fn canonical_acceptance_remains_final_authority() {
    let result = duplicate_evidence_result();
    let proof = terminal_proof(&result, terminal_observations());
    assert_eq!(
        replay_terminal_decision_proof(&proof).unwrap(),
        result.decision
    );
}
