use metao_contracts::failure_causality::{
    bind_failure_origin_producer, project_bound_failure_origin, FactualExecutionOutcome,
    FailureAttributionTarget, FailureClassificationBasis, FailureOrigin, FailureOriginClaim,
    FailureOriginProducerEvidence, FailureOriginProducerKind,
};
use metao_contracts::{ExecutionId, MissionId};

fn mission() -> MissionId {
    MissionId::new("mission-472").unwrap()
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-472").unwrap()
}

fn producer(
    kind: FailureOriginProducerKind,
    origin: FailureOrigin,
) -> FailureOriginProducerEvidence {
    let pre_execution = matches!(
        kind,
        FailureOriginProducerKind::CapacityAuthority | FailureOriginProducerKind::PolicyAuthority
    );
    FailureOriginProducerEvidence {
        producer_id: format!("producer-{kind:?}"),
        mission_id: mission(),
        execution_id: (!pre_execution).then(execution),
        producer_kind: kind,
        original_outcome: (!pre_execution).then_some(FactualExecutionOutcome::Failed),
        origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: format!("evidence://{kind:?}"),
    }
}

fn claim(p: &FailureOriginProducerEvidence) -> FailureOriginClaim {
    FailureOriginClaim {
        mission_id: p.mission_id.clone(),
        execution_id: p.execution_id.clone(),
        original_outcome: p.original_outcome,
        origin: p.origin,
        evidence_ref: p.evidence_ref.clone(),
    }
}

#[test]
fn runtime_local_projection_requires_runtime_producer_binding() {
    let p = producer(
        FailureOriginProducerKind::RuntimeExecution,
        FailureOrigin::RuntimeLocal,
    );
    let bound = bind_failure_origin_producer(&claim(&p), &p).unwrap();
    let projection = project_bound_failure_origin(&bound);
    assert!(projection.factual);
    assert_eq!(projection.attribution, FailureAttributionTarget::Runtime);
    assert_eq!(
        projection.original_outcome,
        Some(FactualExecutionOutcome::Failed)
    );
}

#[test]
fn provider_and_network_remain_external_attribution_targets() {
    for (kind, origin, target) in [
        (
            FailureOriginProducerKind::ProviderAdapter,
            FailureOrigin::ProviderService,
            FailureAttributionTarget::Provider,
        ),
        (
            FailureOriginProducerKind::NetworkAdapter,
            FailureOrigin::NetworkTransport,
            FailureAttributionTarget::Network,
        ),
    ] {
        let p = producer(kind, origin);
        let bound = bind_failure_origin_producer(&claim(&p), &p).unwrap();
        let projection = project_bound_failure_origin(&bound);
        assert_eq!(projection.attribution, target);
        assert_ne!(projection.attribution, FailureAttributionTarget::Runtime);
    }
}

#[test]
fn capacity_and_policy_projection_preserve_absent_execution_outcome() {
    for (kind, origin, target) in [
        (
            FailureOriginProducerKind::CapacityAuthority,
            FailureOrigin::Capacity,
            FailureAttributionTarget::Capacity,
        ),
        (
            FailureOriginProducerKind::PolicyAuthority,
            FailureOrigin::Policy,
            FailureAttributionTarget::Policy,
        ),
    ] {
        let p = producer(kind, origin);
        let bound = bind_failure_origin_producer(&claim(&p), &p).unwrap();
        let projection = project_bound_failure_origin(&bound);
        assert_eq!(projection.original_outcome, None);
        assert_eq!(projection.attribution, target);
    }
}

#[test]
fn projection_contains_producer_identity_and_no_retry_or_acceptance_authority() {
    let p = producer(
        FailureOriginProducerKind::RuntimeExecution,
        FailureOrigin::RuntimeLocal,
    );
    let bound = bind_failure_origin_producer(&claim(&p), &p).unwrap();
    let encoded = serde_json::to_string(&project_bound_failure_origin(&bound)).unwrap();
    assert!(encoded.contains("producer_id"));
    for forbidden in [
        "next_attempt",
        "dispatch",
        "AcceptanceDecision",
        "retry_executed",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
