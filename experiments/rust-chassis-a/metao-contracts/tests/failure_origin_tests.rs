use metao_contracts::failure_causality::{
    attribute_failure_origin, FailureAttributionTarget, FailureClassificationBasis, FailureOrigin,
    FailureOriginFacts, FactualExecutionOutcome,
};

fn facts(origin: FailureOrigin) -> FailureOriginFacts {
    FailureOriginFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        origin,
        basis: FailureClassificationBasis::AuthoritativeObservation,
        evidence_ref: Some("evidence:failure-origin:1".to_string()),
    }
}

#[test]
fn runtime_local_failure_is_attributed_only_to_runtime() {
    let projection = attribute_failure_origin(&facts(FailureOrigin::RuntimeLocal));
    assert_eq!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn provider_failure_is_not_attributed_to_runtime() {
    let projection = attribute_failure_origin(&facts(FailureOrigin::ProviderService));
    assert_eq!(projection.attribution, FailureAttributionTarget::Provider);
    assert_ne!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn network_transport_failure_is_not_attributed_to_runtime() {
    let projection = attribute_failure_origin(&facts(FailureOrigin::NetworkTransport));
    assert_eq!(projection.attribution, FailureAttributionTarget::Network);
    assert_ne!(projection.attribution, FailureAttributionTarget::Runtime);
    assert!(projection.factual);
}

#[test]
fn capacity_and_policy_conditions_remain_separate_from_runtime_health() {
    let capacity = attribute_failure_origin(&facts(FailureOrigin::Capacity));
    let policy = attribute_failure_origin(&facts(FailureOrigin::Policy));

    assert_eq!(capacity.attribution, FailureAttributionTarget::Capacity);
    assert_eq!(policy.attribution, FailureAttributionTarget::Policy);
    assert_ne!(capacity.attribution, FailureAttributionTarget::Runtime);
    assert_ne!(policy.attribution, FailureAttributionTarget::Runtime);
    assert!(capacity.reason.contains("not runtime health"));
    assert!(policy.reason.contains("not runtime health"));
}

#[test]
fn caller_declared_origin_without_authoritative_basis_fails_closed() {
    let mut forged = facts(FailureOrigin::RuntimeLocal);
    forged.basis = FailureClassificationBasis::CallerDeclared;

    let projection = attribute_failure_origin(&forged);
    assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
    assert!(!projection.factual);
}

#[test]
fn missing_or_blank_evidence_fails_closed() {
    let mut missing = facts(FailureOrigin::ProviderService);
    missing.evidence_ref = None;
    let missing_projection = attribute_failure_origin(&missing);

    let mut blank = facts(FailureOrigin::NetworkTransport);
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
        let mut input = facts(FailureOrigin::RuntimeLocal);
        input.original_outcome = outcome;
        let projection = attribute_failure_origin(&input);
        assert_eq!(projection.attribution, FailureAttributionTarget::None);
        assert!(!projection.factual);
    }
}

#[test]
fn unknown_origin_remains_unknown_even_with_factual_evidence() {
    let projection = attribute_failure_origin(&facts(FailureOrigin::Unknown));
    assert_eq!(projection.attribution, FailureAttributionTarget::Unknown);
    assert!(!projection.factual);
}

#[test]
fn serialized_projection_contains_no_retry_dispatch_or_acceptance_authority() {
    let projection = attribute_failure_origin(&facts(FailureOrigin::ProviderService));
    let encoded = serde_json::to_string(&projection).expect("serialize projection");

    assert!(encoded.contains("Provider"));
    assert!(!encoded.contains("next_attempt"));
    assert!(!encoded.contains("dispatch"));
    assert!(!encoded.contains("acceptance"));
    assert!(!encoded.contains("healthy"));
}
