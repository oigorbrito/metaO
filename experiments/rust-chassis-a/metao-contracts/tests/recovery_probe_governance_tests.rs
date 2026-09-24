use metao_contracts::execution_governance::{
    ExecutionAccountingAuthority, ExecutionBudget, ExecutionBudgetReservation,
    ExecutionGateDecision, ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionUsage,
    ReservationStatus,
};
use metao_contracts::runtime_health::{
    bind_recovery_probe_intent, project_recovery_probe_governance, RecoveryProbeApprovalContext,
    RecoveryProbeIntentAuthority, RecoveryProbeIntentClaim,
};
use metao_contracts::{ApprovalAuthorityPort, ApprovalAuthorityTicket, ExecutionId, MissionId};

#[derive(Clone)]
struct ApprovalPort {
    ticket: Option<ApprovalAuthorityTicket>,
}
impl ApprovalAuthorityPort for ApprovalPort {
    fn current(&self, id: &str) -> Option<ApprovalAuthorityTicket> {
        self.ticket
            .as_ref()
            .filter(|t| t.approval_id == id)
            .cloned()
    }
}
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
fn intent_authority() -> RecoveryProbeIntentAuthority {
    RecoveryProbeIntentAuthority {
        intent_id: "probe-478".into(),
        mission_id: MissionId::new("m478").unwrap(),
        execution_id: ExecutionId::new("probe-exec-478").unwrap(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0.0".into(),
        config_id: "config-a".into(),
        authority_generation: 4,
        fencing_token: 44,
        evidence_ref: "authority://probe/478".into(),
    }
}
#[allow(dead_code)]
fn intent() {}
fn bound_intent() -> metao_contracts::runtime_health::BoundRecoveryProbeIntent {
    let a = intent_authority();
    let c = RecoveryProbeIntentClaim {
        intent_id: a.intent_id.clone(),
        mission_id: a.mission_id.clone(),
        execution_id: a.execution_id.clone(),
        runtime_id: a.runtime_id.clone(),
        runtime_version: a.runtime_version.clone(),
        config_id: a.config_id.clone(),
        authority_generation: a.authority_generation,
        fencing_token: a.fencing_token,
    };
    bind_recovery_probe_intent(&c, &a, 4, 44).unwrap()
}
fn ctx() -> RecoveryProbeApprovalContext {
    RecoveryProbeApprovalContext {
        mission_id: MissionId::new("m478").unwrap(),
        execution_id: ExecutionId::new("probe-exec-478").unwrap(),
        subject_state_id: "subject-478".into(),
        policy_bundle_id: "policy-478".into(),
        action: "recovery_probe".into(),
        target: "runtime-a".into(),
        scope: "controlled-recovery".into(),
    }
}
fn usage() -> ExecutionUsage {
    ExecutionUsage {
        money: 1.0,
        tokens: 100,
        wall_time_s: 10.0,
        attempts: 1,
    }
}
fn approval() -> ApprovalAuthorityTicket {
    ApprovalAuthorityTicket {
        approval_id: "approval-478".into(),
        mission_id: MissionId::new("m478").unwrap(),
        execution_id: ExecutionId::new("probe-exec-478").unwrap(),
        subject_state_id: "subject-478".into(),
        policy_bundle_id: "policy-478".into(),
        approver_id: "human".into(),
        capability_id: "approve-probe".into(),
        action: "recovery_probe".into(),
        target: "runtime-a".into(),
        scope: "controlled-recovery".into(),
        authority_epoch: 3,
        not_before_epoch: Some(100.0),
        expires_at_epoch: Some(200.0),
        revoked: false,
    }
}

#[test]
fn policy_deny_blocks_probe() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &a,
        &usage(),
        None,
        &ApprovalPort { ticket: None },
        &ctx(),
        150.0,
    )
    .unwrap();
    assert!(p.policy_denied);
    assert_eq!(p.decision, ExecutionGateDecision::Block);
}
#[test]
fn risk_stop_blocks_probe() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Stop,
        &a,
        &usage(),
        None,
        &ApprovalPort { ticket: None },
        &ctx(),
        150.0,
    )
    .unwrap();
    assert!(p.risk_stopped);
    assert_eq!(p.decision, ExecutionGateDecision::Block);
}
#[test]
fn require_human_needs_probe_specific_approval() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let mut wrong = approval();
    wrong.action = "retry_execution".into();
    let port = ApprovalPort {
        ticket: Some(approval()),
    };
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &a,
        &usage(),
        Some(&wrong),
        &port,
        &ctx(),
        150.0,
    )
    .unwrap();
    assert!(!p.human_approval_satisfied);
    assert_eq!(p.decision, ExecutionGateDecision::RequireHuman);
}
#[test]
fn exact_probe_approval_can_proceed_to_separate_reservation() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let ticket = approval();
    let port = ApprovalPort {
        ticket: Some(ticket.clone()),
    };
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::RequireHuman,
        &a,
        &usage(),
        Some(&ticket),
        &port,
        &ctx(),
        150.0,
    )
    .unwrap();
    assert_eq!(p.decision, ExecutionGateDecision::Proceed);
    assert!(p.human_approval_satisfied);
    let r = ExecutionBudgetReservation {
        reservation_id: "probe-res-478".into(),
        mission_id: MissionId::new("m478").unwrap(),
        execution_id: ExecutionId::new("probe-exec-478").unwrap(),
        action: "recovery_probe".into(),
        requested: usage(),
        status: ReservationStatus::Active,
    };
    assert!(a.reserve(p.budget_version, r).is_ok());
}
#[test]
fn active_reservation_is_counted_by_probe_governance() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let snap = a.snapshot();
    let blocker = ExecutionBudgetReservation {
        reservation_id: "other".into(),
        mission_id: MissionId::new("m-other").unwrap(),
        execution_id: ExecutionId::new("e-other").unwrap(),
        action: "initial_execution".into(),
        requested: ExecutionUsage {
            money: 0.0,
            tokens: 0,
            wall_time_s: 0.0,
            attempts: 3,
        },
        status: ReservationStatus::Active,
    };
    a.reserve(snap.version, blocker).unwrap();
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &a,
        &usage(),
        None,
        &ApprovalPort { ticket: None },
        &ctx(),
        150.0,
    )
    .unwrap();
    assert!(p.budget_blocked);
    assert_eq!(p.decision, ExecutionGateDecision::Block);
}
#[test]
fn probe_governance_contains_no_retry_lineage_or_acceptance_authority() {
    let a = ExecutionAccountingAuthority::new(budget()).unwrap();
    let p = project_recovery_probe_governance(
        &bound_intent(),
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &a,
        &usage(),
        None,
        &ApprovalPort { ticket: None },
        &ctx(),
        150.0,
    )
    .unwrap();
    let s = serde_json::to_string(&p).unwrap();
    for forbidden in [
        "current_attempt",
        "max_attempts",
        "AcceptanceDecision",
        "dispatch",
    ] {
        assert!(!s.contains(forbidden));
    }
}
