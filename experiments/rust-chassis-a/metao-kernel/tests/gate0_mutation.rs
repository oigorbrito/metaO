use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus,
    MissionId, PolicyEffect, RuntimeId,
};
use metao_kernel::evaluate_acceptance;

fn request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: ExecutionId::new("exec-1").unwrap(),
        mission_id: MissionId::new("mission-1").unwrap(),
    }
}

fn result() -> ExecutionResult {
    ExecutionResult {
        execution_id: ExecutionId::new("exec-1").unwrap(),
        runtime_id: RuntimeId::new("runtime-1").unwrap(),
        status: ExecutionStatus::Succeeded,
    }
}

#[test]
fn unverified_evidence_with_exact_binding_is_blocked() {
    let evidence = Evidence {
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("exec-1").unwrap(),
        runtime_id: RuntimeId::new("runtime-1").unwrap(),
        policy_version: "policy-1".into(),
        verified: false,
        created_at_epoch: 10,
        expires_at_epoch: 20,
    };

    assert_eq!(
        evaluate_acceptance(
            &request(),
            &result(),
            Some(&evidence),
            PolicyEffect::Allow,
            15,
        ),
        AcceptanceDecision::Block,
    );
}
