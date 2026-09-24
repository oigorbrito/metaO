use metao_contracts::failure_causality::{
    FactualExecutionOutcome, FailureCausalityFacts, FailureClass, FailureClassificationBasis,
    RecoveryStatus,
};
use metao_contracts::runtime_health::{
    evaluate_bounded_retry, BoundedRetryEligibility, RuntimeHealthEvidenceBasis,
    RuntimeHealthObservation, RuntimeHealthPolicy, RuntimeHealthState,
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

fn policy() -> RuntimeHealthPolicy {
    RuntimeHealthPolicy {
        quarantine_consecutive_failures: 3,
        unhealthy_failure_percent: 60,
        recovery_successes_required: 2,
        retry_pressure_limit: 2,
    }
}

fn observation(state: RuntimeHealthState) -> RuntimeHealthObservation {
    match state {
        RuntimeHealthState::Healthy => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
            evidence_ref: "health:runtime-a:healthy".to_string(),
            window_start_sequence: 1,
            window_end_sequence: 4,
            attempts: 4,
            successes: 4,
            failures: 0,
            consecutive_failures: 0,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 0,
            prior_state: None,
            self_reported_healthy: None,
        },
        RuntimeHealthState::Degraded => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
            evidence_ref: "health:runtime-a:degraded".to_string(),
            window_start_sequence: 1,
            window_end_sequence: 4,
            attempts: 4,
            successes: 3,
            failures: 1,
            consecutive_failures: 1,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 0,
            prior_state: None,
            self_reported_healthy: None,
        },
        RuntimeHealthState::Unhealthy => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
            evidence_ref: "health:runtime-a:unhealthy".to_string(),
            window_start_sequence: 1,
            window_end_sequence: 4,
            attempts: 4,
            successes: 1,
            failures: 3,
            consecutive_failures: 2,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 0,
            prior_state: None,
            self_reported_healthy: None,
        },
        RuntimeHealthState::Quarantined => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
            evidence_ref: "health:runtime-a:quarantined".to_string(),
            window_start_sequence: 1,
            window_end_sequence: 3,
            attempts: 3,
            successes: 0,
            failures: 3,
            consecutive_failures: 3,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 0,
            prior_state: None,
            self_reported_healthy: None,
        },
        RuntimeHealthState::Recovering => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
            evidence_ref: "health:runtime-a:recovering".to_string(),
            window_start_sequence: 2,
            window_end_sequence: 4,
            attempts: 3,
            successes: 2,
            failures: 1,
            consecutive_failures: 0,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 1,
            prior_state: Some(RuntimeHealthState::Unhealthy),
            self_reported_healthy: None,
        },
        RuntimeHealthState::Unknown => RuntimeHealthObservation {
            runtime_id: "runtime-a".to_string(),
            runtime_version: "1.0.0".to_string(),
            config_id: "config-a".to_string(),
            evidence_basis: RuntimeHealthEvidenceBasis::Unknown,
            evidence_ref: "no-execution-observation".to_string(),
            window_start_sequence: 0,
            window_end_sequence: 0,
            attempts: 0,
            successes: 0,
            failures: 0,
            consecutive_failures: 0,
            timeouts: 0,
            transport_failures: 0,
            active_retries: 0,
            fresh_successes_since_unhealthy: 0,
            prior_state: None,
            self_reported_healthy: None,
        },
    }
}

fn evaluate(state: RuntimeHealthState) -> metao_contracts::runtime_health::BoundedRetryProjection {
    evaluate_bounded_retry(&transient_failure(), &observation(state), &policy())
        .expect("valid health observation")
}

#[test]
fn eligible_causal_retry_with_bounded_healthy_runtime_remains_eligible() {
    let result = evaluate(RuntimeHealthState::Healthy);
    assert_eq!(result.eligibility, BoundedRetryEligibility::Eligible);
    assert_eq!(result.next_attempt, Some(2));
}
#[test]
fn causal_attempt_budget_still_has_precedence() {
    let mut facts = transient_failure();
    facts.current_attempt = facts.max_attempts;
    let result =
        evaluate_bounded_retry(&facts, &observation(RuntimeHealthState::Healthy), &policy())
            .unwrap();
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
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
        let result =
            evaluate_bounded_retry(&facts, &observation(RuntimeHealthState::Healthy), &policy())
                .unwrap();
        assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    }
}
#[test]
fn retry_pressure_limit_blocks_ordinary_retry_without_minting_failure() {
    let mut observed = observation(RuntimeHealthState::Degraded);
    observed.active_retries = 3;
    let result = evaluate_bounded_retry(&transient_failure(), &observed, &policy()).unwrap();
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert!(result.retry_pressure_exceeded);
    assert_eq!(observed.failures, 1);
}
#[test]
fn unhealthy_and_quarantined_runtimes_cannot_be_ordinary_retry_targets() {
    for state in [
        RuntimeHealthState::Unhealthy,
        RuntimeHealthState::Quarantined,
    ] {
        assert_eq!(
            evaluate(state).eligibility,
            BoundedRetryEligibility::Ineligible
        );
    }
}
#[test]
fn recovering_runtime_requires_separate_controlled_recovery_authority() {
    let result = evaluate(RuntimeHealthState::Recovering);
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
    assert!(result.reason.contains("controlled recovery authority"));
}
#[test]
fn unknown_health_cannot_be_used_as_fresh_retry_escape_hatch() {
    let unknown = observation(RuntimeHealthState::Unknown);
    let result = evaluate_bounded_retry(&transient_failure(), &unknown, &policy()).unwrap();
    assert_eq!(result.eligibility, BoundedRetryEligibility::Ineligible);
}
#[test]
fn zero_attempts_cannot_claim_factual_adapter_verified_provenance() {
    let mut forged = observation(RuntimeHealthState::Unknown);
    forged.evidence_basis = RuntimeHealthEvidenceBasis::AdapterVerified;
    forged.evidence_ref = "forged:factual-without-execution".into();
    assert!(evaluate_bounded_retry(&transient_failure(), &forged, &policy()).is_err());
}
#[test]
fn invalid_or_self_reported_health_cannot_enable_retry() {
    for basis in [
        RuntimeHealthEvidenceBasis::SelfReported,
        RuntimeHealthEvidenceBasis::Unknown,
    ] {
        let mut observed = observation(RuntimeHealthState::Healthy);
        observed.evidence_basis = basis;
        assert!(evaluate_bounded_retry(&transient_failure(), &observed, &policy()).is_err());
    }
}
#[test]
fn alternating_recovery_state_does_not_restore_ordinary_retry_eligibility() {
    for state in [
        RuntimeHealthState::Quarantined,
        RuntimeHealthState::Recovering,
        RuntimeHealthState::Recovering,
        RuntimeHealthState::Unhealthy,
        RuntimeHealthState::Recovering,
    ] {
        assert_eq!(
            evaluate(state).eligibility,
            BoundedRetryEligibility::Ineligible
        );
    }
}
#[test]
fn bounded_retry_projection_contains_no_dispatch_or_acceptance_authority() {
    let encoded = serde_json::to_string(&evaluate(RuntimeHealthState::Healthy)).unwrap();
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
