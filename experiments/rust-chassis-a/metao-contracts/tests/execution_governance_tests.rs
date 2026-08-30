use metao_contracts::execution_governance::{
    evaluate_pre_runtime_gate, ExecutionBudget, ExecutionGateDecision, ExecutionGovernanceError,
    ExecutionObservedUsage, ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionUsage,
    ExecutionUsageEvidenceBasis,
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

fn observed(usage: ExecutionUsage) -> ExecutionObservedUsage {
    ExecutionObservedUsage {
        usage,
        evidence_basis: ExecutionUsageEvidenceBasis::AdapterVerified,
        evidence_ref: "execution-usage:exec-a:1".to_string(),
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
fn non_finite_or_negative_budget_values_fail_closed() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -1.0] {
        let mut value = budget();
        value.money_limit = invalid;
        assert_eq!(value.validate(), Err(ExecutionGovernanceError::InvalidBudget));
        assert_eq!(
            evaluate_pre_runtime_gate(
                ExecutionPolicyEffect::Allow,
                ExecutionRiskDecision::Allow,
                &value,
                &request(),
                true,
            )
            .decision,
            ExecutionGateDecision::Block
        );
    }
}

#[test]
fn non_finite_or_negative_requested_usage_blocks() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -1.0] {
        let mut requested = request();
        requested.money = invalid;
        assert_eq!(requested.validate(), Err(ExecutionGovernanceError::InvalidUsage));
        assert_eq!(
            evaluate_pre_runtime_gate(
                ExecutionPolicyEffect::Allow,
                ExecutionRiskDecision::Allow,
                &budget(),
                &requested,
                false,
            )
            .decision,
            ExecutionGateDecision::Block
        );
    }
}

#[test]
fn integer_overflow_cannot_be_hidden_by_saturating_accounting() {
    let value = ExecutionBudget {
        token_limit: u64::MAX,
        tokens_used: u64::MAX,
        attempt_limit: u64::MAX,
        attempts_used: u64::MAX,
        ..budget()
    };
    let requested = ExecutionUsage {
        money: 0.0,
        tokens: 1,
        wall_time_s: 0.0,
        attempts: 1,
    };
    assert!(!value.has_pre_runtime_capacity(&requested));
}

#[test]
fn observed_runtime_overage_is_preserved_as_verified_fact() {
    let usage = ExecutionUsage {
        money: 12.0,
        tokens: 1_500,
        wall_time_s: 120.0,
        attempts: 1,
    };
    let projection = budget()
        .observe_usage(&observed(usage))
        .expect("finite observed overage remains factual");
    assert!(projection.over_limit);
    assert_eq!(projection.money_observed, 12.0);
    assert_eq!(projection.tokens_observed, 1_500);
    assert_eq!(projection.wall_time_observed_s, 120.0);
}

#[test]
fn caller_declared_or_unknown_observed_usage_is_not_authoritative() {
    for basis in [
        ExecutionUsageEvidenceBasis::SelfReported,
        ExecutionUsageEvidenceBasis::Unknown,
    ] {
        let mut value = observed(request());
        value.evidence_basis = basis;
        assert_eq!(
            budget().observe_usage(&value),
            Err(ExecutionGovernanceError::InvalidEvidenceBasis)
        );
    }
}

#[test]
fn observed_usage_requires_nonblank_evidence_reference() {
    let mut value = observed(request());
    value.evidence_ref = "   ".to_string();
    assert_eq!(
        budget().observe_usage(&value),
        Err(ExecutionGovernanceError::BlankEvidenceRef)
    );
}

#[test]
fn independent_observation_can_support_post_runtime_usage() {
    let mut value = observed(request());
    value.evidence_basis = ExecutionUsageEvidenceBasis::IndependentObservation;
    assert!(!budget().observe_usage(&value).expect("observation").over_limit);
}

#[test]
fn invalid_observed_usage_is_error_not_false_non_overage() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -1.0] {
        let usage = ExecutionUsage {
            money: invalid,
            tokens: 0,
            wall_time_s: 0.0,
            attempts: 0,
        };
        assert_eq!(
            budget().observe_usage(&observed(usage)),
            Err(ExecutionGovernanceError::InvalidUsage)
        );
    }
}

#[test]
fn observed_integer_overflow_is_error() {
    let value = ExecutionBudget {
        token_limit: u64::MAX,
        tokens_used: u64::MAX,
        ..budget()
    };
    let usage = ExecutionUsage {
        money: 0.0,
        tokens: 1,
        wall_time_s: 0.0,
        attempts: 0,
    };
    assert_eq!(
        value.observe_usage(&observed(usage)),
        Err(ExecutionGovernanceError::InvalidUsage)
    );
}

#[test]
fn execution_budget_is_serially_distinct_from_acceptance_budget() {
    let encoded = serde_json::to_string(&budget()).expect("serialize");
    assert!(encoded.contains("attempt_limit"));
    assert!(!encoded.contains("verifier_attempt_limit"));
    assert!(!encoded.contains("AcceptanceBudget"));
}

#[test]
fn gate_result_has_no_acceptance_or_runtime_sdk_authority() {
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
