use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, MissionId, RuntimeId,
};
use metao_kernel::canonical_acceptance;

fn context() -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "s1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        required_obligations: vec!["verify".into()],
        trusted_verifiers: vec!["verifier-1".into()],
        trusted_provenance_roots: vec!["root-1".into()],
        authorized_authorities: vec!["authority-1".into()],
    }
}

fn evidence() -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "e1".into(),
        obligation_id: "verify".into(),
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

#[test]
fn missing_payload_digest_blocks() {
    let mut item = evidence();
    item.payload_digest.clear();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["missing_provenance"]);
}

#[test]
fn missing_provenance_root_blocks() {
    let mut item = evidence();
    item.provenance_root.clear();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["missing_provenance"]);
}

#[test]
fn empty_trusted_verifiers_allows_nonempty_verifier() {
    let mut ctx = context();
    ctx.trusted_verifiers.clear();
    let result = canonical_acceptance(&ctx, &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn untrusted_verifier_blocks() {
    let mut item = evidence();
    item.verifier_id = "evil".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["untrusted_verifier"]);
}

#[test]
fn trusted_verifier_passes_gate() {
    let result = canonical_acceptance(&context(), &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn empty_trusted_provenance_roots_allows_nonempty_root() {
    let mut ctx = context();
    ctx.trusted_provenance_roots.clear();
    let result = canonical_acceptance(&ctx, &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn untrusted_provenance_root_blocks() {
    let mut item = evidence();
    item.provenance_root = "evil-root".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["untrusted_provenance_root"]);
}

#[test]
fn trusted_provenance_root_passes_gate() {
    let result = canonical_acceptance(&context(), &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn missing_authority_blocks() {
    let mut item = evidence();
    item.authority_id.clear();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["missing_authority"]);
}

#[test]
fn empty_authorized_authorities_allows_nonempty_authority() {
    let mut ctx = context();
    ctx.authorized_authorities.clear();
    let result = canonical_acceptance(&ctx, &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn unauthorized_authority_blocks() {
    let mut item = evidence();
    item.authority_id = "evil-authority".into();
    let result = canonical_acceptance(&context(), &[item], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert_eq!(result.reasons, ["unauthorized_authority"]);
}

#[test]
fn authorized_authority_passes_gate() {
    let result = canonical_acceptance(&context(), &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn fully_trusted_evidence_can_continue_to_acceptance() {
    let result = canonical_acceptance(&context(), &[evidence()], 15.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}
