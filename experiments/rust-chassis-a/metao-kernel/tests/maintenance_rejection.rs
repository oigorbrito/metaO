use metao_contracts::{Evidence, ExecutionId, MissionId, RejectionReason, RuntimeId};
use metao_kernel::classify_rejection;

#[test]
fn invalid_evidence_maps_to_explicit_rejection_reason() {
    let evidence = Evidence {
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        runtime_id: RuntimeId::new("alpha").unwrap(),
        policy_version: "policy-v1".into(),
        verified: false,
        created_at_epoch: 10,
        expires_at_epoch: 20,
    };

    assert_eq!(
        classify_rejection(Some(&evidence)),
        Some(RejectionReason::InvalidEvidence)
    );
    assert_eq!(classify_rejection(None), None);
}
