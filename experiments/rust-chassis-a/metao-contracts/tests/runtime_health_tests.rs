use metao_contracts::runtime_health::{
    derive_runtime_health, RuntimeHealthError, RuntimeHealthEvidenceBasis,
    RuntimeHealthObservation, RuntimeHealthPolicy, RuntimeHealthState,
};

fn policy() -> RuntimeHealthPolicy {
    RuntimeHealthPolicy {
        quarantine_consecutive_failures: 3,
        unhealthy_failure_percent: 60,
        recovery_successes_required: 2,
        retry_pressure_limit: 2,
    }
}

fn observation() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: "runtime-health:runtime-a:window-1".to_string(),
        window_start_sequence: 1,
        window_end_sequence: 10,
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
    }
}

#[test]
fn self_reported_or_unknown_observation_cannot_mint_health_state() {
    for basis in [
        RuntimeHealthEvidenceBasis::SelfReported,
        RuntimeHealthEvidenceBasis::Unknown,
    ] {
        let mut value = observation();
        value.evidence_basis = basis;
        assert_eq!(
            derive_runtime_health(&value, &policy()),
            Err(RuntimeHealthError::InvalidEvidenceBasis)
        );
    }
}

#[test]
fn observation_requires_nonblank_evidence_reference() {
    for evidence in ["", "   "] {
        let mut value = observation();
        value.evidence_ref = evidence.to_string();
        assert_eq!(
            derive_runtime_health(&value, &policy()),
            Err(RuntimeHealthError::BlankEvidenceRef)
        );
    }
}

#[test]
fn independent_observation_can_support_health_projection() {
    let mut value = observation();
    value.evidence_basis = RuntimeHealthEvidenceBasis::IndependentObservation;
    assert_eq!(
        derive_runtime_health(&value, &policy())
            .expect("projection")
            .state,
        RuntimeHealthState::Healthy
    );
}

#[test]
fn empty_window_is_unknown_not_healthy() {
    let mut value = observation();
    value.attempts = 0;
    value.evidence_basis = RuntimeHealthEvidenceBasis::Unknown;
    value.successes = 0;
    value.window_start_sequence = 11;
    value.window_end_sequence = 11;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Unknown);
}

#[test]
fn one_transient_failure_below_threshold_is_degraded_not_quarantined() {
    let mut value = observation();
    value.attempts = 4;
    value.successes = 3;
    value.failures = 1;
    value.consecutive_failures = 1;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Degraded);
}

#[test]
fn repeated_failures_cross_quarantine_threshold_deterministically() {
    let mut value = observation();
    value.attempts = 5;
    value.successes = 2;
    value.failures = 3;
    value.consecutive_failures = 3;
    let left = derive_runtime_health(&value, &policy()).expect("first projection");
    let right = derive_runtime_health(&value, &policy()).expect("second projection");
    assert_eq!(left, right);
    assert_eq!(left.state, RuntimeHealthState::Quarantined);
}

#[test]
fn exact_failure_ratio_threshold_does_not_depend_on_integer_truncation() {
    let mut value = observation();
    value.attempts = 3;
    value.successes = 1;
    value.failures = 2;
    value.consecutive_failures = 2;

    let mut threshold_67 = policy();
    threshold_67.unhealthy_failure_percent = 67;
    let below = derive_runtime_health(&value, &threshold_67).expect("projection");
    assert_eq!(below.state, RuntimeHealthState::Degraded);

    let mut threshold_66 = policy();
    threshold_66.unhealthy_failure_percent = 66;
    let reached = derive_runtime_health(&value, &threshold_66).expect("projection");
    assert_eq!(reached.state, RuntimeHealthState::Unhealthy);
}

#[test]
fn timeout_and_transport_failures_are_factual_failures() {
    let mut value = observation();
    value.attempts = 5;
    value.successes = 3;
    value.failures = 2;
    value.consecutive_failures = 1;
    value.timeouts = 1;
    value.transport_failures = 1;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.failures, 2);
    assert_eq!(result.timeouts, 1);
    assert_eq!(result.transport_failures, 1);
    assert_eq!(result.state, RuntimeHealthState::Degraded);
}

#[test]
fn lying_self_report_does_not_override_factual_state() {
    let mut value = observation();
    value.attempts = 4;
    value.successes = 1;
    value.failures = 3;
    value.consecutive_failures = 3;
    value.self_reported_healthy = Some(true);
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Quarantined);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason.contains("did not override")));
}

#[test]
fn prior_quarantine_requires_fresh_successes_before_healthy() {
    let mut value = observation();
    value.attempts = 1;
    value.successes = 1;
    value.prior_state = Some(RuntimeHealthState::Quarantined);
    value.fresh_successes_since_unhealthy = 1;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Recovering);
}

#[test]
fn recovering_state_cannot_flap_to_healthy_without_threshold() {
    let mut value = observation();
    value.attempts = 1;
    value.successes = 1;
    value.prior_state = Some(RuntimeHealthState::Recovering);
    value.fresh_successes_since_unhealthy = 1;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Recovering);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason.contains("fresh successes 1/2")));
}

#[test]
fn enough_fresh_successes_allow_controlled_recovery() {
    let mut value = observation();
    value.attempts = 2;
    value.successes = 2;
    value.prior_state = Some(RuntimeHealthState::Unhealthy);
    value.fresh_successes_since_unhealthy = 2;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert_eq!(result.state, RuntimeHealthState::Healthy);
    assert_eq!(result.failures, 0);
}

#[test]
fn retry_pressure_alone_degrades_but_never_quarantines() {
    let mut value = observation();
    value.active_retries = 100;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert!(result.retry_pressure_exceeded);
    assert_eq!(result.failures, 0);
    assert_eq!(result.consecutive_failures, 0);
    assert_eq!(result.state, RuntimeHealthState::Degraded);
}

#[test]
fn different_runtime_histories_produce_distinct_projections() {
    let healthy = observation();
    let mut degraded = observation();
    degraded.runtime_id = "runtime-b".to_string();
    degraded.runtime_version = "2.0.0".to_string();
    degraded.config_id = "config-b".to_string();
    degraded.evidence_ref = "runtime-health:runtime-b:window-1".to_string();
    degraded.attempts = 5;
    degraded.successes = 4;
    degraded.failures = 1;
    degraded.consecutive_failures = 1;

    let left = derive_runtime_health(&healthy, &policy()).expect("healthy projection");
    let right = derive_runtime_health(&degraded, &policy()).expect("degraded projection");
    assert_ne!(left.runtime_id, right.runtime_id);
    assert_eq!(left.state, RuntimeHealthState::Healthy);
    assert_eq!(right.state, RuntimeHealthState::Degraded);
}

#[test]
fn retry_pressure_is_projected_without_dispatch_authority() {
    let mut value = observation();
    value.active_retries = 3;
    let result = derive_runtime_health(&value, &policy()).expect("projection");
    assert!(result.retry_pressure_exceeded);
    assert_eq!(result.state, RuntimeHealthState::Degraded);
}

#[test]
fn invalid_counter_relationships_fail_closed() {
    let mut value = observation();
    value.attempts = 2;
    value.successes = 2;
    value.failures = 1;
    assert_eq!(
        derive_runtime_health(&value, &policy()),
        Err(RuntimeHealthError::InvalidCounters)
    );
}

#[test]
fn counter_overflow_cannot_saturate_into_valid_attempt_total() {
    let mut value = observation();
    value.attempts = u32::MAX;
    value.successes = u32::MAX;
    value.failures = 1;
    value.consecutive_failures = 1;
    assert_eq!(
        derive_runtime_health(&value, &policy()),
        Err(RuntimeHealthError::InvalidCounters)
    );
}

#[test]
fn invalid_policy_fails_closed() {
    let mut invalid = policy();
    invalid.quarantine_consecutive_failures = 0;
    assert_eq!(
        derive_runtime_health(&observation(), &invalid),
        Err(RuntimeHealthError::InvalidPolicy)
    );
}

#[test]
fn serialization_contains_no_acceptance_or_runtime_sdk_authority() {
    let result = derive_runtime_health(&observation(), &policy()).expect("projection");
    let encoded = serde_json::to_string(&result).expect("serialize projection");
    let decoded: metao_contracts::runtime_health::RuntimeHealthProjection =
        serde_json::from_str(&encoded).expect("deserialize projection");
    assert_eq!(decoded, result);
    for forbidden in [
        "AcceptanceDecision",
        "SPEC_READY",
        "PLAN_READY",
        "MVP_ACCEPTED",
        "dispatch",
        "failover",
        "provider_sdk",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
