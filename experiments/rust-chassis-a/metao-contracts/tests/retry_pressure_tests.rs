use metao_contracts::failure_causality::{
    FactualExecutionOutcome, FailureCausalityFacts, FailureClass, FailureClassificationBasis,
    RecoveryStatus,
};
use metao_contracts::runtime_health::{
    evaluate_bounded_retry, BoundedRetryEligibility, RuntimeHealthProjection, RuntimeHealthState,
};

fn transient_failure() -> FailureCausalityFacts {
    FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AdapterNormalization,
        failure_class_evidence_ref: Some("adapter-error:transient".to_string()),
        recovery_required: false,
        recovery_status: RecoveryStatus::NotRequired,
        current_attempt: 1,
        max_attempts: 3,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

fn health(state: RuntimeHealthState) -> RuntimeHealthProjection {
    RuntimeHealthProjection {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        state,
        attempts: 4,
        successes: 3,
        failures: 1,
        consecutive_failures: 1,
        timeouts: 0,
        transport_failures: 0,
        active_retries: 0,
        retry_pressure_exceeded: false,
        self_reported_healthy: None,
        reasons: vec![],
    }
}

#[test]
fn eligible_causal_retry_with_bounded_healthy_runtime_remains_eligible() {
    let result = evaluate_bounded_retry(&transient_failure(), &health(RuntimeHealthState::Healthy));
    assert_eq!(result.eligibility, BoundedRetryEligibility::Eligible);
    assert_eq!(result.next_attempt, Some(2));
}

#[test]
fn causal_attempt_budget_still_has_precedence() {
    let mut facts = transient_failure();
    facts.current_attempt = facts.max_attempts;
    let result = evaluate_bounded_retry(&facts, &health(RuntimeHealthState::Healthy));
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert_eq!(result.next_attempt, None);
    assert!(result.reason.contains("causality gate blocked"));
}

#[test]
fn policy_risk_and_budget_blocks_still_dominate_health() {
    for index in 0..3 {
        let mut facts = transient_failure();
        match index {
            0 => facts.policy_blocked = true,
            1 => facts.risk_blocked = true,
            _ => facts.budget_blocked = true,
        }
        let result = evaluate_bounded_retry(&facts, &health(RuntimeHealthState::Healthy));
        assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    }
}

#[test]
fn retry_pressure_limit_blocks_ordinary_retry_without_minting_failure() {
    let mut projection = health(RuntimeHealthState::Degraded);
    projection.active_retries = 3;
    projection.retry_pressure_exceeded = true;

    let result = evaluate_bounded_retry(&transient_failure(), &projection);
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert!(result.retry_pressure_exceeded);
    assert_eq!(projection.failures, 1);
    assert!(result.reason.contains("pressure limit"));
}

#[test]
fn unhealthy_and_quarantined_runtimes_cannot_be_ordinary_retry_targets() {
    for state in [RuntimeHealthState::Unhealthy, RuntimeHealthState::Quarantined] {
        let result = evaluate_bounded_retry(&transient_failure(), &health(state));
        assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
        assert_eq!(result.next_attempt, None);
    }
}

#[test]
fn recovering_runtime_requires_separate_controlled_recovery_authority() {
    let result = evaluate_bounded_retry(
        &transient_failure(),
        &health(RuntimeHealthState::Recovering),
    );
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert!(result.reason.contains("controlled recovery authority"));
}

#[test]
fn unknown_health_cannot_be_used_as_fresh_retry_escape_hatch() {
    let result = evaluate_bounded_retry(&transient_failure(), &health(RuntimeHealthState::Unknown));
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert!(result.reason.contains("fresh healthy retry target"));
}

#[test]
fn alternating_recovery_state_does_not_restore_ordinary_retry_eligibility() {
    let sequence = [
        RuntimeHealthState::Quarantined,
        RuntimeHealthState::Recovering,
        RuntimeHealthState::Recovering,
        RuntimeHealthState::Unhealthy,
        RuntimeHealthState::Recovering,
    ];

    for state in sequence {
        let result = evaluate_bounded_retry(&transient_failure(), &health(state));
        assert_eq!(
            result.eligibility,
            BoundedRetryEligibility::Ineligible,
            "state {state:?} unexpectedly became an ordinary retry target"
        );
    }
}

#[test]
fn bounded_retry_projection_contains_no_dispatch_or_acceptance_authority() {
    let encoded = serde_json::to_string(&evaluate_bounded_retry(
        &transient_failure(),
        &health(RuntimeHealthState::Healthy),
    ))
    .expect("serialize bounded retry projection");

    for forbidden in [
        "retry_executed",
        "dispatch",
        "failover_executed",
        "AcceptanceDecision",
        "provider_sdk",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
