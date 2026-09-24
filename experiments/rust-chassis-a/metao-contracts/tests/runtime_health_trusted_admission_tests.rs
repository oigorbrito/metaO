use metao_contracts::execution_lease::{
    authorize_runtime_health_admission, AdmissionTimeBasis, AuthorizedRuntimeHealthAdmission,
    BoundRuntimeHealthObservationLineage, ExecutionLease, LeaseAssurance, LeaseEvidenceBasis,
    LeaseState, RuntimeHealthAdmissionAuthority, RuntimeHealthAdmissionError,
};

fn lease() -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-482".into(),
        logical_execution_key: "logical-482".into(),
        execution_id: "execution-482".into(),
        holder_identity: "worker-a".into(),
        generation: 7,
        fencing_token: 11,
        acquired_at_epoch: 100,
        renewed_at_epoch: 110,
        expires_at_epoch: 200,
        state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some("lease://482".into()),
    }
}
fn lineage() -> BoundRuntimeHealthObservationLineage {
    BoundRuntimeHealthObservationLineage {
        result_id: "result-482".into(),
        execution_id: "execution-482".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "cfg-a".into(),
        lease_generation: 7,
        fencing_token: 11,
        observation_evidence_ref: "health://482".into(),
        result_evidence_ref: "result://482".into(),
    }
}
fn trusted(at: i64) -> RuntimeHealthAdmissionAuthority {
    RuntimeHealthAdmissionAuthority {
        holder_identity: "worker-a".into(),
        admitted_at_epoch: at,
        time_basis: AdmissionTimeBasis::TrustedControlPlaneClock,
        authority_ref: "control-plane-clock://482".into(),
    }
}

#[test]
fn current_lease_and_trusted_time_inside_window_authorize_admission() {
    let result: AuthorizedRuntimeHealthAdmission =
        authorize_runtime_health_admission(&lineage(), &lease(), &trusted(150)).unwrap();
    assert_eq!(result.admitted_at_epoch, 150);
}
#[test]
fn late_result_cannot_be_rescued_by_backdated_event_metadata() {
    assert_eq!(
        authorize_runtime_health_admission(&lineage(), &lease(), &trusted(201)),
        Err(RuntimeHealthAdmissionError::StaleLeaseOrFence)
    );
}
#[test]
fn caller_declared_or_evidence_metadata_time_is_not_trusted_clock() {
    for basis in [
        AdmissionTimeBasis::CallerDeclared,
        AdmissionTimeBasis::EvidenceMetadata,
        AdmissionTimeBasis::Unknown,
    ] {
        let mut a = trusted(150);
        a.time_basis = basis;
        assert_eq!(
            authorize_runtime_health_admission(&lineage(), &lease(), &a),
            Err(RuntimeHealthAdmissionError::InvalidAdmissionAuthority)
        );
    }
}
#[test]
fn takeover_generation_or_fence_rotation_rejects_old_lineage() {
    let mut current = lease();
    current.generation = 8;
    current.fencing_token = 12;
    assert_eq!(
        authorize_runtime_health_admission(&lineage(), &current, &trusted(150)),
        Err(RuntimeHealthAdmissionError::LineageLeaseMismatch)
    );
}
#[test]
fn stale_holder_cannot_be_rescued_by_changing_only_time() {
    let mut a = trusted(150);
    a.holder_identity = "old-worker".into();
    assert_eq!(
        authorize_runtime_health_admission(&lineage(), &lease(), &a),
        Err(RuntimeHealthAdmissionError::StaleLeaseOrFence)
    );
}
#[test]
fn admission_projection_contains_no_health_mutation_retry_dispatch_or_acceptance() {
    let encoded = serde_json::to_string(
        &authorize_runtime_health_admission(&lineage(), &lease(), &trusted(150)).unwrap(),
    )
    .unwrap();
    for forbidden in [
        "health_state",
        "next_attempt",
        "dispatch",
        "AcceptanceDecision",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
