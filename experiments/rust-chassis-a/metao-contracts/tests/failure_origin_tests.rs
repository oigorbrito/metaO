use metao_contracts::failure_causality::{
    attribute_failure_origin, FailureAttributionTarget, FailureClassificationBasis, FailureOrigin,
    FailureOriginFacts, FactualExecutionOutcome,
};

fn execution_failure(origin: FailureOrigin) -> FailureOriginFacts {
    FailureOriginFacts {
        original_outcome: Some(FactualExecutionOutcome::Failed),
        origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: Some("evidence:failure-origin:1".to_string()),
    }
}

fn pre_execution_condition(origin: FailureOrigin) -> FailureOriginFacts {
    FailureOriginFacts {
        original_outcome: None,
        origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: Some("evidence:pre-execution-origin:1".to_string()),
    }
}

#[test]
fn runtime_local_failure_is_attributed_only_to_runtime() {
    let projection = attribute_failure_origin(&execution_failure(FailureOrigin::RuntimeLocal));
    assert_eq!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn provider_failure_is_not_attributed_to_runtime() {
    let projection = attribute_failure_origin(&execution_failure(FailureOrigin::ProviderService));
    assert_eq!(projection.attribution, FailureAttributionTarget::Provider);
    assert_ne!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn network_transport_failure_is_not_attributed_to_runtime() {
    let projection = attribute_failure_origin(&execution_failure(FailureOrigin::NetworkTransport));
    assert_eq!(projection.attribution, FailureAttributionTarget::Network);
    assert_ne!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn capacity_and_policy_conditions_are_pre_execution_and_do_not_mint_failure_outcomes() {
    let capacity = attribute_failure_origin(&pre_execution_condition(FailureOrigin::Capacity));
    let policy = attribute_failure_origin(&pre_execution_condition(FailureOrigin::Policy));

    assert_eq!(capacity.original_outcome, None);
    assert_eq!(policy.original_outcome, None);
    assert_eq!(capacity.attribution, FailureAttributionTarget::Capacity);
    assert_eq!(policy.attribution, FailureAttributionTarget::Policy);
    assert_ne!(capacity.attribution, FailureAttributionTarget::Runtime);
    assert_ne!(policy.attribution, FailureAttributionTarget::Runtime);
    assert!(capacity.reason.contains("pre-execution"));
    assert!(policy.reason.contains("pre-execution"));
}

#[test]
fn inconsistent_capacity_or_policy_with_execution_outcome_fails_closed() {
    for origin in [FailureOrigin::Capacity, FailureOrigin::Policy] {
        let projection = attribute_failure_origin(&execution_failure(origin));
        assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
        assert!(!projection.factual);
        assert!(projection.reason.contains("cannot carry an execution outcome"));
    }
}

#[test]
fn execution_failure_origins_require_failed_or_timeout_outcome() {
    for origin in [
        FailureOrigin::RuntimeLocal,
        FailureOrigin::ProviderService,
        FailureOrigin::NetworkTransport,
    ] {
        let mut missing = execution_failure(origin);
        missing.original_outcome = None;
        let projection = attribute_failure_origin(&missing);
        assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
        assert!(!projection.factual);

        let mut succeeded = execution_failure(origin);
        succeeded.original_outcome = Some(FactualExecutionOutcome::Succeeded);
        let projection = attribute_failure_origin(&succeeded);
        assert_eq!(projection.attribution, FailureAttributionTarget::None);
        assert!(!projection.factual);
    }
}

#[test]
fn caller_declared_origin_without_authoritative_basis_fails_closed() {
    let mut forged = execution_failure(FailureOrigin::RuntimeLocal);
    forged.basis = FailureClassificationBasis::CallerDeclared;

    let projection = attribute_failure_origin(&forged);
    assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
    assert!(!projection.factual);
}

#[test]
fn missing_or_blank_evidence_fails_closed() {
    let mut missing = execution_failure(FailureOrigin::ProviderService);
    missing.evidence_ref = None;
    let missing_projection = attribute_failure_origin(&missing);

    let mut blank = execution_failure(FailureOrigin::NetworkTransport);
    blank.evidence_ref = Some("   ".to_string());
    let blank_projection = attribute_failure_origin(&blank);

    assert_eq!(missing_projection.attribution, FailureAttributionTarget::Unknown);
    assert_eq!(blank_projection.attribution, FailureAttributionTarget::Unknown);
    assert!(!missing_projection.factual);
    assert!(!blank_projection.factual);
}

#[test]
fn successful_or_cancelled_outcomes_do_not_mint_failure_attribution() {
    for outcome in [
        FactualExecutionOutcome::Succeeded,
        FactualExecutionOutcome::Cancelled,
    ] {
        let mut input = execution_failure(FailureOrigin::RuntimeLocal);
        input.original_outcome = Some(outcome);
        let projection = attribute_failure_origin(&input);
        assert_eq!(projection.attribution, FailureAttributionTarget::None);
        assert!(!projection.factual);
    }
}

#[test]
fn unknown_origin_remains_unknown_even_with_factual_evidence() {
    let projection = attribute_failure_origin(&execution_failure(FailureOrigin::Unknown));
    assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
    assert!(!projection.factual);
}

#[test]
fn serialized_projection_contains_no_retry_dispatch_or_acceptance_authority() {
    let projection = attribute_failure_origin(&execution_failure(FailureOrigin::ProviderService));
    let encoded = serde_json::to_string(&projection).expect("serialize projection");

    assert!(encoded.contains("Provider"));
    assert!(!encoded.contains("next_attempt"));
    assert!(!encoded.contains("dispatch"));
    assert!(!encoded.contains("acceptance"));
    assert!(!encoded.contains("healthy"));
}
