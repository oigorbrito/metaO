use metao_contracts::execution_lease::{
    ExecutionLease, LeaseAssurance, LeaseEvidenceBasis, LeaseState,
};
use metao_contracts::runtime_health::{
    authorize_runtime_health_observation, RuntimeHealthObservationAuthority,
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

#[test]
fn current_authoritative_owner_can_authorize_health_observation() {
    let projection = authorize_runtime_health_observation(&lease(), &authority());
    assert!(projection.authorized);
    assert!(projection.reason.contains("current execution lease"));
}

#[test]
fn stale_generation_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.lease_generation = 1;
    let projection = authorize_runtime_health_observation(&lease(), &stale);
    assert!(!projection.authorized);
}

#[test]
fn stale_fencing_token_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.fencing_token = 21;
    let projection = authorize_runtime_health_observation(&lease(), &stale);
    assert!(!projection.authorized);
}

#[test]
fn wrong_holder_cannot_authorize_health_observation() {
    let mut stale = authority();
    stale.holder_identity = "controller-a".to_string();
    let projection = authorize_runtime_health_observation(&lease(), &stale);
    assert!(!projection.authorized);
}

#[test]
fn expired_or_released_lease_cannot_authorize_health_observation() {
    let mut expired_time = authority();
    expired_time.observed_at_epoch = 200;
    assert!(!authorize_runtime_health_observation(&lease(), &expired_time).authorized);

    let mut released = lease();
    released.state = LeaseState::Released;
    assert!(!authorize_runtime_health_observation(&released, &authority()).authorized);
}

#[test]
fn execution_binding_mismatch_is_rejected_before_fence_evaluation() {
    let mut mismatched = authority();
    mismatched.execution_id = "execution-old".to_string();
    let projection = authorize_runtime_health_observation(&lease(), &mismatched);
    assert!(!projection.authorized);
    assert!(projection.reason.contains("binding"));
}

#[test]
fn non_authoritative_lease_provenance_cannot_authorize_observation() {
    let mut forged = lease();
    forged.evidence_basis = LeaseEvidenceBasis::CallerDeclared;
    let projection = authorize_runtime_health_observation(&forged, &authority());
    assert!(!projection.authorized);
}

#[test]
fn authorization_projection_contains_no_health_mutation_or_execution_outcome() {
    let projection = authorize_runtime_health_observation(&lease(), &authority());
    let encoded = serde_json::to_string(&projection).expect("serialize projection");

    assert!(encoded.contains("authorized"));
    assert!(!encoded.contains("Healthy"));
    assert!(!encoded.contains("Failed"));
    assert!(!encoded.contains("attempts"));
    assert!(!encoded.contains("dispatch"));
    assert!(!encoded.contains("acceptance"));
}
