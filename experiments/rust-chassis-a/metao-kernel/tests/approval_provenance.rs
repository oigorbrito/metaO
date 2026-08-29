use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, ApprovalAuthorityPort, ApprovalAuthorityTicket,
    EvidenceEnvelope, ExecutionId, MissionId, ProvenanceVerificationObservation,
    ProvenanceVerificationPort, ProvenanceVerificationStatus, RuntimeId, VerifierId,
};
use metao_kernel::{
    canonical_acceptance, resolve_approval_authority, resolve_approval_provenance_terminal_sources,
    verify_provenance, TerminalSourceDecision,
};

#[derive(Clone)]
struct StaticApprovalPort {
    current: Option<ApprovalAuthorityTicket>,
}

impl ApprovalAuthorityPort for StaticApprovalPort {
    fn current(&self, approval_id: &str) -> Option<ApprovalAuthorityTicket> {
        self.current
            .clone()
            .filter(|ticket| ticket.approval_id == approval_id)
    }
}

#[derive(Clone)]
struct StaticProvenancePort {
    observation: Option<ProvenanceVerificationObservation>,
}

impl ProvenanceVerificationPort for StaticProvenancePort {
    fn verify(&self, _evidence: &EvidenceEnvelope) -> Option<ProvenanceVerificationObservation> {
        self.observation.clone()
    }
}

fn approval_ticket() -> ApprovalAuthorityTicket {
    ApprovalAuthorityTicket {
        approval_id: "approval-1".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        subject_state_id: "state-1".into(),
        policy_bundle_id: "policy-1".into(),
        approver_id: "approver-1".into(),
        capability_id: "cap-1".into(),
        action: "approve".into(),
        target: "target-1".into(),
        scope: "scope-1".into(),
        authority_epoch: 10,
        not_before_epoch: Some(10.0),
        expires_at_epoch: Some(20.0),
        revoked: false,
    }
}

fn approval_port(ticket: Option<ApprovalAuthorityTicket>) -> StaticApprovalPort {
    StaticApprovalPort { current: ticket }
}

fn evidence() -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "evidence-1".into(),
        obligation_id: "verify".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        orchestrator_id: RuntimeId::new("orch-1").unwrap(),
        adapter_version: "1".into(),
        attempt_id: "attempt-1".into(),
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        verifier_id: "verifier-1".into(),
        payload_digest: "digest-1".into(),
        provenance_root: "root-1".into(),
        authority_id: "authority-1".into(),
        passed: true,
        created_at_epoch: 10.0,
        expires_at_epoch: Some(20.0),
        approval_id: None,
        confidence: None,
    }
}

fn provenance_observation(
    status: ProvenanceVerificationStatus,
) -> ProvenanceVerificationObservation {
    ProvenanceVerificationObservation {
        status,
        evidence_id: "evidence-1".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        payload_digest: "digest-1".into(),
        provenance_root: "root-1".into(),
        verifier_id: VerifierId::new("verifier-1").unwrap(),
        issuer_id: "authority-1".into(),
        observed_at_epoch: 15.0,
        expires_at_epoch: Some(20.0),
        reason: String::new(),
    }
}

fn provenance_port(observation: Option<ProvenanceVerificationObservation>) -> StaticProvenancePort {
    StaticProvenancePort { observation }
}

fn context() -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        required_obligations: vec!["verify".into()],
        trusted_verifiers: vec!["verifier-1".into()],
        trusted_provenance_roots: vec!["root-1".into()],
        authorized_authorities: vec!["authority-1".into()],
    }
}

#[test]
fn current_authorized_approval_continues() {
    let result = resolve_approval_authority(
        &approval_ticket(),
        &approval_port(Some(approval_ticket())),
        15.0,
    );
    assert_eq!(result.decision, TerminalSourceDecision::Continue);
    assert!(result.reasons.is_empty());
}

#[test]
fn approval_record_without_current_authority_blocks() {
    let result = resolve_approval_authority(&approval_ticket(), &approval_port(None), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["missing_approval_source"]);
}

#[test]
fn revoked_authority_blocks() {
    let mut current = approval_ticket();
    current.revoked = true;
    let result =
        resolve_approval_authority(&approval_ticket(), &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_revoked"]);
}

#[test]
fn stale_authority_epoch_fails_closed() {
    let mut current = approval_ticket();
    current.authority_epoch = 11;
    let mut candidate = approval_ticket();
    candidate.authority_epoch = 10;
    let result = resolve_approval_authority(&candidate, &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Stale);
    assert_eq!(result.reasons, ["approval_authority_epoch_stale"]);
}

#[test]
fn capability_mismatch_blocks() {
    let mut current = approval_ticket();
    current.capability_id = "cap-2".into();
    let result =
        resolve_approval_authority(&approval_ticket(), &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_binding_mismatch"]);
}

#[test]
fn action_mismatch_blocks() {
    let mut current = approval_ticket();
    current.action = "reject".into();
    let result =
        resolve_approval_authority(&approval_ticket(), &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_binding_mismatch"]);
}

#[test]
fn target_mismatch_blocks() {
    let mut current = approval_ticket();
    current.target = "target-2".into();
    let result =
        resolve_approval_authority(&approval_ticket(), &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_binding_mismatch"]);
}

#[test]
fn scope_mismatch_blocks() {
    let mut current = approval_ticket();
    current.scope = "scope-2".into();
    let result =
        resolve_approval_authority(&approval_ticket(), &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_binding_mismatch"]);
}

#[test]
fn approval_before_not_before_blocks() {
    let mut candidate = approval_ticket();
    candidate.not_before_epoch = Some(16.0);
    let result =
        resolve_approval_authority(&candidate, &approval_port(Some(candidate.clone())), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_not_yet_valid"]);
}

#[test]
fn expired_approval_blocks() {
    let mut candidate = approval_ticket();
    candidate.expires_at_epoch = Some(14.0);
    let result =
        resolve_approval_authority(&candidate, &approval_port(Some(candidate.clone())), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_expired"]);
}

#[test]
fn caller_approval_claim_cannot_override_authority_source() {
    let mut current = approval_ticket();
    current.capability_id = "cap-authoritative".into();
    let mut candidate = approval_ticket();
    candidate.capability_id = "cap-caller".into();
    let result = resolve_approval_authority(&candidate, &approval_port(Some(current)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["approval_binding_mismatch"]);
}

#[test]
fn caller_provenance_claim_alone_is_not_verified() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Unverified);
    obs.reason = "unverified_provenance".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["unverified_provenance"]);
}

#[test]
fn valid_provider_neutral_attestation_continues() {
    let result = verify_provenance(
        &evidence(),
        &provenance_port(Some(provenance_observation(
            ProvenanceVerificationStatus::Verified,
        ))),
        15.0,
    );
    assert_eq!(result.decision, TerminalSourceDecision::Continue);
    assert!(result.reasons.is_empty());
}

#[test]
fn missing_attestation_source_fails_closed() {
    let result = verify_provenance(&evidence(), &provenance_port(None), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["missing_provenance_source"]);
}

#[test]
fn invalid_attestation_binding_blocks() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Verified);
    obs.subject_state_id = "state-2".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_binding_mismatch"]);
}

#[test]
fn invalid_issuer_verifier_identity_blocks() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Verified);
    obs.verifier_id = VerifierId::new("verifier-evil").unwrap();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_binding_mismatch"]);
}

#[test]
fn stale_legitimate_provenance_produces_stale() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Stale);
    obs.reason = "provenance_stale".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Stale);
    assert_eq!(result.reasons, ["provenance_stale"]);
}

#[test]
fn expired_hostile_provenance_fails_closed() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Verified);
    obs.expires_at_epoch = Some(14.0);
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_expired"]);
}

#[test]
fn local_matching_digest_alone_does_not_yield_authenticity() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Unverified);
    obs.reason = "local_hash_is_not_authenticity".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["local_hash_is_not_authenticity"]);
}

#[test]
fn fabricated_provenance_root_blocks() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Verified);
    obs.provenance_root = "fabricated-root".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_binding_mismatch"]);
}

#[test]
fn rollback_provenance_state_blocks() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Invalid);
    obs.reason = "provenance_rollback".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_rollback"]);
}

#[test]
fn runtime_self_report_cannot_mint_provenance() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Unverified);
    obs.verifier_id = VerifierId::new("runtime-self-report").unwrap();
    obs.reason = "runtime_self_report".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_binding_mismatch"]);
}

#[test]
fn verifier_self_report_cannot_mint_provenance() {
    let mut obs = provenance_observation(ProvenanceVerificationStatus::Unverified);
    obs.issuer_id = "verifier-self-report".into();
    obs.reason = "verifier_self_report".into();
    let result = verify_provenance(&evidence(), &provenance_port(Some(obs)), 15.0);
    assert_eq!(result.decision, TerminalSourceDecision::Block);
    assert_eq!(result.reasons, ["provenance_binding_mismatch"]);
}

#[test]
fn approval_and_provenance_path_cannot_mint_metao_accepted() {
    let approval = approval_ticket();
    let approval_gate = resolve_approval_provenance_terminal_sources(
        &approval,
        &approval_port(Some(approval.clone())),
        &evidence(),
        &provenance_port(Some(provenance_observation(
            ProvenanceVerificationStatus::Verified,
        ))),
        15.0,
    );
    assert_eq!(approval_gate.decision, TerminalSourceDecision::Continue);
    let result = canonical_acceptance(&context(), &[], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::NotDone);
}

#[test]
fn canonical_acceptance_remains_final_authority() {
    let result = canonical_acceptance(&context(), &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}
