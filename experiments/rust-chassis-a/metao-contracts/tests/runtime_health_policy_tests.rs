use metao_contracts::runtime_health::{
    derive_runtime_health, RuntimeHealthError, RuntimeHealthObservation, RuntimeHealthPolicy,
    RuntimeHealthState,
};

fn policy() -> RuntimeHealthPolicy {
    RuntimeHealthPolicy {
        quarantine_consecutive_failures: 3,
        unhealthy_failure_percent: 60,
        recovery_successes_required: 2,
        retry_pressure_limit: 0,
    }
}

fn observation() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        window_start_sequence: 1,
        window_end_sequence: 2,
        attempts: 1,
        successes: 1,
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
fn zero_retry_pressure_limit_is_valid_and_enforces_no_concurrent_retry() {
    let base = observation();
    let allowed = derive_runtime_health(&base, &policy()).expect("zero retry limit is valid");
    assert!(!allowed.retry_pressure_exceeded);
    assert_eq!(allowed.state, RuntimeHealthState::Healthy);

    let mut retrying = observation();
    retrying.active_retries = 1;
    let projected = derive_runtime_health(&retrying, &policy()).expect("projection");
    assert!(projected.retry_pressure_exceeded);
    assert_eq!(projected.state, RuntimeHealthState::Degraded);
}

#[test]
fn blank_runtime_identity_fails_closed() {
    let mut value = observation();
    value.runtime_id = "   ".to_string();
    assert_eq!(
        derive_runtime_health(&value, &policy()),
        Err(RuntimeHealthError::BlankRuntimeIdentity)
    );
}

#[test]
fn reversed_observation_window_fails_closed() {
    let mut value = observation();
    value.window_start_sequence = 10;
    value.window_end_sequence = 9;
    assert_eq!(
        derive_runtime_health(&value, &policy()),
        Err(RuntimeHealthError::InvalidObservationWindow)
    );
}
