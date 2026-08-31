use metao_contracts::execution_governance::{
    evaluate_pre_runtime_gate, ExecutionBudget, ExecutionGateDecision, ExecutionObservedUsage,
    ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionUsage, ExecutionUsageEvidenceBasis,
};
use metao_contracts::execution_stage_evidence::{
    project_execution_stages, ExecutionStageEvidence, ExecutionStageEvidenceBasis,
    ExecutionStageStatus,
};
use metao_contracts::failure_causality::{
    evaluate_retry_eligibility, FactualExecutionOutcome, FailureCausalityFacts, FailureClass,
    FailureClassificationBasis, RecoveryStatus, RetryEligibility,
};
use metao_contracts::runtime_health::{
    derive_runtime_health, RuntimeHealthEvidenceBasis, RuntimeHealthObservation,
    RuntimeHealthPolicy, RuntimeHealthState,
};

fn budget() -> ExecutionBudget {
    ExecutionBudget {
        money_limit: 10.0,
        token_limit: 1000,
        wall_time_limit_s: 100.0,
        attempt_limit: 3,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    }
}

fn usage() -> ExecutionUsage {
    ExecutionUsage {
        money: 1.0,
        tokens: 10,
        wall_time_s: 1.0,
        attempts: 1,
    }
}

#[test]
fn governed_execution_composes_policy_risk_budget_health_failure_and_stage_evidence() {
    let allow = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &usage(),
        true,
    );
    assert_eq!(allow.decision, ExecutionGateDecision::Proceed);

    let deny = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &budget(),
        &usage(),
        true,
    );
    assert_eq!(deny.decision, ExecutionGateDecision::Block);

    let stop = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Stop,
        &budget(),
        &usage(),
        true,
    );
    assert_eq!(stop.decision, ExecutionGateDecision::Block);

    let no_approval = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &usage(),
        false,
    );
    assert_eq!(no_approval.decision, ExecutionGateDecision::RequireHuman);

    let with_approval = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &budget(),
        &usage(),
        true,
    );
    assert_eq!(with_approval.decision, ExecutionGateDecision::Proceed);

    let exhausted_budget = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &ExecutionBudget {
            money_limit: 0.0,
            token_limit: 0,
            wall_time_limit_s: 0.0,
            attempt_limit: 0,
            money_used: 0.0,
            tokens_used: 0,
            wall_time_used_s: 0.0,
            attempts_used: 0,
        },
        &usage(),
        true,
    );
    assert_eq!(exhausted_budget.decision, ExecutionGateDecision::Block);

    let observation = RuntimeHealthObservation {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "config-a".into(),
        evidence_basis: RuntimeHealthEvidenceBasis::IndependentObservation,
        evidence_ref: "health-evidence-1".into(),
        window_start_sequence: 1,
        window_end_sequence: 4,
        attempts: 4,
        successes: 3,
        failures: 1,
        consecutive_failures: 1,
        timeouts: 0,
        transport_failures: 0,
        active_retries: 0,
        fresh_successes_since_unhealthy: 0,
        prior_state: Some(RuntimeHealthState::Healthy),
        self_reported_healthy: Some(true),
    };
    let projection = derive_runtime_health(
        &observation,
        &RuntimeHealthPolicy {
            quarantine_consecutive_failures: 3,
            unhealthy_failure_percent: 75,
            recovery_successes_required: 2,
            retry_pressure_limit: 2,
        },
    )
    .expect("health projection");
    assert_eq!(projection.state, RuntimeHealthState::Degraded);
    assert!(projection
        .reasons
        .iter()
        .any(|reason| reason.contains("self-report healthy=true did not override")));

    let stage_report = project_execution_stages(&[
        ExecutionStageEvidence {
            stage_id: "dispatch".into(),
            sequence: 1,
            requested: true,
            executed: true,
            status: ExecutionStageStatus::Pass,
            reason: "dispatch observed".into(),
            evidence_basis: ExecutionStageEvidenceBasis::IndependentObservation,
            evidence_ref: Some("stage-evidence-1".into()),
        },
        ExecutionStageEvidence {
            stage_id: "report".into(),
            sequence: 2,
            requested: true,
            executed: false,
            status: ExecutionStageStatus::Skipped,
            reason: "governance blocked projection".into(),
            evidence_basis: ExecutionStageEvidenceBasis::Unknown,
            evidence_ref: None,
        },
        ExecutionStageEvidence {
            stage_id: "observer".into(),
            sequence: 3,
            requested: false,
            executed: false,
            status: ExecutionStageStatus::NotRequested,
            reason: "telemetry has no authority".into(),
            evidence_basis: ExecutionStageEvidenceBasis::Unknown,
            evidence_ref: None,
        },
    ])
    .expect("stage report");
    assert_eq!(stage_report.passed, 1);
    assert_eq!(stage_report.skipped, 1);
    assert_eq!(stage_report.not_requested, 1);

    let retry = evaluate_retry_eligibility(&FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("retry-evidence-1".into()),
        recovery_required: true,
        recovery_status: RecoveryStatus::Complete,
        current_attempt: 1,
        max_attempts: 3,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    });
    assert_eq!(retry.eligibility, RetryEligibility::Eligible);
    assert_eq!(retry.next_attempt, Some(2));

    let blocked_retry = evaluate_retry_eligibility(&FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Cancelled,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("retry-evidence-2".into()),
        recovery_required: true,
        recovery_status: RecoveryStatus::Complete,
        current_attempt: 1,
        max_attempts: 3,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    });
    assert_eq!(blocked_retry.eligibility, RetryEligibility::Ineligible);

    let usage_observation = ExecutionObservedUsage {
        usage: usage(),
        evidence_basis: ExecutionUsageEvidenceBasis::IndependentObservation,
        evidence_ref: "usage-evidence-1".into(),
    };
    let observed = budget()
        .observe_usage(&usage_observation)
        .expect("observed usage");
    assert!(!observed.over_limit);
    assert_eq!(observed.attempts_observed, 1);
}
