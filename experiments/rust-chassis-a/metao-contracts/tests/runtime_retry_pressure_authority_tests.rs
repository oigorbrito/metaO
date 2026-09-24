use metao_contracts::runtime_health::{
    bind_active_retry_pressure, ActiveRetryAuthorityBasis, ActiveRetryExecutionRecord,
    ActiveRetryExecutionState, ActiveRetrySetProducer, RuntimeHealthError,
};
use metao_contracts::MissionId;

fn record(id: &str, state: ActiveRetryExecutionState) -> ActiveRetryExecutionRecord {
    ActiveRetryExecutionRecord {
        retry_execution_id: id.into(),
        mission_id: MissionId::new("mission-504").unwrap(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1".into(),
        config_id: "cfg-a".into(),
        retry_lineage_id: "lineage-a".into(),
        authority_generation: 7,
        fencing_token: 11,
        current_authority_generation: 7,
        current_fencing_token: 11,
        state,
        evidence_ref: format!("retry-registry://{id}"),
    }
}

fn producer(records: Vec<ActiveRetryExecutionRecord>) -> ActiveRetrySetProducer {
    ActiveRetrySetProducer {
        producer_id: "canonical-execution-registry".into(),
        state_version: 12,
        basis: ActiveRetryAuthorityBasis::CanonicalExecutionRegistry,
        evidence_ref: "execution-registry://snapshot/12".into(),
        records,
    }
}

#[test]
fn canonical_active_set_counts_only_active_exact_runtime_records() {
    let mut other = record("other-runtime", ActiveRetryExecutionState::Active);
    other.runtime_id = "runtime-b".into();
    let bound = bind_active_retry_pressure(
        &producer(vec![
            record("a", ActiveRetryExecutionState::Active),
            record("b", ActiveRetryExecutionState::Active),
            record("settled", ActiveRetryExecutionState::Settled),
            other,
        ]),
        "runtime-a",
        "1",
        "cfg-a",
    )
    .unwrap();
    assert_eq!(bound.active_retries(), 2);
    assert_eq!(bound.state_version(), 12);
    assert_eq!(bound.producer_id(), "canonical-execution-registry");
}

#[test]
fn identical_duplicate_retry_execution_is_idempotent() {
    let item = record("same", ActiveRetryExecutionState::Active);
    let bound = bind_active_retry_pressure(
        &producer(vec![item.clone(), item]),
        "runtime-a",
        "1",
        "cfg-a",
    )
    .unwrap();
    assert_eq!(bound.active_retries(), 1);
}

#[test]
fn conflicting_duplicate_retry_execution_fails_closed() {
    let first = record("same", ActiveRetryExecutionState::Active);
    let mut conflict = first.clone();
    conflict.state = ActiveRetryExecutionState::Settled;
    assert_eq!(
        bind_active_retry_pressure(&producer(vec![first, conflict]), "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::RetryPressureDuplicateConflict)
    );
}

#[test]
fn caller_declared_or_unknown_basis_cannot_mint_pressure_authority() {
    for basis in [
        ActiveRetryAuthorityBasis::CallerDeclared,
        ActiveRetryAuthorityBasis::Unknown,
    ] {
        let mut value = producer(vec![record("a", ActiveRetryExecutionState::Active)]);
        value.basis = basis;
        assert_eq!(
            bind_active_retry_pressure(&value, "runtime-a", "1", "cfg-a"),
            Err(RuntimeHealthError::InvalidRetryPressureAuthority)
        );
    }
}

#[test]
fn blank_or_unversioned_registry_snapshot_fails_closed() {
    let mut blank = producer(vec![]);
    blank.evidence_ref = " ".into();
    assert_eq!(
        bind_active_retry_pressure(&blank, "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::InvalidRetryPressureAuthority)
    );
    let mut unversioned = producer(vec![]);
    unversioned.state_version = 0;
    assert_eq!(
        bind_active_retry_pressure(&unversioned, "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::InvalidRetryPressureAuthority)
    );
}

#[test]
fn zero_generation_or_fence_is_invalid() {
    let mut stale = record("stale", ActiveRetryExecutionState::Active);
    stale.authority_generation = 0;
    assert_eq!(
        bind_active_retry_pressure(&producer(vec![stale]), "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::InvalidRetryPressureAuthority)
    );
    let mut unfenced = record("unfenced", ActiveRetryExecutionState::Active);
    unfenced.fencing_token = 0;
    assert_eq!(
        bind_active_retry_pressure(&producer(vec![unfenced]), "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::InvalidRetryPressureAuthority)
    );
}

#[test]
fn rotated_generation_or_fence_rejects_record_still_claimed_active() {
    let mut generation = record("generation", ActiveRetryExecutionState::Active);
    generation.current_authority_generation = 8;
    assert_eq!(
        bind_active_retry_pressure(&producer(vec![generation]), "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::RetryPressureStaleExecution)
    );
    let mut fence = record("fence", ActiveRetryExecutionState::Active);
    fence.current_fencing_token = 12;
    assert_eq!(
        bind_active_retry_pressure(&producer(vec![fence]), "runtime-a", "1", "cfg-a"),
        Err(RuntimeHealthError::RetryPressureStaleExecution)
    );
}

#[test]
fn terminal_record_does_not_become_active_after_rotation() {
    let mut settled = record("settled", ActiveRetryExecutionState::Settled);
    settled.current_authority_generation = 8;
    settled.current_fencing_token = 12;
    let bound =
        bind_active_retry_pressure(&producer(vec![settled]), "runtime-a", "1", "cfg-a").unwrap();
    assert_eq!(bound.active_retries(), 0);
}

#[test]
fn pressure_projection_contains_no_dispatch_or_acceptance_authority() {
    let bound = bind_active_retry_pressure(
        &producer(vec![record("a", ActiveRetryExecutionState::Active)]),
        "runtime-a",
        "1",
        "cfg-a",
    )
    .unwrap();
    let encoded = serde_json::to_string(&bound).unwrap();
    for forbidden in ["dispatch", "next_attempt", "failover", "AcceptanceDecision"] {
        assert!(!encoded.contains(forbidden));
    }
}
