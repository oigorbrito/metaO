use metao_contracts::execution_lease::{
    ExecutionLease, ExecutionLeaseError, LeaseAssurance, LeaseEvidenceBasis, LeaseState,
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
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some(format!("lease-store:{generation}:{fence}")),
    }
}

#[test]
fn caller_declared_or_unknown_cannot_mint_authoritative_store_lease() {
    for basis in [
        LeaseEvidenceBasis::CallerDeclared,
        LeaseEvidenceBasis::Unknown,
    ] {
        let mut value = lease("owner-a", 1, 10);
        value.evidence_basis = basis;
        assert_eq!(
            value.validate(),
            Err(ExecutionLeaseError::InvalidEvidenceBasis)
        );
        assert!(!value.authorizes("owner-a", 1, 10, 150));
    }
}

#[test]
fn authoritative_store_lease_requires_nonblank_evidence_ref() {
    for evidence in [None, Some(String::new()), Some("   ".to_string())] {
        let mut value = lease("owner-a", 1, 10);
        value.evidence_ref = evidence;
        assert_eq!(value.validate(), Err(ExecutionLeaseError::BlankEvidenceRef));
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
fn lease_cannot_authorize_before_renewal_or_after_expiry() {
    let current = lease("owner-a", 1, 10);
    assert!(!current.authorizes("owner-a", 1, 10, 99));
    assert!(!current.authorizes("owner-a", 1, 10, 109));
    assert!(current.authorizes("owner-a", 1, 10, 110));
    assert!(!current.authorizes("owner-a", 1, 10, 200));
}

#[test]
fn invalid_public_lease_cannot_bypass_authorization_validation() {
    let mut current = lease("owner-a", 1, 10);
    current.expires_at_epoch = current.renewed_at_epoch;
    assert_eq!(
        current.validate(),
        Err(ExecutionLeaseError::InvalidTimeWindow)
    );
    assert!(!current.authorizes("owner-a", 1, 10, 110));
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
    assert!(current
        .validate_successor(&lease("owner-b", 3, 31))
        .is_err());
    assert!(current
        .validate_successor(&lease("owner-b", 4, 30))
        .is_err());
}

#[test]
fn execution_id_change_requires_new_generation_and_fence_even_for_same_holder() {
    let current = lease("owner-a", 5, 50);
    let mut same_generation = current.clone();
    same_generation.execution_id = "exec-new".to_string();
    same_generation.renewed_at_epoch = 120;
    same_generation.expires_at_epoch = 220;
    assert_eq!(
        current.validate_successor(&same_generation),
        Err(ExecutionLeaseError::GenerationRegression)
    );

    let mut same_fence = current.clone();
    same_fence.execution_id = "exec-new".to_string();
    same_fence.generation = 6;
    same_fence.renewed_at_epoch = 120;
    same_fence.expires_at_epoch = 220;
    assert_eq!(
        current.validate_successor(&same_fence),
        Err(ExecutionLeaseError::FenceRegression)
    );

    let mut valid = current.clone();
    valid.execution_id = "exec-new".to_string();
    valid.generation = 6;
    valid.fencing_token = 51;
    valid.renewed_at_epoch = 120;
    valid.expires_at_epoch = 220;
    valid.evidence_ref = Some("lease-store:6:51".to_string());
    assert_eq!(current.validate_successor(&valid), Ok(()));
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
    let mut renewed = current.clone();
    renewed.renewed_at_epoch = 120;
    renewed.expires_at_epoch = 220;
    assert_eq!(current.validate_successor(&renewed), Ok(()));
    assert_eq!(
        current.validate_successor(&lease("owner-a", 4, 50)),
        Err(ExecutionLeaseError::GenerationRegression)
    );
    assert_eq!(
        current.validate_successor(&lease("owner-a", 5, 49)),
        Err(ExecutionLeaseError::FenceRegression)
    );
}

#[test]
fn same_execution_renewal_cannot_roll_time_backwards() {
    let mut current = lease("owner-a", 5, 50);
    current.renewed_at_epoch = 150;
    current.expires_at_epoch = 260;
    let mut stale = current.clone();
    stale.renewed_at_epoch = 140;
    stale.expires_at_epoch = 250;
    assert_eq!(
        current.validate_successor(&stale),
        Err(ExecutionLeaseError::TimeRegression)
    );
}

#[test]
fn released_or_expired_lease_requires_new_generation_and_fence_to_reactivate() {
    for terminal_state in [LeaseState::Released, LeaseState::Expired] {
        let mut current = lease("owner-a", 5, 50);
        current.state = terminal_state;
        let mut stale = current.clone();
        stale.state = LeaseState::Active;
        stale.renewed_at_epoch = 120;
        stale.expires_at_epoch = 220;
        assert_eq!(
            current.validate_successor(&stale),
            Err(ExecutionLeaseError::GenerationRegression)
        );
        stale.generation = 6;
        stale.fencing_token = 51;
        stale.evidence_ref = Some("lease-store:6:51".to_string());
        assert_eq!(current.validate_successor(&stale), Ok(()));
    }
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
    assert_eq!(
        value.validate(),
        Err(ExecutionLeaseError::InvalidTimeWindow)
    );
}

#[test]
fn development_provider_is_explicitly_lower_assurance() {
    let mut value = lease("owner-local", 1, 1);
    value.assurance = LeaseAssurance::SingleInstanceDevelopment;
    value.evidence_basis = LeaseEvidenceBasis::DevelopmentLocal;
    value.evidence_ref = None;
    assert!(value.validate().is_ok());
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
    for forbidden in [
        "AcceptanceDecision",
        "ExecutionStatus",
        "FAILED",
        "PolicyEffect",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
