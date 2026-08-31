use metao_contracts::failure_causality::{
    evaluate_retry_eligibility, FactualExecutionOutcome, FailureCausalityFacts, FailureClass,
    FailureClassificationBasis, RecoveryStatus, RetryEligibility,
};

fn transient_failure() -> FailureCausalityFacts {
    FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AdapterNormalization,
        failure_class_evidence_ref: Some("adapter-error:RUNTIME_ADAPTER_FAILED".to_string()),
        recovery_required: true,
        recovery_status: RecoveryStatus::Complete,
        current_attempt: 1,
        max_attempts: 3,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

#[test]
fn factual_transient_failure_can_be_eligible_without_executing_retry() {
    let result = evaluate_retry_eligibility(&transient_failure());
    assert_eq!(result.eligibility, RetryEligibility::Eligible);
    assert_eq!(result.next_attempt, Some(2));
    assert_eq!(result.original_outcome, FactualExecutionOutcome::Failed);
    assert_eq!(
        result.failure_class_basis,
        FailureClassificationBasis::AdapterNormalization
    );
}

#[test]
fn caller_declared_transience_is_not_retry_authority() {
    let mut facts = transient_failure();
    facts.failure_class_basis = FailureClassificationBasis::CallerDeclared;
    let result = evaluate_retry_eligibility(&facts);
    assert_eq!(result.eligibility, RetryEligibility::Ineligible);
    assert_eq!(result.next_attempt, None);
    assert!(result
        .reason
        .contains("lacks authoritative factual evidence"));
}

#[test]
fn missing_or_blank_transience_evidence_is_ineligible() {
    for evidence_ref in [None, Some(String::new()), Some("   ".to_string())] {
        let mut facts = transient_failure();
        facts.failure_class_evidence_ref = evidence_ref;
        assert_eq!(
            evaluate_retry_eligibility(&facts).eligibility,
            RetryEligibility::Ineligible
        );
    }
}

#[test]
fn missing_classification_basis_cannot_enable_retry() {
    let mut facts = transient_failure();
    facts.failure_class_basis = FailureClassificationBasis::Missing;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn authoritative_observation_can_support_transience() {
    let mut facts = transient_failure();
    facts.failure_class_basis = FailureClassificationBasis::AuthoritativeObservation;
    facts.failure_class_evidence_ref = Some("transport-observation:timeout-42".to_string());
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Eligible
    );
}

#[test]
fn cancelled_is_not_generic_failed_or_retryable() {
    let mut facts = transient_failure();
    facts.original_outcome = FactualExecutionOutcome::Cancelled;
    let result = evaluate_retry_eligibility(&facts);
    assert_eq!(result.original_outcome, FactualExecutionOutcome::Cancelled);
    assert_eq!(result.eligibility, RetryEligibility::Ineligible);
}

#[test]
fn timeout_remains_explicit_and_requires_transient_classification() {
    let mut facts = transient_failure();
    facts.original_outcome = FactualExecutionOutcome::Timeout;
    let result = evaluate_retry_eligibility(&facts);
    assert_eq!(result.original_outcome, FactualExecutionOutcome::Timeout);
    assert_eq!(result.eligibility, RetryEligibility::Eligible);

    facts.failure_class = FailureClass::Unknown;
    let unknown = evaluate_retry_eligibility(&facts);
    assert_eq!(unknown.eligibility, RetryEligibility::Ineligible);
}

#[test]
fn unknown_failure_is_not_transient_by_default() {
    let mut facts = transient_failure();
    facts.failure_class = FailureClass::Unknown;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn permanent_failure_is_ineligible() {
    let mut facts = transient_failure();
    facts.failure_class = FailureClass::Permanent;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn required_recovery_must_be_complete_before_retry() {
    for recovery in [
        RecoveryStatus::NotRequired,
        RecoveryStatus::NotAttempted,
        RecoveryStatus::Incomplete,
        RecoveryStatus::Failed,
    ] {
        let mut facts = transient_failure();
        facts.recovery_status = recovery;
        assert_eq!(
            evaluate_retry_eligibility(&facts).eligibility,
            RetryEligibility::Ineligible
        );
    }
}

#[test]
fn no_recovery_requirement_allows_explicit_not_required_state() {
    let mut facts = transient_failure();
    facts.recovery_required = false;
    facts.recovery_status = RecoveryStatus::NotRequired;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Eligible
    );
}

#[test]
fn no_recovery_requirement_does_not_make_not_attempted_ambiguous_state_eligible() {
    let mut facts = transient_failure();
    facts.recovery_required = false;
    facts.recovery_status = RecoveryStatus::NotAttempted;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn successful_recovery_does_not_rewrite_original_failure() {
    let facts = transient_failure();
    let result = evaluate_retry_eligibility(&facts);
    assert!(result.recovery_required);
    assert_eq!(result.recovery_status, RecoveryStatus::Complete);
    assert_eq!(result.original_outcome, FactualExecutionOutcome::Failed);
}

#[test]
fn attempt_exhaustion_blocks_retry() {
    let mut facts = transient_failure();
    facts.current_attempt = 3;
    assert_eq!(
        evaluate_retry_eligibility(&facts).eligibility,
        RetryEligibility::Ineligible
    );
}

#[test]
fn stronger_policy_risk_and_budget_blocks_dominate_transience() {
    for index in 0..3 {
        let mut facts = transient_failure();
        match index {
            0 => facts.policy_blocked = true,
            1 => facts.risk_blocked = true,
            _ => facts.budget_blocked = true,
        }
        assert_eq!(
            evaluate_retry_eligibility(&facts).eligibility,
            RetryEligibility::Ineligible
        );
    }
}

#[test]
fn projection_has_no_retry_execution_or_acceptance_authority() {
    let encoded = serde_json::to_string(&evaluate_retry_eligibility(&transient_failure()))
        .expect("serialize");
    for forbidden in [
        "retry_executed",
        "dispatch",
        "failover_executed",
        "AcceptanceDecision",
        "provider_sdk",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
