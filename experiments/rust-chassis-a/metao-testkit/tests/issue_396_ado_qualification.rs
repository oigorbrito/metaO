use metao_contracts::execution_stage_evidence::{
    ExecutionStageEvidence, ExecutionStageEvidenceBasis, ExecutionStageEvidenceError,
    ExecutionStageStatus,
};
use metao_contracts::failure_causality::{
    evaluate_retry_eligibility, ExecutionTerminationCause, ExecutionTerminationFact,
    FactualExecutionOutcome, FailureCausalityFacts, FailureClass, FailureClassificationBasis,
    RecoveryStatus, RetryEligibility,
};
use metao_contracts::{
    EvidenceEnvelope, ExecutionId, MissionId, RuntimeId, VerificationAttemptId,
    VerificationAttemptStarted, VerificationRequestId, VerifierId,
};

fn verified_stage(status: ExecutionStageStatus) -> ExecutionStageEvidence {
    ExecutionStageEvidence {
        stage_id: "qualification".to_string(),
        sequence: 1,
        requested: true,
        executed: true,
        status,
        reason: "deterministic qualification fixture".to_string(),
        evidence_basis: ExecutionStageEvidenceBasis::IndependentObservation,
        evidence_ref: Some("evidence://issue-396".to_string()),
    }
}

fn retry_facts(
    outcome: FactualExecutionOutcome,
    current_attempt: u64,
    max_attempts: u64,
) -> FailureCausalityFacts {
    FailureCausalityFacts {
        original_outcome: outcome,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("evidence://failure".to_string()),
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
fn b1_verified_pass_is_well_formed() {
    let stage = verified_stage(ExecutionStageStatus::Pass);
    assert_eq!(stage.validate(), Ok(()));
}

#[test]
fn b2_runner_success_cannot_create_pass_without_required_evidence() {
    let stage = ExecutionStageEvidence {
        stage_id: "qualification".to_string(),
        sequence: 1,
        requested: true,
        executed: true,
        status: ExecutionStageStatus::Pass,
        reason: "runner reported success".to_string(),
        evidence_basis: ExecutionStageEvidenceBasis::SelfReported,
        evidence_ref: None,
    };

    assert_eq!(
        stage.validate(),
        Err(ExecutionStageEvidenceError::InvalidEvidenceBasis)
    );
}

#[test]
fn b3_timeout_is_preserved_and_can_remain_retry_eligible_when_factually_transient() {
    let projection =
        evaluate_retry_eligibility(&retry_facts(FactualExecutionOutcome::Timeout, 1, 3));

    assert_eq!(
        projection.original_outcome,
        FactualExecutionOutcome::Timeout
    );
    assert_eq!(projection.eligibility, RetryEligibility::Eligible);
    assert_eq!(projection.next_attempt, Some(2));
}

#[test]
fn b4_cancellation_is_not_rewritten_as_failure_or_retryable_work() {
    let projection =
        evaluate_retry_eligibility(&retry_facts(FactualExecutionOutcome::Cancelled, 1, 3));

    assert_eq!(
        projection.original_outcome,
        FactualExecutionOutcome::Cancelled
    );
    assert_eq!(projection.eligibility, RetryEligibility::Ineligible);
    assert_eq!(projection.next_attempt, None);
}

#[test]
fn b5_failure_causality_preserves_original_failure() {
    let projection =
        evaluate_retry_eligibility(&retry_facts(FactualExecutionOutcome::Failed, 1, 3));

    assert_eq!(projection.original_outcome, FactualExecutionOutcome::Failed);
}

#[test]
fn b6_attempt_budget_exhaustion_blocks_retry_without_rewriting_outcome() {
    let projection =
        evaluate_retry_eligibility(&retry_facts(FactualExecutionOutcome::Timeout, 3, 3));

    assert_eq!(
        projection.original_outcome,
        FactualExecutionOutcome::Timeout
    );
    assert_eq!(projection.eligibility, RetryEligibility::Ineligible);
    assert_eq!(projection.next_attempt, None);
}

#[test]
fn b7_candidate_distinguishes_criterion_satisfied_from_sampling_budget_exhausted() {
    let criterion_satisfied = ExecutionTerminationFact {
        outcome: FactualExecutionOutcome::Succeeded,
        cause: ExecutionTerminationCause::CriterionSatisfied,
    };
    let sampling_budget_exhausted_target_unsatisfied = ExecutionTerminationFact {
        outcome: FactualExecutionOutcome::Succeeded,
        cause: ExecutionTerminationCause::BudgetExhausted,
    };

    assert_eq!(
        criterion_satisfied.outcome,
        sampling_budget_exhausted_target_unsatisfied.outcome
    );
    assert_ne!(
        criterion_satisfied.cause,
        sampling_budget_exhausted_target_unsatisfied.cause
    );
}

#[test]
fn b8_termination_cause_remains_factual_and_does_not_mint_stage_pass() {
    let termination = ExecutionTerminationFact {
        outcome: FactualExecutionOutcome::Succeeded,
        cause: ExecutionTerminationCause::CriterionSatisfied,
    };
    let invalid_stage = ExecutionStageEvidence {
        stage_id: "qualification".to_string(),
        sequence: 1,
        requested: true,
        executed: true,
        status: ExecutionStageStatus::Pass,
        reason: format!("runner terminated with {:?}", termination.cause),
        evidence_basis: ExecutionStageEvidenceBasis::SelfReported,
        evidence_ref: None,
    };

    assert_eq!(
        invalid_stage.validate(),
        Err(ExecutionStageEvidenceError::InvalidEvidenceBasis)
    );
}

#[test]
fn p1_versioned_verifier_identity_is_recorded_at_attempt_start() {
    let started = VerificationAttemptStarted {
        request_id: VerificationRequestId::new("request-1").unwrap(),
        attempt_id: VerificationAttemptId::new("attempt-1").unwrap(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("execution-1").unwrap(),
        verifier_id: VerifierId::new("verifier-a").unwrap(),
        verifier_version: "1.2.3".to_string(),
        started_at_epoch: 1.0,
    };

    assert_eq!(started.verifier_id.as_str(), "verifier-a");
    assert_eq!(started.verifier_version, "1.2.3");
}

fn envelope(
    adapter_version: &str,
    policy_bundle_id: &str,
    provenance_root: &str,
) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "evidence-1".to_string(),
        obligation_id: "obligation-1".to_string(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("execution-1").unwrap(),
        orchestrator_id: RuntimeId::new("runtime-a").unwrap(),
        adapter_version: adapter_version.to_string(),
        attempt_id: "attempt-1".to_string(),
        subject_id: "subject-1".to_string(),
        subject_state_id: "subject-state-1".to_string(),
        verification_context_id: "verification-context-1".to_string(),
        policy_bundle_id: policy_bundle_id.to_string(),
        verifier_id: "verifier-a".to_string(),
        payload_digest: "sha256:payload".to_string(),
        provenance_root: provenance_root.to_string(),
        authority_id: "authority-1".to_string(),
        passed: true,
        created_at_epoch: 1.0,
        expires_at_epoch: None,
        approval_id: None,
        confidence: None,
    }
}

#[test]
fn p2_adapter_version_drift_is_observable_in_evidence() {
    let before = envelope("1.2.3", "policy-v1", "prov-a");
    let after = envelope("1.2.4", "policy-v1", "prov-a");

    assert_ne!(before.adapter_version, after.adapter_version);
}

#[test]
fn p3_policy_bundle_drift_is_observable_in_evidence() {
    let before = envelope("1.2.3", "policy-v1", "prov-a");
    let after = envelope("1.2.3", "policy-v2", "prov-a");

    assert_ne!(before.policy_bundle_id, after.policy_bundle_id);
}

#[test]
fn p4_provenance_root_is_explicit_but_orchestrator_version_is_not_in_envelope() {
    let evidence = envelope("1.2.3", "policy-v1", "prov-a");
    let serialized = serde_json::to_value(evidence).unwrap();

    assert_eq!(serialized["provenance_root"], "prov-a");
    assert_eq!(serialized["adapter_version"], "1.2.3");
    assert!(serialized.get("orchestrator_version").is_none());
}

#[test]
fn p5_version_lineage_can_be_compared_without_overwriting_prior_record() {
    let first = VerificationAttemptStarted {
        request_id: VerificationRequestId::new("request-1").unwrap(),
        attempt_id: VerificationAttemptId::new("attempt-1").unwrap(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("execution-1").unwrap(),
        verifier_id: VerifierId::new("verifier-a").unwrap(),
        verifier_version: "1.2.3".to_string(),
        started_at_epoch: 1.0,
    };
    let resumed = VerificationAttemptStarted {
        request_id: VerificationRequestId::new("request-2").unwrap(),
        attempt_id: VerificationAttemptId::new("attempt-2").unwrap(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: ExecutionId::new("execution-1").unwrap(),
        verifier_id: VerifierId::new("verifier-a").unwrap(),
        verifier_version: "1.3.0".to_string(),
        started_at_epoch: 2.0,
    };

    assert_eq!(first.verifier_version, "1.2.3");
    assert_eq!(resumed.verifier_version, "1.3.0");
    assert_ne!(first.attempt_id, resumed.attempt_id);
}
