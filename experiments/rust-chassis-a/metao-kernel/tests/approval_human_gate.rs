use metao_contracts::{AcceptanceDecision, ApprovalRecord};
use metao_kernel::{apply_confidence_after_hard_gates, require_human, resume_after_approval};

fn request() -> metao_contracts::ApprovalRequest {
    require_human("ap-1", "m1", "x1", "s1", "p1", "high risk")
}

fn approved_record() -> ApprovalRecord {
    ApprovalRecord {
        approval_id: "ap-1".into(),
        mission_id: "m1".into(),
        execution_id: "x1".into(),
        subject_state_id: "s1".into(),
        policy_bundle_id: "p1".into(),
        approver_id: "human-1".into(),
        approved: true,
    }
}

fn denied_record() -> ApprovalRecord {
    ApprovalRecord {
        approved: false,
        ..approved_record()
    }
}

#[test]
fn human_request_preserves_bindings() {
    let request = request();
    assert_eq!(request.approval_id, "ap-1");
    assert_eq!(request.mission_id, "m1");
    assert_eq!(request.execution_id, "x1");
    assert_eq!(request.subject_state_id, "s1");
    assert_eq!(request.policy_bundle_id, "p1");
    assert_eq!(request.reason, "high risk");
}

#[test]
fn approved_exact_binding_accepts() {
    assert_eq!(
        resume_after_approval(&request(), &approved_record()),
        AcceptanceDecision::Accept
    );
}

#[test]
fn denied_exact_binding_blocks() {
    assert_eq!(
        resume_after_approval(&request(), &denied_record()),
        AcceptanceDecision::Block
    );
}

#[test]
fn approval_id_mismatch_blocks() {
    let mut record = approved_record();
    record.approval_id = "ap-2".into();
    assert_eq!(
        resume_after_approval(&request(), &record),
        AcceptanceDecision::Block
    );
}

#[test]
fn mission_id_mismatch_blocks() {
    let mut record = approved_record();
    record.mission_id = "m2".into();
    assert_eq!(
        resume_after_approval(&request(), &record),
        AcceptanceDecision::Block
    );
}

#[test]
fn execution_id_mismatch_blocks() {
    let mut record = approved_record();
    record.execution_id = "x2".into();
    assert_eq!(
        resume_after_approval(&request(), &record),
        AcceptanceDecision::Block
    );
}

#[test]
fn subject_state_id_mismatch_blocks() {
    let mut record = approved_record();
    record.subject_state_id = "s2".into();
    assert_eq!(
        resume_after_approval(&request(), &record),
        AcceptanceDecision::Block
    );
}

#[test]
fn policy_bundle_id_mismatch_blocks() {
    let mut record = approved_record();
    record.policy_bundle_id = "p2".into();
    assert_eq!(
        resume_after_approval(&request(), &record),
        AcceptanceDecision::Block
    );
}

#[test]
fn hard_gate_precedence_is_preserved() {
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::Block, 1.0, 0.8).unwrap(),
        AcceptanceDecision::Block
    );
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::NotDone, 1.0, 0.8).unwrap(),
        AcceptanceDecision::NotDone
    );
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::Stale, 1.0, 0.8).unwrap(),
        AcceptanceDecision::Stale
    );
}

#[test]
fn low_confidence_requires_human() {
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.4, 0.8).unwrap(),
        AcceptanceDecision::RequireHuman
    );
}

#[test]
fn threshold_confidence_accepts() {
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.8, 0.8).unwrap(),
        AcceptanceDecision::Accept
    );
}

#[test]
fn high_confidence_accepts() {
    assert_eq!(
        apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.95, 0.8).unwrap(),
        AcceptanceDecision::Accept
    );
}

#[test]
fn invalid_confidence_fails_closed() {
    assert!(apply_confidence_after_hard_gates(AcceptanceDecision::Accept, -0.1, 0.8).is_err());
    assert!(apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 1.1, 0.8).is_err());
}

#[test]
fn invalid_threshold_fails_closed() {
    assert!(apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.5, -0.1).is_err());
    assert!(apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.5, 1.1).is_err());
}
