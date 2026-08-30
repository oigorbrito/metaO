use metao_contracts::execution_lease::{
    ExecutionLease, ExecutionLeaseError, LeaseAssurance, LeaseState,
};

fn lease(holder: &str, generation: u64, fence: u64) -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-1".to_string(),
        logical_execution_key: "logical-execution-1".to_string(),
        execution_id: format!("exec-{generation}"),
        holder_identity: holder.to_string(),
        generation,
        fencing_token: fence,
        acquired_at_epoch: 100,
        renewed_at_epoch: 110,
        expires_at_epoch: 200,
        state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
    }
}

#[test]
fn exact_current_holder_generation_and_fence_are_required() {
    let current = lease("owner-a", 1, 10);
    assert!(current.authorizes("owner-a", 1, 10, 150));
    assert!(!current.authorizes("owner-a", 1, 9, 150));
    assert!(!current.authorizes("owner-a", 0, 10, 150));
    assert!(!current.authorizes("owner-b", 1, 10, 150));
}

#[test]
fn expired_or_released_lease_never_authorizes() {
    let current = lease("owner-a", 1, 10);
    assert!(!current.authorizes("owner-a", 1, 10, 200));

    let mut released = current.clone();
    released.state = LeaseState::Released;
    assert!(!released.authorizes("owner-a", 1, 10, 150));
}

#[test]
fn takeover_requires_strictly_newer_generation_and_fence() {
    let current = lease("owner-a", 3, 30);
    let successor = lease("owner-b", 4, 31);
    assert_eq!(current.validate_successor(&successor), Ok(()));

    let stale_generation = lease("owner-b", 3, 31);
    assert!(current.validate_successor(&stale_generation).is_err());

    let stale_fence = lease("owner-b", 4, 30);
    assert!(current.validate_successor(&stale_fence).is_err());
}

#[test]
fn stale_owner_returning_after_takeover_is_rejected() {
    let old = lease("owner-a", 7, 70);
    let current = lease("owner-b", 8, 80);
    old.validate_successor(&current).expect("valid takeover");

    assert!(current.authorizes("owner-b", 8, 80, 150));
    assert!(!current.authorizes("owner-a", 7, 70, 150));
}

#[test]
fn late_done_from_old_owner_has_no_ownership_authority() {
    let current = lease("owner-b", 8, 80);
    assert!(!current.authorizes("owner-a", 7, 70, 150));
}

#[test]
fn same_holder_renewal_cannot_move_generation_or_fence_backwards() {
    let current = lease("owner-a", 5, 50);
    let mut renewed = lease("owner-a", 5, 50);
    renewed.renewed_at_epoch = 120;
    renewed.expires_at_epoch = 220;
    assert_eq!(current.validate_successor(&renewed), Ok(()));

    let stale_generation = lease("owner-a", 4, 50);
    assert_eq!(
        current.validate_successor(&stale_generation),
        Err(ExecutionLeaseError::GenerationRegression)
    );
    let stale_fence = lease("owner-a", 5, 49);
    assert_eq!(
        current.validate_successor(&stale_fence),
        Err(ExecutionLeaseError::FenceRegression)
    );
}

#[test]
fn zero_generation_or_fence_fails_closed() {
    let mut value = lease("owner-a", 1, 10);
    value.generation = 0;
    assert_eq!(value.validate(), Err(ExecutionLeaseError::ZeroGeneration));

    let mut value = lease("owner-a", 1, 10);
    value.fencing_token = 0;
    assert_eq!(value.validate(), Err(ExecutionLeaseError::ZeroFencingToken));
}

#[test]
fn invalid_time_window_fails_closed() {
    let mut value = lease("owner-a", 1, 10);
    value.expires_at_epoch = value.renewed_at_epoch;
    assert_eq!(value.validate(), Err(ExecutionLeaseError::InvalidTimeWindow));
}

#[test]
fn development_provider_is_explicitly_lower_assurance() {
    let mut value = lease("owner-local", 1, 1);
    value.assurance = LeaseAssurance::SingleInstanceDevelopment;
    let encoded = serde_json::to_string(&value).expect("serialize");
    assert!(encoded.contains("SingleInstanceDevelopment"));
    assert!(!encoded.contains("HA_PROTECTED"));
    assert!(!encoded.contains("high_availability_guaranteed"));
}

#[test]
fn deterministic_serialization_contains_no_failure_or_acceptance_authority() {
    let value = lease("owner-a", 1, 10);
    let encoded = serde_json::to_string(&value).expect("serialize");
    let decoded: ExecutionLease = serde_json::from_str(&encoded).expect("deserialize");
    assert_eq!(decoded, value);
    for forbidden in ["AcceptanceDecision", "ExecutionStatus", "FAILED", "PolicyEffect"] {
        assert!(!encoded.contains(forbidden));
    }
}
