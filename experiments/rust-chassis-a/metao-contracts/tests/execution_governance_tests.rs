use metao_contracts::execution_governance::{
    evaluate_pre_runtime_gate, ExecutionBudget, ExecutionGateDecision, ExecutionPolicyEffect,
    ExecutionRiskDecision, ExecutionUsage,
};

fn budget() -> ExecutionBudget {
    ExecutionBudget {
        money_limit: 10.0,
        token_limit: 1_000,
        wall_time_limit_s: 100.0,
        attempt_limit: 3,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    }
}

fn request() -> ExecutionUsage {
    ExecutionUsage {
        money: 1.0,
        tokens: 100,
        wall_time_s: 10.0,
        attempts: 1,
    }
}

#[test]
fn policy_deny_cannot_be_overridden_by_human_approval() {
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &budget(),
        &request(),
        true,
    );
    assert_eq!(result.decision, ExecutionGateDecision::Block);
}

#[test]
fn risk_stop_cannot_be_overridden_by_human_approval() {
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Stop,
        &budget(),
        &request(),
        true,
    );
    assert_eq!(result.decision, ExecutionGateDecision::Block);
}

#[test]
fn exhausted_execution_budget_cannot_be_overridden_by_approval() {
    let mut value = budget();
    value.attempts_used = value.attempt_limit;
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &value,
        &request(),
        true,
    );
    assert_eq!(result.decision, ExecutionGateDecision::Block);
}

#[test]
fn explicit_zero_budget_blocks_before_runtime() {
    let mut value = budget();
    value.token_limit = 0;
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &value,
        &request(),
        false,
    );
    assert_eq!(result.decision, ExecutionGateDecision::Block);
}

#[test]
fn require_human_needs_approval_but_approval_does_not_create_other_authority() {
    let without = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &request(),
        false,
    );
    assert_eq!(without.decision, ExecutionGateDecision::RequireHuman);

    let with = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &request(),
        true,
    );
    assert_eq!(with.decision, ExecutionGateDecision::Proceed);
}

#[test]
fn requested_usage_over_limit_blocks_before_runtime() {
    let mut requested = request();
    requested.tokens = 1_001;
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &requested,
        false,
    );
    assert_eq!(result.decision, ExecutionGateDecision::Block);
}

#[test]
fn observed_runtime_overage_is_preserved_as_fact() {
    let observed = ExecutionUsage {
        money: 12.0,
        tokens: 1_500,
        wall_time_s: 120.0,
        attempts: 1,
    };
    let projection = budget().observe_usage(&observed);
    assert!(projection.over_limit);
    assert_eq!(projection.money_observed, 12.0);
    assert_eq!(projection.tokens_observed, 1_500);
    assert_eq!(projection.wall_time_observed_s, 120.0);
}

#[test]
fn execution_budget_is_serially_distinct_from_acceptance_budget() {
    let encoded = serde_json::to_string(&budget()).expect("serialize");
    assert!(encoded.contains("attempt_limit"));
    assert!(!encoded.contains("verifier_attempt_limit"));
    assert!(!encoded.contains("AcceptanceBudget"));
}

#[test]
fn gate_result_has_no acceptance_or_runtime_sdk_authority() {
    let result = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &request(),
        false,
    );
    let encoded = serde_json::to_string(&result).expect("serialize");
    for forbidden in ["AcceptanceDecision", "provider_sdk", "Orchestrator"] {
        assert!(!encoded.contains(forbidden));
    }
}
