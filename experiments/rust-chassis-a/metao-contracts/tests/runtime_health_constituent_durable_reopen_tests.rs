use metao_contracts::execution_lease::{
    AdmittedRuntimeHealthConstituent, AdmittedRuntimeHealthFact, RuntimeHealthConstituentOutcome,
    RuntimeHealthConstituentPersistedState, RuntimeHealthConstituentRecordDecision,
    RuntimeHealthConstituentState, RuntimeHealthConstituentStateError,
};

fn constituent(
    result: &str,
    execution: &str,
    sequence: u64,
    outcome: RuntimeHealthConstituentOutcome,
) -> AdmittedRuntimeHealthConstituent {
    let lease_generation = 7;
    let fencing_token = lease_generation.saturating_add(4);
    AdmittedRuntimeHealthConstituent {
        fact: AdmittedRuntimeHealthFact {
            result_id: result.into(),
            execution_id: execution.into(),
            runtime_id: "runtime-a".into(),
            runtime_version: "1".into(),
            config_id: "cfg-a".into(),
            lease_generation,
            fencing_token,
            admitted_at_epoch: 150,
            admission_authority_ref: "clock://501".into(),
            observation_evidence_ref: format!("health://{execution}"),
            result_evidence_ref: format!("result://{execution}"),
            failure_origin_producer_id: if outcome == RuntimeHealthConstituentOutcome::Succeeded {
                None
            } else {
                Some(format!("origin-{execution}"))
            },
        },
        sequence,
        outcome,
    }
}

#[test]
fn json_round_trip_reopens_same_authoritative_window() {
    let mut state = RuntimeHealthConstituentState::new();
    state
        .record(constituent(
            "r1",
            "e1",
            1,
            RuntimeHealthConstituentOutcome::RuntimeLocalFailed,
        ))
        .unwrap();
    state
        .record(constituent(
            "r2",
            "e2",
            2,
            RuntimeHealthConstituentOutcome::Succeeded,
        ))
        .unwrap();
    let before = state.aggregate(0, None, None).unwrap();
    let encoded = serde_json::to_string(&state.export_state()).unwrap();
    let persisted: RuntimeHealthConstituentPersistedState = serde_json::from_str(&encoded).unwrap();
    let reopened = RuntimeHealthConstituentState::reopen(persisted).unwrap();
    let after = reopened.aggregate(0, None, None).unwrap();
    assert_eq!(before, after);
    assert_eq!(after.attempts, 2);
    assert_eq!(after.failures, 1);
}

#[test]
fn replay_after_restart_is_idempotent() {
    let one = constituent(
        "r1",
        "e1",
        1,
        RuntimeHealthConstituentOutcome::RuntimeLocalFailed,
    );
    let mut state = RuntimeHealthConstituentState::new();
    state.record(one.clone()).unwrap();
    let mut reopened = RuntimeHealthConstituentState::reopen(state.export_state()).unwrap();
    assert_eq!(
        reopened.record(one),
        Ok(RuntimeHealthConstituentRecordDecision::Idempotent)
    );
    assert_eq!(reopened.constituents().len(), 1);
    assert_eq!(reopened.aggregate(0, None, None).unwrap().failures, 1);
}

#[test]
fn conflicting_result_after_restart_fails_closed() {
    let one = constituent(
        "r1",
        "e1",
        1,
        RuntimeHealthConstituentOutcome::RuntimeLocalFailed,
    );
    let mut state = RuntimeHealthConstituentState::new();
    state.record(one.clone()).unwrap();
    let mut reopened = RuntimeHealthConstituentState::reopen(state.export_state()).unwrap();
    let mut conflict = one;
    conflict.outcome = RuntimeHealthConstituentOutcome::Succeeded;
    conflict.fact.failure_origin_producer_id = None;
    assert_eq!(
        reopened.record(conflict),
        Err(RuntimeHealthConstituentStateError::DuplicateResultConflict)
    );
}

#[test]
fn sequence_conflict_after_restart_fails_closed() {
    let mut state = RuntimeHealthConstituentState::new();
    state
        .record(constituent(
            "r1",
            "e1",
            1,
            RuntimeHealthConstituentOutcome::Succeeded,
        ))
        .unwrap();
    let mut reopened = RuntimeHealthConstituentState::reopen(state.export_state()).unwrap();
    assert_eq!(
        reopened.record(constituent(
            "r2",
            "e2",
            1,
            RuntimeHealthConstituentOutcome::Succeeded
        )),
        Err(RuntimeHealthConstituentStateError::SequenceConflict)
    );
}

#[test]
fn corrupted_persisted_failure_without_origin_is_rejected() {
    let mut broken = constituent(
        "r1",
        "e1",
        1,
        RuntimeHealthConstituentOutcome::RuntimeLocalFailed,
    );
    broken.fact.failure_origin_producer_id = None;
    assert!(matches!(
        RuntimeHealthConstituentState::reopen(RuntimeHealthConstituentPersistedState {
            constituents: vec![broken]
        }),
        Err(RuntimeHealthConstituentStateError::InvalidConstituent)
    ));
}

#[test]
fn duplicate_entry_in_persisted_state_is_rejected_not_silently_deduped() {
    let one = constituent("r1", "e1", 1, RuntimeHealthConstituentOutcome::Succeeded);
    assert_eq!(
        RuntimeHealthConstituentState::reopen(RuntimeHealthConstituentPersistedState {
            constituents: vec![one.clone(), one]
        })
        .err(),
        Some(RuntimeHealthConstituentStateError::InvalidPersistedState)
    );
}

#[test]
fn reopened_state_accepts_next_sequence_without_reauthorizing_prior_facts() {
    let mut state = RuntimeHealthConstituentState::new();
    state
        .record(constituent(
            "r1",
            "e1",
            1,
            RuntimeHealthConstituentOutcome::Succeeded,
        ))
        .unwrap();
    let mut reopened = RuntimeHealthConstituentState::reopen(state.export_state()).unwrap();
    assert_eq!(
        reopened.record(constituent(
            "r2",
            "e2",
            2,
            RuntimeHealthConstituentOutcome::RuntimeLocalTimeout
        )),
        Ok(RuntimeHealthConstituentRecordDecision::Recorded)
    );
    let window = reopened.aggregate(0, None, None).unwrap();
    assert_eq!(window.attempts, 2);
    assert_eq!(window.failures, 1);
    assert_eq!(window.timeouts, 1);
    assert_eq!(window.transport_failures, 0);
}
