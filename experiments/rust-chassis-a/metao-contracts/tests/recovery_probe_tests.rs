use metao_contracts::runtime_health::{
    evaluate_recovery_probe_authorization, RecoveryProbeAuthorizationFacts,
    RecoveryProbeEligibility, RuntimeHealthProjection, RuntimeHealthState,
};

fn health(state: RuntimeHealthState) -> RuntimeHealthProjection {
    RuntimeHealthProjection {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        state,
        attempts: 3,
        successes: 1,
        failures: 2,
        consecutive_failures: 2,
        timeouts: 0,
        transport_failures: 0,
        active_retries: 0,
        retry_pressure_exceeded: false,
        self_reported_healthy: Some(true),
        reasons: vec!["fixture".to_string()],
    }
}

fn authorized() -> RecoveryProbeAuthorizationFacts {
    RecoveryProbeAuthorizationFacts {
        explicit_probe_intent: true,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

#[test]
fn unhealthy_and_quarantined_runtime_can_be_probe_eligible_when_explicitly_authorized() {
    for state in [RuntimeHealthState::Unhealthy, RuntimeHealthState::Quarantined] {
        let result = evaluate_recovery_probe_authorization(&health(state), &authorized());
        assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
        assert_eq!(result.health_state, state);
    }
}

#[test]
fn recovering_runtime_remains_probe_path_not_ordinary_health_mutation() {
    let result = evaluate_recovery_probe_authorization(
        &health(RuntimeHealthState::Recovering),
        &authorized(),
    );
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
    assert_eq!(result.health_state, RuntimeHealthState::Recovering);
    assert!(result.reason.contains("post-probe health remain separate"));
}

#[test]
fn missing_explicit_probe_intent_blocks_recovery_probe() {
    let mut facts = authorized();
    facts.explicit_probe_intent = false;
    let result = evaluate_recovery_probe_authorization(
        &health(RuntimeHealthState::Quarantined),
        &facts,
    );
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
    assert!(result.reason.contains("explicit authorization intent"));
}

#[test]
fn policy_risk_and_budget_denials_dominate_probe_intent() {
    for index in 0..3 {
        let mut facts = authorized();
        match index {
            0 => facts.policy_blocked = true,
            1 => facts.risk_blocked = true,
            _ => facts.budget_blocked = true,
        }
        let result = evaluate_recovery_probe_authorization(
            &health(RuntimeHealthState::Quarantined),
            &facts,
        );
        assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
    }
}

#[test]
fn healthy_degraded_and_unknown_do_not_use_recovery_probe_path() {
    for state in [
        RuntimeHealthState::Healthy,
        RuntimeHealthState::Degraded,
        RuntimeHealthState::Unknown,
    ] {
        let result = evaluate_recovery_probe_authorization(&health(state), &authorized());
        assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
        assert!(result.reason.contains("does not require controlled recovery"));
    }
}

#[test]
fn self_reported_healthy_does_not_authorize_or_restore_state() {
    let projection = health(RuntimeHealthState::Quarantined);
    assert_eq!(projection.self_reported_healthy, Some(true));
    let result = evaluate_recovery_probe_authorization(&projection, &authorized());
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
    assert_eq!(result.health_state, RuntimeHealthState::Quarantined);
}

#[test]
fn authorization_projection_contains_no_dispatch_or_acceptance_authority() {
    let encoded = serde_json::to_string(&evaluate_recovery_probe_authorization(
        &health(RuntimeHealthState::Quarantined),
        &authorized(),
    ))
    .expect("serialize recovery probe authorization");

    for forbidden in [
        "dispatch",
        "retry_executed",
        "failover_executed",
        "AcceptanceDecision",
        "provider_sdk",
        "HEALTHY",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
