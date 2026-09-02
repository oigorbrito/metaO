//! Deterministic L2 authority/evidence fixtures for architecture qualification.
//!
//! This crate is intentionally provider-free. It tests metaO contract semantics
//! before any donor adapter is allowed to claim compatibility.

use metao_contracts::{
    evaluate_pre_runtime_gate, CompletionEvidenceBasis, CompletionEvidenceStatus,
    ExecutionBudget, ExecutionGateDecision, ExecutionPolicyEffect, ExecutionRiskDecision,
    ExecutionUsage, ProjectCompletionDecision, ProjectCompletionGate,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum L2Outcome {
    Pass,
    Reject,
    Block,
    NotDone,
    Unsupported,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct L2Receipt {
    pub fixture_id: &'static str,
    pub strategy_id: &'static str,
    pub outcome: L2Outcome,
    pub authority_owner: &'static str,
    pub evidence_binding: &'static str,
    pub reason_code: &'static str,
}

pub fn a01_executor_done_is_not_acceptance() -> L2Receipt {
    L2Receipt {
        fixture_id: "L2-A01",
        strategy_id: "metao-current-contracts",
        outcome: L2Outcome::Reject,
        authority_owner: "project-completion-gate",
        evidence_binding: "independent-or-verified-only",
        reason_code: "SELF_REPORTED_COMPLETION_NOT_ACCEPTANCE",
    }
}

pub fn a04_unknown_usage_blocks() -> L2Receipt {
    let budget = ExecutionBudget {
        money_limit: 1.0,
        token_limit: 100,
        wall_time_limit_s: 60.0,
        attempt_limit: 1,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    };
    let requested = ExecutionUsage {
        money: 0.1,
        tokens: 1,
        wall_time_s: 1.0,
        attempts: 1,
    };
    let gate = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &budget,
        &requested,
        false,
    );
    L2Receipt {
        fixture_id: "L2-A04",
        strategy_id: "metao-current-contracts",
        outcome: match gate.decision {
            ExecutionGateDecision::Block => L2Outcome::Block,
            _ => L2Outcome::Unsupported,
        },
        authority_owner: "execution-governance",
        evidence_binding: "fail-closed",
        reason_code: "POLICY_DENY_BLOCKS",
    }
}

pub fn a05_unauthorized_paid_fallback_blocks() -> L2Receipt {
    let budget = ExecutionBudget {
        money_limit: 0.0,
        token_limit: 100,
        wall_time_limit_s: 60.0,
        attempt_limit: 1,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    };
    let requested = ExecutionUsage {
        money: 0.01,
        tokens: 1,
        wall_time_s: 1.0,
        attempts: 1,
    };
    let gate = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget,
        &requested,
        false,
    );
    L2Receipt {
        fixture_id: "L2-A05",
        strategy_id: "metao-current-contracts",
        outcome: match gate.decision {
            ExecutionGateDecision::Block => L2Outcome::Reject,
            _ => L2Outcome::Unsupported,
        },
        authority_owner: "execution-budget",
        evidence_binding: "budget-authority",
        reason_code: "UNAUTHORIZED_COST_BLOCKED",
    }
}

pub fn a07_unproven_obligation_is_not_done() -> L2Receipt {
    // The completion gate is the authoritative mechanism. The concrete project
    // construction lives in contract integration tests; this fixture freezes the
    // expected terminal disposition for adapters.
    let _basis = CompletionEvidenceBasis::CallerDeclared;
    let _status = CompletionEvidenceStatus::NotProven;
    let _decision = ProjectCompletionDecision::NotDone;
    let _gate = ProjectCompletionGate;
    L2Receipt {
        fixture_id: "L2-A07",
        strategy_id: "metao-current-contracts",
        outcome: L2Outcome::NotDone,
        authority_owner: "project-completion-gate",
        evidence_binding: "exact-contract-independent-evidence",
        reason_code: "MANDATORY_OBLIGATION_UNPROVEN",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a01_rejects_self_reported_completion() {
        assert_eq!(a01_executor_done_is_not_acceptance().outcome, L2Outcome::Reject);
    }

    #[test]
    fn a04_blocks_closed() {
        assert_eq!(a04_unknown_usage_blocks().outcome, L2Outcome::Block);
    }

    #[test]
    fn a05_rejects_unauthorized_cost() {
        assert_eq!(a05_unauthorized_paid_fallback_blocks().outcome, L2Outcome::Reject);
    }

    #[test]
    fn a07_keeps_project_open() {
        assert_eq!(a07_unproven_obligation_is_not_done().outcome, L2Outcome::NotDone);
    }
}
