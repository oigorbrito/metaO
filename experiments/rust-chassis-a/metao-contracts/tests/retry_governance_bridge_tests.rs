use metao_contracts::execution_governance::{
    bind_retry_governance, project_retry_governance, ExecutionBudget, ExecutionGateDecision,
    ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionUsage, RetryApprovalContext,
    RetryGovernanceBridgeError,
};
use metao_contracts::failure_causality::{
    bind_execution_retry_authority, evaluate_retry_eligibility, ExecutionRetryAttemptClaim,
    ExecutionRetryAuthorityState, FactualExecutionOutcome, FailureCausalityFacts, FailureClass,
    FailureClassificationBasis, RecoveryStatus, RetryEligibility,
};
use metao_contracts::{ApprovalAuthorityPort, ApprovalAuthorityTicket, ExecutionId, MissionId};

#[derive(Clone)]
struct ApprovalPort {
    ticket: Option<ApprovalAuthorityTicket>,
}

impl ApprovalAuthorityPort for ApprovalPort {
    fn current(&self, approval_id: &str) -> Option<ApprovalAuthorityTicket> {
        self.ticket
            .as_ref()
            .filter(|ticket| ticket.approval_id == approval_id)
            .cloned()
    }
}

fn mission() -> MissionId {
    MissionId::new("mission-476").unwrap()
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-476").unwrap()
}

fn budget() -> ExecutionBudget {
    ExecutionBudget {
        money_limit: 10.0,
        token_limit: 1_000,
        wall_time_limit_s: 100.0,
        attempt_limit: 5,
        money_used: 1.0,
        tokens_used: 100,
        wall_time_used_s: 10.0,
        attempts_used: 1,
    }
}

fn requested_retry_usage() -> ExecutionUsage {
    ExecutionUsage {
        money: 1.0,
        tokens: 100,
        wall_time_s: 10.0,
        attempts: 1,
    }
}

fn facts() -> FailureCausalityFacts {
    FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("evidence://failure/retry-476".into()),
        recovery_required: false,
        recovery_status: RecoveryStatus::NotRequired,
        current_attempt: 2,
        max_attempts: 4,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

fn retry_authority() -> ExecutionRetryAuthorityState {
    ExecutionRetryAuthorityState {
        mission_id: mission(),
        execution_id: execution(),
        retry_lineage_id: "retry-lineage-476".into(),
        current_attempt: 2,
        max_attempts: 4,
        state_version: 8,
        evidence_ref: "event-ledger://execution-retry/476/8".into(),
    }
}

fn retry_claim() -> ExecutionRetryAttemptClaim {
    ExecutionRetryAttemptClaim {
        mission_id: mission(),
        execution_id: execution(),
        retry_lineage_id: "retry-lineage-476".into(),
        current_attempt: 2,
        max_attempts: 4,
    }
}

fn approval_context() -> RetryApprovalContext {
    RetryApprovalContext {
        mission_id: mission(),
        execution_id: execution(),
        subject_state_id: "subject-state-476".into(),
        policy_bundle_id: "policy-476".into(),
        action: "retry_execution".into(),
        target: "execution-476".into(),
        scope: "ordinary-retry".into(),
    }
}

fn approval() -> ApprovalAuthorityTicket {
    ApprovalAuthorityTicket {
        approval_id: "approval-476".into(),
        mission_id: mission(),
        execution_id: execution(),
        subject_state_id: "subject-state-476".into(),
        policy_bundle_id: "policy-476".into(),
        approver_id: "human-authority-1".into(),
        capability_id: "approve-retry".into(),
        action: "retry_execution".into(),
        target: "execution-476".into(),
        scope: "ordinary-retry".into(),
        authority_epoch: 9,
        not_before_epoch: Some(100.0),
        expires_at_epoch: Some(200.0),
        revoked: false,
    }
}

fn no_approval_port() -> ApprovalPort {
    ApprovalPort { ticket: None }
}

#[test]
fn canonical_policy_deny_blocks_retry_despite_favorable_caller_boolean() {
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert!(governance.policy_denied);
    let bound = bind_retry_governance(&facts(), &governance).unwrap();
    assert!(bound.policy_blocked);
    assert_eq!(
        evaluate_retry_eligibility(&bound).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn canonical_risk_stop_blocks_retry_despite_favorable_caller_boolean() {
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Stop,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert!(governance.risk_stopped);
    let bound = bind_retry_governance(&facts(), &governance).unwrap();
    assert!(bound.risk_blocked);
}

#[test]
fn exhausted_execution_budget_blocks_retry_despite_favorable_caller_boolean() {
    let mut exhausted = budget();
    exhausted.attempts_used = exhausted.attempt_limit;
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &exhausted,
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert!(governance.budget_blocked);
    let bound = bind_retry_governance(&facts(), &governance).unwrap();
    assert!(bound.budget_blocked);
}

#[test]
fn valid_allow_risk_and_capacity_preserve_retry_eligibility_without_dispatch_authority() {
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert_eq!(governance.decision, ExecutionGateDecision::Proceed);
    let bound = bind_retry_governance(&facts(), &governance).unwrap();
    assert_eq!(
        evaluate_retry_eligibility(&bound).eligibility,
        RetryEligibility::Eligible
    );
    let serialized = serde_json::to_string(&governance).unwrap();
    assert!(!serialized.contains("dispatch"));
    assert!(!serialized.contains("Acceptance"));
}

#[test]
fn require_human_without_canonical_approval_remains_pending() {
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert_eq!(governance.decision, ExecutionGateDecision::RequireHuman);
    assert_eq!(
        bind_retry_governance(&facts(), &governance),
        Err(RetryGovernanceBridgeError::HumanApprovalRequired)
    );
}

#[test]
fn canonical_exact_approval_satisfies_require_human() {
    let ticket = approval();
    let port = ApprovalPort {
        ticket: Some(ticket.clone()),
    };
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        Some(&ticket),
        &port,
        &approval_context(),
        150.0,
    );
    assert!(governance.human_approval_required);
    assert!(governance.human_approval_satisfied);
    assert_eq!(governance.decision, ExecutionGateDecision::Proceed);
}

#[test]
fn approval_for_other_action_or_execution_cannot_authorize_retry() {
    let canonical = approval();
    let port = ApprovalPort {
        ticket: Some(canonical.clone()),
    };
    let mut forged = canonical.clone();
    forged.action = "recovery_probe".into();
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        Some(&forged),
        &port,
        &approval_context(),
        150.0,
    );
    assert!(!governance.human_approval_satisfied);
    assert_eq!(governance.decision, ExecutionGateDecision::RequireHuman);

    let mut forged_execution = canonical;
    forged_execution.execution_id = ExecutionId::new("other-execution").unwrap();
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        Some(&forged_execution),
        &port,
        &approval_context(),
        150.0,
    );
    assert!(!governance.human_approval_satisfied);
}

#[test]
fn expired_or_revoked_approval_cannot_authorize_retry() {
    let mut canonical = approval();
    canonical.revoked = true;
    let port = ApprovalPort {
        ticket: Some(canonical.clone()),
    };
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        Some(&canonical),
        &port,
        &approval_context(),
        150.0,
    );
    assert!(!governance.human_approval_satisfied);

    let expired = approval();
    let port = ApprovalPort {
        ticket: Some(expired.clone()),
    };
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &requested_retry_usage(),
        Some(&expired),
        &port,
        &approval_context(),
        201.0,
    );
    assert!(!governance.human_approval_satisfied);
}

#[test]
fn bridge_retains_typed_causes_without_parsing_gate_reason() {
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Stop,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    let value = serde_json::to_value(governance).unwrap();
    assert_eq!(value["policy_denied"], true);
    assert_eq!(value["risk_stopped"], true);
    assert!(value.get("reason").is_none());
}

#[test]
fn caller_true_blockers_remain_conservative_but_do_not_become_canonical_provenance() {
    let mut caller = facts();
    caller.policy_blocked = true;
    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    assert!(!governance.policy_denied);
    let bound = bind_retry_governance(&caller, &governance).unwrap();
    assert!(bound.policy_blocked);
}

#[test]
fn retry_lineage_ordinal_and_execution_budget_attempt_capacity_remain_distinct() {
    let retry_bound = bind_execution_retry_authority(&facts(), &retry_claim(), &retry_authority())
        .expect("#475 retry authority must bind first");
    assert_eq!(retry_bound.current_attempt, 2);
    assert_eq!(budget().attempts_used, 1);

    let governance = project_retry_governance(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &requested_retry_usage(),
        None,
        &no_approval_port(),
        &approval_context(),
        150.0,
    );
    let composed = bind_retry_governance(&retry_bound, &governance).unwrap();
    assert_eq!(composed.current_attempt, 2);
    assert_eq!(composed.max_attempts, 4);
    assert_eq!(
        evaluate_retry_eligibility(&composed).eligibility,
        RetryEligibility::Eligible
    );
}
