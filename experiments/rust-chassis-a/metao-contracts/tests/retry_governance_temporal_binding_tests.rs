use metao_contracts::execution_governance::{
    project_retry_governance, ExecutionBudget, ExecutionGateDecision, ExecutionPolicyEffect,
    ExecutionRiskDecision, ExecutionUsage, RetryApprovalContext,
};
use metao_contracts::{
    ApprovalAuthorityPort, ApprovalAuthorityTicket, ExecutionId, MissionId,
};

#[derive(Clone)]
struct Port(ApprovalAuthorityTicket);

impl ApprovalAuthorityPort for Port {
    fn current(&self, approval_id: &str) -> Option<ApprovalAuthorityTicket> {
        (self.0.approval_id == approval_id).then(|| self.0.clone())
    }
}

fn mission() -> MissionId {
    MissionId::new("mission-temporal-476").unwrap()
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-temporal-476").unwrap()
}

fn ticket() -> ApprovalAuthorityTicket {
    ApprovalAuthorityTicket {
        approval_id: "approval-temporal-476".into(),
        mission_id: mission(),
        execution_id: execution(),
        subject_state_id: "state-476".into(),
        policy_bundle_id: "policy-476".into(),
        approver_id: "approver-476".into(),
        capability_id: "approve-retry".into(),
        action: "retry_execution".into(),
        target: "execution-temporal-476".into(),
        scope: "ordinary-retry".into(),
        authority_epoch: 5,
        not_before_epoch: Some(100.0),
        expires_at_epoch: Some(200.0),
        revoked: false,
    }
}

#[test]
fn caller_cannot_alter_authoritative_approval_validity_window() {
    let canonical = ticket();
    let port = Port(canonical.clone());
    let mut presented = canonical.clone();
    presented.expires_at_epoch = Some(250.0);

    let result = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &ExecutionBudget {
            money_limit: 10.0,
            token_limit: 1000,
            wall_time_limit_s: 100.0,
            attempt_limit: 5,
            money_used: 0.0,
            tokens_used: 0,
            wall_time_used_s: 0.0,
            attempts_used: 0,
        },
        &ExecutionUsage {
            money: 1.0,
            tokens: 10,
            wall_time_s: 1.0,
            attempts: 1,
        },
        Some(&presented),
        &port,
        &RetryApprovalContext {
            mission_id: mission(),
            execution_id: execution(),
            subject_state_id: "state-476".into(),
            policy_bundle_id: "policy-476".into(),
            action: "retry_execution".into(),
            target: "execution-temporal-476".into(),
            scope: "ordinary-retry".into(),
        },
        150.0,
    );

    assert!(!result.human_approval_satisfied);
    assert_eq!(result.decision, ExecutionGateDecision::RequireHuman);
}
