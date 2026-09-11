use metao_contracts::runtime_health::{
    evaluate_recovery_probe_authorization, RecoveryProbeAuthorizationFacts,
    RecoveryProbeEligibility, RuntimeHealthEvidenceBasis, RuntimeHealthObservation,
    RuntimeHealthPolicy, RuntimeHealthState,
};

fn policy() -> RuntimeHealthPolicy {
    RuntimeHealthPolicy {
        quarantine_consecutive_failures: 3,
        unhealthy_failure_percent: 60,
        recovery_successes_required: 2,
        retry_pressure_limit: 2,
    }
}

fn observation(state: RuntimeHealthState) -> RuntimeHealthObservation {
    let mut observation = RuntimeHealthObservation {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: format!("health:runtime-a:{state:?}"),
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
    };

    match state {
        RuntimeHealthState::Healthy => {}
        RuntimeHealthState::Degraded => {
            observation.successes = 3;
            observation.failures = 1;
            observation.consecutive_failures = 1;
        }
        RuntimeHealthState::Unhealthy => {
            observation.successes = 1;
            observation.failures = 3;
            observation.consecutive_failures = 2;
        }
        RuntimeHealthState::Quarantined => {
            observation.window_end_sequence = 3;
            observation.attempts = 3;
            observation.successes = 0;
            observation.failures = 3;
            observation.consecutive_failures = 3;
        }
        RuntimeHealthState::Recovering => {
            observation.window_start_sequence = 2;
            observation.attempts = 3;
            observation.successes = 2;
            observation.failures = 1;
            observation.consecutive_failures = 0;
            observation.fresh_successes_since_unhealthy = 1;
            observation.prior_state = Some(RuntimeHealthState::Unhealthy);
        }
        RuntimeHealthState::Unknown => {
            observation.window_start_sequence = 0;
            observation.window_end_sequence = 0;
            observation.attempts = 0;
            observation.successes = 0;
            observation.failures = 0;
        }
    }

    observation
}

fn authorized() -> RecoveryProbeAuthorizationFacts {
    RecoveryProbeAuthorizationFacts {
        explicit_probe_intent: true,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

fn evaluate(
    state: RuntimeHealthState,
    facts: &RecoveryProbeAuthorizationFacts,
) -> metao_contracts::runtime_health::RecoveryProbeAuthorizationProjection {
    evaluate_recovery_probe_authorization(&observation(state), &policy(), facts)
        .expect("factual health fixture must validate")
}

#[test]
fn unhealthy_and_quarantined_runtime_can_be_probe_eligible_when_explicitly_authorized() {
    for state in [RuntimeHealthState::Unhealthy, RuntimeHealthState::Quarantined] {
        let result = evaluate(state, &authorized());
        assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
        assert_eq!(result.health_state, state);
    }
}

#[test]
fn recovering_runtime_remains_probe_path_not_ordinary_health_mutation() {
    let result = evaluate(RuntimeHealthState::Recovering, &authorized());
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
    assert_eq!(result.health_state, RuntimeHealthState::Recovering);
    assert!(result.reason.contains("post-probe health remain separate"));
}

#[test]
fn missing_explicit_probe_intent_blocks_recovery_probe() {
    let mut facts = authorized();
    facts.explicit_probe_intent = false;
    let result = evaluate(RuntimeHealthState::Quarantined, &facts);
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
        let result = evaluate(RuntimeHealthState::Quarantined, &facts);
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
        let result = evaluate(state, &authorized());
        assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
        assert!(result.reason.contains("does not require controlled recovery"));
    }
}

#[test]
fn self_reported_healthy_does_not_authorize_or_restore_state() {
    let mut factual = observation(RuntimeHealthState::Quarantined);
    factual.self_reported_healthy = Some(true);
    let result = evaluate_recovery_probe_authorization(&factual, &policy(), &authorized())
        .expect("self-report does not invalidate factual evidence");
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
    assert_eq!(result.health_state, RuntimeHealthState::Quarantined);
}

#[test]
fn self_reported_unknown_or_blank_health_evidence_fails_closed() {
    for basis in [
        RuntimeHealthEvidenceBasis::SelfReported,
        RuntimeHealthEvidenceBasis::Unknown,
    ] {
        let mut forged = observation(RuntimeHealthState::Quarantined);
        forged.evidence_basis = basis;
        assert!(evaluate_recovery_probe_authorization(&forged, &policy(), &authorized()).is_err());
    }

    let mut blank = observation(RuntimeHealthState::Quarantined);
    blank.evidence_ref = "   ".to_string();
    assert!(evaluate_recovery_probe_authorization(&blank, &policy(), &authorized()).is_err());
}

#[test]
fn authorization_projection_contains_no_dispatch_or_acceptance_authority() {
    let encoded = serde_json::to_string(&evaluate(RuntimeHealthState::Quarantined, &authorized()))
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
