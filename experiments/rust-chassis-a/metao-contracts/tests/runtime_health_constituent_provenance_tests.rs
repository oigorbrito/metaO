use metao_contracts::execution_lease::{
    admit_runtime_health_constituent, aggregate_runtime_health_constituents, AdmissionTimeBasis,
    AdmittedRuntimeHealthConstituent, AdmittedRuntimeHealthFact, ExecutionLease,
    ExecutionResultLineageProducer, ExecutionRuntimeBindingBasis, ExecutionRuntimeBindingClaim,
    ExecutionRuntimeBindingProducer, LeaseAssurance, LeaseEvidenceBasis, LeaseState,
    RuntimeHealthAdmissionAuthority, RuntimeHealthConstituentError, RuntimeHealthConstituentOutcome,
    RuntimeHealthFactAdmissionError,
};
use metao_contracts::failure_causality::{
    BoundFailureOrigin, FailureClassificationBasis, FailureOrigin, FailureOriginProducerKind,
    FactualExecutionOutcome,
};
use metao_contracts::runtime_health::{RuntimeHealthEvidenceBasis, RuntimeHealthObservation};
use metao_contracts::{ExecutionId, MissionId};

fn lease(execution: &str) -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-501".into(), logical_execution_key: format!("logical-{execution}"),
        execution_id: execution.into(), holder_identity: "worker-501".into(), generation: 7,
        fencing_token: 11, acquired_at_epoch: 100, renewed_at_epoch: 110,
        expires_at_epoch: 200, state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some(format!("lease://{execution}")),
    }
}

fn producer(execution: &str) -> ExecutionRuntimeBindingProducer {
    ExecutionRuntimeBindingProducer {
        producer_id: format!("dispatch-{execution}"), mission_id: "mission-501".into(),
        logical_execution_key: format!("logical-{execution}"), execution_id: execution.into(),
        runtime_id: "runtime-a".into(), runtime_version: "1".into(), config_id: "cfg-a".into(),
        lease_generation: 7, fencing_token: 11, basis: ExecutionRuntimeBindingBasis::CanonicalDispatch,
        evidence_ref: format!("dispatch://{execution}"),
    }
}

fn claim(execution: &str) -> ExecutionRuntimeBindingClaim {
    let p = producer(execution);
    ExecutionRuntimeBindingClaim {
        mission_id: p.mission_id, logical_execution_key: p.logical_execution_key,
        execution_id: p.execution_id, runtime_id: p.runtime_id, runtime_version: p.runtime_version,
        config_id: p.config_id, lease_generation: p.lease_generation, fencing_token: p.fencing_token,
    }
}

fn observation(execution: &str, seq: u64, success: bool, timeout: bool) -> RuntimeHealthObservation {
    RuntimeHealthObservation {
        runtime_id: "runtime-a".into(), runtime_version: "1".into(), config_id: "cfg-a".into(),
        evidence_basis: RuntimeHealthEvidenceBasis::AdapterVerified,
        evidence_ref: format!("health://{execution}"), window_start_sequence: seq, window_end_sequence: seq,
        attempts: 1, successes: u32::from(success), failures: u32::from(!success),
        consecutive_failures: u32::from(!success), timeouts: u32::from(timeout), transport_failures: 0,
        active_retries: 0, fresh_successes_since_unhealthy: 0, prior_state: None,
        self_reported_healthy: None,
    }
}

fn result(execution: &str) -> ExecutionResultLineageProducer {
    ExecutionResultLineageProducer {
        result_id: format!("result-{execution}"), execution_id: execution.into(), runtime_id: "runtime-a".into(),
        runtime_version: "1".into(), config_id: "cfg-a".into(), lease_generation: 7, fencing_token: 11,
        health_observation_evidence_ref: format!("health://{execution}"),
        result_evidence_ref: format!("result://{execution}"),
    }
}

fn authority() -> RuntimeHealthAdmissionAuthority {
    RuntimeHealthAdmissionAuthority {
        holder_identity: "worker-501".into(), admitted_at_epoch: 150,
        time_basis: AdmissionTimeBasis::TrustedControlPlaneClock,
        authority_ref: "clock://501".into(),
    }
}

fn origin(execution: &str, origin: FailureOrigin, kind: FailureOriginProducerKind) -> BoundFailureOrigin {
    BoundFailureOrigin {
        producer_id: format!("origin-{execution}"), mission_id: MissionId::new("mission-501").unwrap(),
        execution_id: Some(ExecutionId::new(execution).unwrap()), producer_kind: kind,
        original_outcome: Some(FactualExecutionOutcome::Failed), origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: format!("origin://{execution}"),
    }
}

fn admitted(execution: &str, seq: u64, outcome: RuntimeHealthConstituentOutcome) -> AdmittedRuntimeHealthConstituent {
    AdmittedRuntimeHealthConstituent {
        fact: AdmittedRuntimeHealthFact {
            result_id: format!("result-{execution}"), execution_id: execution.into(), runtime_id: "runtime-a".into(),
            runtime_version: "1".into(), config_id: "cfg-a".into(), lease_generation: 7, fencing_token: 11,
            admitted_at_epoch: 150, admission_authority_ref: "clock://501".into(),
            observation_evidence_ref: format!("health://{execution}"), result_evidence_ref: format!("result://{execution}"),
            failure_origin_producer_id: if outcome == RuntimeHealthConstituentOutcome::Succeeded { None } else { Some(format!("origin-{execution}")) },
        },
        sequence: seq,
        outcome,
    }
}

#[test]
fn aggregate_two_runtime_local_failures_counts_two() {
    let window = aggregate_runtime_health_constituents(&[
        admitted("e1", 1, RuntimeHealthConstituentOutcome::RuntimeLocalFailed),
        admitted("e2", 2, RuntimeHealthConstituentOutcome::RuntimeLocalFailed),
    ], 0, None, None).unwrap();
    assert_eq!(window.attempts, 2);
    assert_eq!(window.failures, 2);
    assert_eq!(window.transport_failures, 0);
}

#[test]
fn provider_failure_is_rejected_before_runtime_local_aggregation() {
    let obs = observation("provider", 2, false, false);
    let external = origin("provider", FailureOrigin::ProviderService, FailureOriginProducerKind::ProviderAdapter);
    let err = admit_runtime_health_constituent(&claim("provider"), &producer("provider"), &result("provider"), &obs, &lease("provider"), &authority(), Some(&external)).unwrap_err();
    assert_eq!(err, RuntimeHealthConstituentError::Admission(RuntimeHealthFactAdmissionError::ExternalFailureOrigin));
    let window = aggregate_runtime_health_constituents(&[
        admitted("local", 1, RuntimeHealthConstituentOutcome::RuntimeLocalFailed),
    ], 0, None, None).unwrap();
    assert_eq!(window.failures, 1);
}

#[test]
fn network_timeout_is_rejected_before_runtime_local_aggregation() {
    let obs = observation("network", 2, false, true);
    let external = origin("network", FailureOrigin::NetworkTransport, FailureOriginProducerKind::NetworkAdapter);
    let err = admit_runtime_health_constituent(&claim("network"), &producer("network"), &result("network"), &obs, &lease("network"), &authority(), Some(&external)).unwrap_err();
    assert_eq!(err, RuntimeHealthConstituentError::Admission(RuntimeHealthFactAdmissionError::ExternalFailureOrigin));
}

#[test]
fn caller_aggregate_with_two_attempts_is_not_a_constituent() {
    let mut obs = observation("aggregate", 1, false, false);
    obs.attempts = 2; obs.failures = 2; obs.consecutive_failures = 2; obs.window_end_sequence = 2;
    let local = origin("aggregate", FailureOrigin::RuntimeLocal, FailureOriginProducerKind::RuntimeExecution);
    assert_eq!(
        admit_runtime_health_constituent(&claim("aggregate"), &producer("aggregate"), &result("aggregate"), &obs, &lease("aggregate"), &authority(), Some(&local)),
        Err(RuntimeHealthConstituentError::NotSingleExecutionObservation)
    );
}

#[test]
fn duplicate_replay_is_idempotent_but_conflict_fails_closed() {
    let one = admitted("e1", 1, RuntimeHealthConstituentOutcome::RuntimeLocalFailed);
    let window = aggregate_runtime_health_constituents(&[one.clone(), one.clone()], 0, None, None).unwrap();
    assert_eq!(window.attempts, 1);
    let mut conflict = one.clone(); conflict.outcome = RuntimeHealthConstituentOutcome::Succeeded;
    assert_eq!(
        aggregate_runtime_health_constituents(&[one, conflict], 0, None, None),
        Err(RuntimeHealthConstituentError::DuplicateResultConflict)
    );
}

#[test]
fn same_sequence_cannot_name_two_results() {
    assert_eq!(
        aggregate_runtime_health_constituents(&[
            admitted("e1", 1, RuntimeHealthConstituentOutcome::Succeeded),
            admitted("e2", 1, RuntimeHealthConstituentOutcome::Succeeded),
        ], 0, None, None),
        Err(RuntimeHealthConstituentError::SequenceConflict)
    );
}

#[test]
fn stale_constituent_is_rejected_before_aggregation() {
    let obs = observation("stale", 1, true, false);
    let mut stale = lease("stale"); stale.generation = 8; stale.fencing_token = 12;
    let err = admit_runtime_health_constituent(&claim("stale"), &producer("stale"), &result("stale"), &obs, &stale, &authority(), None).unwrap_err();
    assert!(matches!(err, RuntimeHealthConstituentError::Admission(_)));
}

#[test]
fn success_requires_no_failure_origin() {
    let obs = observation("success", 1, true, false);
    let constituent = admit_runtime_health_constituent(&claim("success"), &producer("success"), &result("success"), &obs, &lease("success"), &authority(), None).unwrap();
    assert_eq!(constituent.outcome, RuntimeHealthConstituentOutcome::Succeeded);
    assert_eq!(constituent.fact.failure_origin_producer_id, None);
}

#[test]
fn aggregation_projection_mints_no_dispatch_retry_or_acceptance_authority() {
    let window = aggregate_runtime_health_constituents(&[
        admitted("e1", 1, RuntimeHealthConstituentOutcome::Succeeded),
    ], 0, None, Some(true)).unwrap();
    let encoded = serde_json::to_string(&window).unwrap();
    for forbidden in ["dispatch", "next_attempt", "AcceptanceDecision", "failover"] {
        assert!(!encoded.contains(forbidden));
    }
}
