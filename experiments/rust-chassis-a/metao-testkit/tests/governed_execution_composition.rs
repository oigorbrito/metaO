use metao_contracts::execution_governance::{
    ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionBudget,
    ExecutionUsage, evaluate_pre_runtime_gate, ExecutionGateDecision
};
use metao_contracts::runtime_health::{
    RuntimeHealthObservation, RuntimeHealthStatus
};
use metao_contracts::failure_causality::{
    analyze_failure_causality, RecoveryRequirement
};
use metao_contracts::execution_stage_evidence::{
    ExecutionStageStatus, ExecutionStageReport, analyze_stage_evidence,
    ExecutionStageEvidence
};

#[test]
fn composed_execution_governance_path() {
    let budget = ExecutionBudget {
        money_limit: 10.0,
        token_limit: 1000,
        wall_time_limit_s: 100.0,
        attempt_limit: 3,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    };
    let request = ExecutionUsage {
        money: 1.0,
        tokens: 10,
        wall_time_s: 1.0,
        attempts: 1,
    };

    // 1. Policy & Risk & Budget Admission
    let gate = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget,
        &request,
        true,
    );
    assert_eq!(gate.decision, ExecutionGateDecision::Proceed);

    // 2. Runtime Health
    let health = RuntimeHealthObservation {
        status: RuntimeHealthStatus::Healthy,
        consecutive_failures: 0,
        last_failure_reason: None,
        observed_at: 0.0,
    };
    assert_eq!(health.status, RuntimeHealthStatus::Healthy);

    // 3. Execution stage evidence
    let stage = ExecutionStageEvidence {
        stage_name: "dispatch".into(),
        sequence: 1,
        status: ExecutionStageStatus::Pass,
        reason: None,
    };
    let report = analyze_stage_evidence(&[stage]);
    assert!(report.is_ok());
    
    // We compose everything without making a monolithic framework!
}
