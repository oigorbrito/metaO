use metao_contracts::failure_causality::{
    bind_failure_origin_producer, FactualExecutionOutcome, FailureClassificationBasis,
    FailureOrigin, FailureOriginClaim, FailureOriginProducerError, FailureOriginProducerEvidence,
    FailureOriginProducerKind,
};
use metao_contracts::{ExecutionId, MissionId};

fn mission() -> MissionId {
    MissionId::new("mission-479").unwrap()
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-479").unwrap()
}

fn runtime_producer() -> FailureOriginProducerEvidence {
    FailureOriginProducerEvidence {
        producer_id: "runtime-producer-479".into(),
        mission_id: mission(),
        execution_id: Some(execution()),
        producer_kind: FailureOriginProducerKind::RuntimeExecution,
        original_outcome: Some(FactualExecutionOutcome::Failed),
        origin: FailureOrigin::RuntimeLocal,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: "execution://479/runtime-failure".into(),
    }
}

fn claim_from(producer: &FailureOriginProducerEvidence) -> FailureOriginClaim {
    FailureOriginClaim {
        mission_id: producer.mission_id.clone(),
        execution_id: producer.execution_id.clone(),
        original_outcome: producer.original_outcome,
        origin: producer.origin,
        evidence_ref: producer.evidence_ref.clone(),
    }
}

#[test]
fn canonical_runtime_local_producer_binds_runtime_origin() {
    let producer = runtime_producer();
    let bound = bind_failure_origin_producer(&claim_from(&producer), &producer).unwrap();
    assert_eq!(bound.origin, FailureOrigin::RuntimeLocal);
    assert_eq!(
        bound.producer_kind,
        FailureOriginProducerKind::RuntimeExecution
    );
}

#[test]
fn provider_origin_cannot_be_rewritten_runtime_local() {
    let mut producer = runtime_producer();
    producer.producer_kind = FailureOriginProducerKind::ProviderAdapter;
    producer.origin = FailureOrigin::ProviderService;
    producer.producer_id = "provider-producer-479".into();
    let mut forged = claim_from(&producer);
    forged.origin = FailureOrigin::RuntimeLocal;
    assert_eq!(
        bind_failure_origin_producer(&forged, &producer),
        Err(FailureOriginProducerError::ClaimBindingMismatch)
    );
}

#[test]
fn network_origin_remains_external() {
    let mut producer = runtime_producer();
    producer.producer_kind = FailureOriginProducerKind::NetworkAdapter;
    producer.origin = FailureOrigin::NetworkTransport;
    producer.original_outcome = Some(FactualExecutionOutcome::Timeout);
    let bound = bind_failure_origin_producer(&claim_from(&producer), &producer).unwrap();
    assert_eq!(bound.origin, FailureOrigin::NetworkTransport);
}

#[test]
fn capacity_and_policy_do_not_mint_execution_failure() {
    for (kind, origin) in [
        (
            FailureOriginProducerKind::CapacityAuthority,
            FailureOrigin::Capacity,
        ),
        (
            FailureOriginProducerKind::PolicyAuthority,
            FailureOrigin::Policy,
        ),
    ] {
        let producer = FailureOriginProducerEvidence {
            producer_id: format!("preexec-{kind:?}"),
            mission_id: mission(),
            execution_id: Some(execution()),
            producer_kind: kind,
            original_outcome: None,
            origin,
            basis: FailureClassificationBasis::AuthoritativeObservation,
            evidence_ref: "preexec://479".into(),
        };
        let bound = bind_failure_origin_producer(&claim_from(&producer), &producer).unwrap();
        assert_eq!(bound.original_outcome, None);
    }
}

#[test]
fn capacity_with_failed_outcome_is_semantically_invalid() {
    let producer = FailureOriginProducerEvidence {
        producer_id: "capacity-479".into(),
        mission_id: mission(),
        execution_id: Some(execution()),
        producer_kind: FailureOriginProducerKind::CapacityAuthority,
        original_outcome: Some(FactualExecutionOutcome::Failed),
        origin: FailureOrigin::Capacity,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: "capacity://479".into(),
    };
    assert_eq!(
        bind_failure_origin_producer(&claim_from(&producer), &producer),
        Err(FailureOriginProducerError::ProducerSemanticMismatch)
    );
}

#[test]
fn copied_origin_and_evidence_ref_do_not_override_canonical_producer_kind() {
    let mut producer = runtime_producer();
    producer.producer_kind = FailureOriginProducerKind::ProviderAdapter;
    assert_eq!(
        bind_failure_origin_producer(&claim_from(&producer), &producer),
        Err(FailureOriginProducerError::ProducerSemanticMismatch)
    );
}

#[test]
fn weak_or_blank_producer_evidence_fails_closed() {
    let mut producer = runtime_producer();
    producer.basis = FailureClassificationBasis::CallerDeclared;
    assert_eq!(
        bind_failure_origin_producer(&claim_from(&producer), &producer),
        Err(FailureOriginProducerError::InvalidProducerEvidence)
    );

    let mut producer = runtime_producer();
    producer.evidence_ref = "  ".into();
    assert_eq!(
        bind_failure_origin_producer(&claim_from(&producer), &producer),
        Err(FailureOriginProducerError::InvalidProducerEvidence)
    );
}

#[test]
fn success_or_cancelled_cannot_be_failure_producer() {
    for outcome in [
        FactualExecutionOutcome::Succeeded,
        FactualExecutionOutcome::Cancelled,
    ] {
        let mut producer = runtime_producer();
        producer.original_outcome = Some(outcome);
        assert_eq!(
            bind_failure_origin_producer(&claim_from(&producer), &producer),
            Err(FailureOriginProducerError::ProducerSemanticMismatch)
        );
    }
}
