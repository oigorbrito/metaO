use metao_contracts::failure_causality::{
    bind_execution_retry_authority, evaluate_retry_eligibility, ExecutionRetryAttemptClaim,
    ExecutionRetryAuthorityError, ExecutionRetryAuthorityState, FactualExecutionOutcome,
    FailureCausalityFacts, FailureClass, FailureClassificationBasis, RecoveryStatus,
    RetryEligibility,
};
use metao_contracts::{ExecutionId, MissionId};

fn mission() -> MissionId {
    MissionId::new("mission-475").unwrap()
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-475").unwrap()
}

fn authoritative(current_attempt: u64, max_attempts: u64) -> ExecutionRetryAuthorityState {
    ExecutionRetryAuthorityState {
        mission_id: mission(),
        execution_id: execution(),
        retry_lineage_id: "retry-lineage-475".into(),
        current_attempt,
        max_attempts,
        state_version: 7,
        evidence_ref: "event-ledger://execution-retry/475/7".into(),
    }
}

fn claim(current_attempt: u64, max_attempts: u64) -> ExecutionRetryAttemptClaim {
    ExecutionRetryAttemptClaim {
        mission_id: mission(),
        execution_id: execution(),
        retry_lineage_id: "retry-lineage-475".into(),
        current_attempt,
        max_attempts,
    }
}

fn facts(current_attempt: u64, max_attempts: u64) -> FailureCausalityFacts {
    FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("evidence://failure/transient".into()),
        recovery_required: false,
        recovery_status: RecoveryStatus::NotRequired,
        current_attempt,
        max_attempts,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    }
}

#[test]
fn canonical_execution_retry_state_binds_retry_counters() {
    let bound = bind_execution_retry_authority(&facts(2, 4), &claim(2, 4), &authoritative(2, 4))
        .expect("canonical retry state should bind");

    assert_eq!(bound.current_attempt, 2);
    assert_eq!(bound.max_attempts, 4);
    let projection = evaluate_retry_eligibility(&bound);
    assert_eq!(projection.eligibility, RetryEligibility::Eligible);
    assert_eq!(projection.next_attempt, Some(3));
}

#[test]
fn forged_lower_current_attempt_is_rejected() {
    let error = bind_execution_retry_authority(&facts(1, 4), &claim(1, 4), &authoritative(2, 4))
        .expect_err("caller must not reopen retry by lowering attempt state");
    assert_eq!(error, ExecutionRetryAuthorityError::AttemptStateMismatch);
}

#[test]
fn forged_larger_max_attempts_is_rejected() {
    let error = bind_execution_retry_authority(&facts(2, 9), &claim(2, 9), &authoritative(2, 4))
        .expect_err("caller must not expand retry budget");
    assert_eq!(error, ExecutionRetryAuthorityError::AttemptStateMismatch);
}

#[test]
fn omitted_or_invalid_authoritative_state_fails_closed() {
    let mut state = authoritative(2, 4);
    state.evidence_ref = "   ".into();
    let error = bind_execution_retry_authority(&facts(2, 4), &claim(2, 4), &state)
        .expect_err("invalid authority evidence must fail closed");
    assert_eq!(
        error,
        ExecutionRetryAuthorityError::InvalidAuthoritativeState
    );
}

#[test]
fn retry_lineage_binding_mismatch_fails_closed() {
    let mut caller = claim(2, 4);
    caller.retry_lineage_id = "other-lineage".into();
    let error = bind_execution_retry_authority(&facts(2, 4), &caller, &authoritative(2, 4))
        .expect_err("wrong retry lineage must fail closed");
    assert_eq!(error, ExecutionRetryAuthorityError::BindingMismatch);
}

#[test]
fn mission_or_execution_binding_mismatch_fails_closed() {
    let mut caller = claim(2, 4);
    caller.execution_id = ExecutionId::new("other-execution").unwrap();
    let error = bind_execution_retry_authority(&facts(2, 4), &caller, &authoritative(2, 4))
        .expect_err("wrong execution binding must fail closed");
    assert_eq!(error, ExecutionRetryAuthorityError::BindingMismatch);
}

#[test]
fn exhausted_authoritative_retry_state_cannot_be_reopened() {
    let bound = bind_execution_retry_authority(&facts(4, 4), &claim(4, 4), &authoritative(4, 4))
        .expect("matching exhausted state is factual");
    let projection = evaluate_retry_eligibility(&bound);
    assert_eq!(projection.eligibility, RetryEligibility::Ineligible);
    assert_eq!(projection.next_attempt, None);
}

#[test]
fn verification_attempt_identity_is_not_part_of_execution_retry_authority() {
    let serialized = serde_json::to_value(authoritative(2, 4)).unwrap();
    assert!(serialized.get("retry_lineage_id").is_some());
    assert!(serialized.get("verification_attempt_id").is_none());
    assert!(serialized.get("attempt_id").is_none());
}
