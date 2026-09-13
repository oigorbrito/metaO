use metao_contracts::execution_governance::ExecutionGateDecision;
use metao_contracts::runtime_health::{
    evaluate_controlled_recovery_probe, BoundRecoveryProbeIntent, RecoveryProbeEligibility,
    RecoveryProbeEligibilityError, RecoveryProbeGovernanceProjection, RuntimeHealthEvidenceBasis,
    RuntimeHealthObservation, RuntimeHealthPolicy,
};
use metao_contracts::ExecutionId;

fn intent() -> BoundRecoveryProbeIntent {
    BoundRecoveryProbeIntent {
        intent_id: "probe-intent-469".into(),
        execution_id: ExecutionId::new("probe-exec-469").unwrap(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0.0".into(),
        config_id: "config-a".into(),
        authority_generation: 3,
        fencing_token: 7,
        evidence_ref: "authority://probe/469".into(),
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

fn unhealthy() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0.0".into(),
        config_id: "config-a".into(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: "health://runtime-a/469".into(),
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
    }
}

fn governance(decision: ExecutionGateDecision) -> RecoveryProbeGovernanceProjection {
    RecoveryProbeGovernanceProjection {
        policy_denied: decision == ExecutionGateDecision::Block,
        risk_stopped: false,
        budget_blocked: false,
        human_approval_required: false,
        human_approval_satisfied: false,
        budget_version: 11,
        decision,
    }
}

#[test]
fn canonical_intent_governance_and_unhealthy_fact_are_probe_eligible() {
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::Proceed),
        &unhealthy(),
        &policy(),
    )
    .unwrap();
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Eligible);
    assert_eq!(result.budget_version, 11);
}

#[test]
fn governance_block_dominates_factual_unhealthy_state() {
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::Block),
        &unhealthy(),
        &policy(),
    )
    .unwrap();
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
}

#[test]
fn require_human_never_becomes_probe_eligibility() {
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::RequireHuman),
        &unhealthy(),
        &policy(),
    )
    .unwrap();
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
}

#[test]
fn runtime_binding_drift_fails_closed() {
    let mut observed = unhealthy();
    observed.runtime_id = "runtime-b".into();
    assert_eq!(
        evaluate_controlled_recovery_probe(
            &intent(),
            &governance(ExecutionGateDecision::Proceed),
            &observed,
            &policy(),
        ),
        Err(RecoveryProbeEligibilityError::IntentHealthBindingMismatch)
    );
}

#[test]
fn healthy_runtime_does_not_use_controlled_probe_path() {
    let mut observed = unhealthy();
    observed.successes = 4;
    observed.failures = 0;
    observed.consecutive_failures = 0;
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::Proceed),
        &observed,
        &policy(),
    )
    .unwrap();
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
}

#[test]
fn invalid_health_provenance_blocks_instead_of_becoming_unknown_escape_hatch() {
    let mut observed = unhealthy();
    observed.evidence_basis = RuntimeHealthEvidenceBasis::SelfReported;
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::Proceed),
        &observed,
        &policy(),
    )
    .unwrap();
    assert_eq!(result.eligibility, RecoveryProbeEligibility::Ineligible);
}

#[test]
fn eligibility_projection_contains_no_dispatch_or_acceptance_authority() {
    let result = evaluate_controlled_recovery_probe(
        &intent(),
        &governance(ExecutionGateDecision::Proceed),
        &unhealthy(),
        &policy(),
    )
    .unwrap();
    let encoded = serde_json::to_string(&result).unwrap();
    for forbidden in ["dispatch", "AcceptanceDecision", "retry_executed"] {
        assert!(!encoded.contains(forbidden));
    }
}
