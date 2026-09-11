use metao_contracts::execution_lease::{
    ExecutionLease, LeaseAssurance, LeaseEvidenceBasis, LeaseState,
};
use metao_contracts::runtime_health::{
    authorize_runtime_health_observation, RuntimeExecutionHealthBinding,
    RuntimeHealthEvidenceBasis, RuntimeHealthObservation, RuntimeHealthObservationAuthority,
};

fn lease() -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-1".to_string(),
        logical_execution_key: "logical-1".to_string(),
        execution_id: "execution-2".to_string(),
        holder_identity: "controller-b".to_string(),
        generation: 2,
        fencing_token: 22,
        acquired_at_epoch: 100,
        renewed_at_epoch: 110,
        expires_at_epoch: 200,
        state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some("lease-store:execution-2:g2".to_string()),
    }
}

fn authority() -> RuntimeHealthObservationAuthority {
    RuntimeHealthObservationAuthority {
        execution_id: "execution-2".to_string(),
        holder_identity: "controller-b".to_string(),
        lease_generation: 2,
        fencing_token: 22,
        observed_at_epoch: 150,
    }
}

fn binding() -> RuntimeExecutionHealthBinding {
    RuntimeExecutionHealthBinding {
        execution_id: "execution-2".to_string(),
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: "adapter:execution-2:runtime-a".to_string(),
    }
}

fn observation() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "config-a".to_string(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: "health:execution-2:runtime-a".to_string(),
        window_start_sequence: 1,
        window_end_sequence: 1,
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

fn authorize(
    lease: &ExecutionLease,
    authority: &RuntimeHealthObservationAuthority,
    binding: &RuntimeExecutionHealthBinding,
    observation: &RuntimeHealthObservation,
) -> metao_contracts::runtime_health::RuntimeHealthObservationAuthorization {
    authorize_runtime_health_observation(lease, authority, binding, observation)
}

#[test]
fn current_owner_with_factual_runtime_binding_can_authorize_health_observation() {
    let projection = authorize(&lease(), &authority(), &binding(), &observation());
    assert!(projection.authorized);
    assert_eq!(projection.runtime_id, "runtime-a");
    assert!(projection.reason.contains("factual execution-to-runtime binding"));
}

#[test]
fn stale_generation_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.lease_generation = 1;
    assert!(!authorize(&lease(), &stale, &binding(), &observation()).authorized);
}

#[test]
fn stale_fencing_token_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.fencing_token = 21;
    assert!(!authorize(&lease(), &stale, &binding(), &observation()).authorized);
}

#[test]
fn wrong_holder_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.holder_identity = "controller-a".to_string();
    assert!(!authorize(&lease(), &stale, &binding(), &observation()).authorized);
}

#[test]
fn expired_or_released_lease_cannot_authorize_health_observation() {
    let mut expired_time = authority();
    expired_time.observed_at_epoch = 200;
    assert!(!authorize(&lease(), &expired_time, &binding(), &observation()).authorized);

    let mut released = lease();
    released.state = LeaseState::Released;
    assert!(!authorize(&released, &authority(), &binding(), &observation()).authorized);
}

#[test]
fn execution_binding_mismatch_is_rejected_before_runtime_attribution() {
    let mut mismatched = binding();
    mismatched.execution_id = "execution-old".to_string();
    let projection = authorize(&lease(), &authority(), &mismatched, &observation());
    assert!(!projection.authorized);
    assert!(projection.reason.contains("execution binding"));
}

#[test]
fn runtime_version_or_config_mismatch_cannot_contaminate_other_health_history() {
    for field in 0..3 {
        let mut mismatched = binding();
        match field {
            0 => mismatched.runtime_id = "runtime-b".to_string(),
            1 => mismatched.runtime_version = "2.0.0".to_string(),
            _ => mismatched.config_id = "config-b".to_string(),
        }
        let projection = authorize(&lease(), &authority(), &mismatched, &observation());
        assert!(!projection.authorized);
        assert!(projection.reason.contains("runtime binding"));
    }
}

#[test]
fn caller_declared_or_blank_binding_evidence_fails_closed() {
    let mut caller = binding();
    caller.evidence_basis = RuntimeHealthEvidenceBasis::SelfReported;
    assert!(!authorize(&lease(), &authority(), &caller, &observation()).authorized);

    let mut blank = binding();
    blank.evidence_ref = "   ".to_string();
    assert!(!authorize(&lease(), &authority(), &blank, &observation()).authorized);
}

#[test]
fn invalid_observation_evidence_fails_closed_even_with_valid_lease_and_binding() {
    let mut forged = observation();
    forged.evidence_basis = RuntimeHealthEvidenceBasis::SelfReported;
    assert!(!authorize(&lease(), &authority(), &binding(), &forged).authorized);
}

#[test]
fn non_authoritative_lease_provenance_cannot_authorize_observation() {
    let mut forged = lease();
    forged.evidence_basis = LeaseEvidenceBasis::CallerDeclared;
    assert!(!authorize(&forged, &authority(), &binding(), &observation()).authorized);
}

#[test]
fn authorization_projection_contains_no_health_mutation_or_execution_outcome() {
    let projection = authorize(&lease(), &authority(), &binding(), &observation());
    let encoded = serde_json::to_string(&projection).expect("serialize projection");

    assert!(encoded.contains("authorized"));
    assert!(encoded.contains("runtime-a"));
    assert!(!encoded.contains("Healthy"));
    assert!(!encoded.contains("Failed"));
    assert!(!encoded.contains("attempts"));
    assert!(!encoded.contains("dispatch"));
    assert!(!encoded.contains("acceptance"));
}
