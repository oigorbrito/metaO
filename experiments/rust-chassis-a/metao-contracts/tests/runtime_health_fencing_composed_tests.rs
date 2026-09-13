use metao_contracts::execution_lease::{
    admit_runtime_health_fact, AdmissionTimeBasis, ExecutionLease, ExecutionResultLineageProducer,
    ExecutionRuntimeBindingBasis, ExecutionRuntimeBindingClaim, ExecutionRuntimeBindingProducer,
    LeaseAssurance, LeaseEvidenceBasis, LeaseState, RuntimeHealthAdmissionAuthority,
    RuntimeHealthFactAdmissionError,
};
use metao_contracts::failure_causality::{
    bind_failure_origin_producer, FailureClassificationBasis, FailureOrigin, FailureOriginClaim,
    FailureOriginProducerEvidence, FailureOriginProducerKind, FactualExecutionOutcome,
};
use metao_contracts::runtime_health::{RuntimeHealthEvidenceBasis, RuntimeHealthObservation};
use metao_contracts::{ExecutionId, MissionId};

fn lease() -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-474".into(),
        logical_execution_key: "logical-474".into(),
        execution_id: "execution-474".into(),
        holder_identity: "controller-b".into(),
        generation: 9,
        fencing_token: 29,
        acquired_at_epoch: 100,
        renewed_at_epoch: 110,
        expires_at_epoch: 200,
        state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some("lease://474/g9".into()),
    }
}

fn producer() -> ExecutionRuntimeBindingProducer {
    ExecutionRuntimeBindingProducer {
        producer_id: "dispatch-producer-474".into(),
        mission_id: "mission-474".into(),
        logical_execution_key: "logical-474".into(),
        execution_id: "execution-474".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "cfg-a".into(),
        lease_generation: 9,
        fencing_token: 29,
        basis: ExecutionRuntimeBindingBasis::CanonicalDispatch,
        evidence_ref: "dispatch://474".into(),
    }
}

fn claim() -> ExecutionRuntimeBindingClaim {
    ExecutionRuntimeBindingClaim {
        mission_id: "mission-474".into(),
        logical_execution_key: "logical-474".into(),
        execution_id: "execution-474".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "cfg-a".into(),
        lease_generation: 9,
        fencing_token: 29,
    }
}

fn result() -> ExecutionResultLineageProducer {
    ExecutionResultLineageProducer {
        result_id: "result-474".into(),
        execution_id: "execution-474".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "cfg-a".into(),
        lease_generation: 9,
        fencing_token: 29,
        health_observation_evidence_ref: "health://474".into(),
        result_evidence_ref: "result://474".into(),
    }
}

fn success_observation() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "cfg-a".into(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: "health://474".into(),
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

fn failed_observation() -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        attempts: 1,
        successes: 0,
        failures: 1,
        consecutive_failures: 1,
        ..success_observation()
    }
}

fn authority(at: i64) -> RuntimeHealthAdmissionAuthority {
    RuntimeHealthAdmissionAuthority {
        holder_identity: "controller-b".into(),
        admitted_at_epoch: at,
        time_basis: AdmissionTimeBasis::TrustedControlPlaneClock,
        authority_ref: "control-plane-clock://474".into(),
    }
}

fn bound_origin(kind: FailureOriginProducerKind, origin: FailureOrigin) -> metao_contracts::failure_causality::BoundFailureOrigin {
    let producer = FailureOriginProducerEvidence {
        producer_id: format!("origin-{kind:?}"),
        mission_id: MissionId::new("mission-474").unwrap(),
        execution_id: Some(ExecutionId::new("execution-474").unwrap()),
        producer_kind: kind,
        original_outcome: Some(FactualExecutionOutcome::Failed),
        origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: "origin://474".into(),
    };
    let claim = FailureOriginClaim {
        mission_id: producer.mission_id.clone(),
        execution_id: producer.execution_id.clone(),
        original_outcome: producer.original_outcome,
        origin: producer.origin,
        evidence_ref: producer.evidence_ref.clone(),
    };
    bind_failure_origin_producer(&claim, &producer).unwrap()
}

#[test]
fn canonical_success_chain_admits_factual_health_fact() {
    let admitted = admit_runtime_health_fact(
        &claim(), &producer(), &result(), &success_observation(), &lease(), &authority(150), None,
    ).unwrap();
    assert_eq!(admitted.execution_id, "execution-474");
    assert_eq!(admitted.runtime_id, "runtime-a");
    assert_eq!(admitted.failure_origin_producer_id, None);
}

#[test]
fn runtime_local_failure_requires_and_accepts_producer_bound_origin() {
    let origin = bound_origin(FailureOriginProducerKind::RuntimeExecution, FailureOrigin::RuntimeLocal);
    let admitted = admit_runtime_health_fact(
        &claim(), &producer(), &result(), &failed_observation(), &lease(), &authority(150), Some(&origin),
    ).unwrap();
    assert_eq!(admitted.failure_origin_producer_id.as_deref(), Some("origin-RuntimeExecution"));
}

#[test]
fn failed_observation_without_canonical_origin_fails_closed() {
    assert_eq!(
        admit_runtime_health_fact(
            &claim(), &producer(), &result(), &failed_observation(), &lease(), &authority(150), None,
        ),
        Err(RuntimeHealthFactAdmissionError::FailureOriginRequired)
    );
}

#[test]
fn provider_and_network_failures_cannot_contaminate_runtime_local_health() {
    for (kind, origin) in [
        (FailureOriginProducerKind::ProviderAdapter, FailureOrigin::ProviderService),
        (FailureOriginProducerKind::NetworkAdapter, FailureOrigin::NetworkTransport),
    ] {
        let bound = bound_origin(kind, origin);
        assert_eq!(
            admit_runtime_health_fact(
                &claim(), &producer(), &result(), &failed_observation(), &lease(), &authority(150), Some(&bound),
            ),
            Err(RuntimeHealthFactAdmissionError::ExternalFailureOrigin)
        );
    }
}

#[test]
fn observation_from_other_execution_is_rejected_even_with_same_runtime_tuple() {
    let mut other = result();
    other.execution_id = "execution-old".into();
    assert!(matches!(
        admit_runtime_health_fact(
            &claim(), &producer(), &other, &success_observation(), &lease(), &authority(150), None,
        ),
        Err(RuntimeHealthFactAdmissionError::ResultLineage(_))
    ));
}

#[test]
fn stale_generation_or_fence_fails_independently_of_valid_lineage() {
    let mut stale = lease();
    stale.generation = 10;
    stale.fencing_token = 30;
    assert!(matches!(
        admit_runtime_health_fact(
            &claim(), &producer(), &result(), &success_observation(), &stale, &authority(150), None,
        ),
        Err(RuntimeHealthFactAdmissionError::RuntimeIdentityBinding(_))
    ));
}

#[test]
fn trusted_lineage_cannot_rescue_late_admission_after_expiry() {
    assert!(matches!(
        admit_runtime_health_fact(
            &claim(), &producer(), &result(), &success_observation(), &lease(), &authority(201), None,
        ),
        Err(RuntimeHealthFactAdmissionError::TrustedAdmission(_))
    ));
}

#[test]
fn caller_or_event_time_cannot_replace_trusted_admission_clock() {
    for basis in [AdmissionTimeBasis::CallerDeclared, AdmissionTimeBasis::EvidenceMetadata] {
        let mut untrusted = authority(150);
        untrusted.time_basis = basis;
        assert!(matches!(
            admit_runtime_health_fact(
                &claim(), &producer(), &result(), &success_observation(), &lease(), &untrusted, None,
            ),
            Err(RuntimeHealthFactAdmissionError::TrustedAdmission(_))
        ));
    }
}

#[test]
fn zero_attempt_bootstrap_state_is_not_execution_bound_admissible_fact() {
    let mut zero = success_observation();
    zero.attempts = 0;
    zero.successes = 0;
    zero.evidence_basis = RuntimeHealthEvidenceBasis::Unknown;
    assert!(matches!(
        admit_runtime_health_fact(
            &claim(), &producer(), &result(), &zero, &lease(), &authority(150), None,
        ),
        Err(RuntimeHealthFactAdmissionError::ResultLineage(_))
    ));
}

#[test]
fn admitted_fact_contains_no_health_state_retry_dispatch_or_acceptance_authority() {
    let admitted = admit_runtime_health_fact(
        &claim(), &producer(), &result(), &success_observation(), &lease(), &authority(150), None,
    ).unwrap();
    let encoded = serde_json::to_string(&admitted).unwrap();
    for forbidden in ["health_state", "next_attempt", "dispatch", "AcceptanceDecision"] {
        assert!(!encoded.contains(forbidden));
    }
}
