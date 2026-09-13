use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionGovernanceError {
    InvalidBudget,
    InvalidUsage,
    BlankEvidenceRef,
    InvalidEvidenceBasis,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionRiskDecision {
    Allow,
    RequireHuman,
    Stop,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionPolicyEffect {
    Allow,
    Deny,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionUsageEvidenceBasis {
    IndependentObservation,
    AdapterVerified,
    SelfReported,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionBudget {
    pub money_limit: f64,
    pub token_limit: u64,
    pub wall_time_limit_s: f64,
    pub attempt_limit: u64,
    pub money_used: f64,
    pub tokens_used: u64,
    pub wall_time_used_s: f64,
    pub attempts_used: u64,
}

impl ExecutionBudget {
    pub fn validate(&self) -> Result<(), ExecutionGovernanceError> {
        if !self.money_limit.is_finite()
            || !self.wall_time_limit_s.is_finite()
            || !self.money_used.is_finite()
            || !self.wall_time_used_s.is_finite()
            || self.money_limit < 0.0
            || self.wall_time_limit_s < 0.0
            || self.money_used < 0.0
            || self.wall_time_used_s < 0.0
        {
            return Err(ExecutionGovernanceError::InvalidBudget);
        }
        if self.money_used > self.money_limit
            || self.tokens_used > self.token_limit
            || self.wall_time_used_s > self.wall_time_limit_s
            || self.attempts_used > self.attempt_limit
        {
            return Err(ExecutionGovernanceError::InvalidUsage);
        }
        Ok(())
    }

    pub fn has_pre_runtime_capacity(&self, request: &ExecutionUsage) -> bool {
        if self.validate().is_err() || request.validate().is_err() {
            return false;
        }
        let next_money = self.money_used + request.money;
        let next_wall_time = self.wall_time_used_s + request.wall_time_s;
        let Some(next_tokens) = self.tokens_used.checked_add(request.tokens) else {
            return false;
        };
        let Some(next_attempts) = self.attempts_used.checked_add(request.attempts) else {
            return false;
        };
        next_money.is_finite()
            && next_wall_time.is_finite()
            && next_money <= self.money_limit
            && next_tokens <= self.token_limit
            && next_wall_time <= self.wall_time_limit_s
            && next_attempts <= self.attempt_limit
    }

    pub fn observe_usage(
        &self,
        observed: &ExecutionObservedUsage,
    ) -> Result<ExecutionBudgetObservation, ExecutionGovernanceError> {
        self.validate()?;
        observed.validate()?;

        let next_money = self.money_used + observed.usage.money;
        let next_wall_time = self.wall_time_used_s + observed.usage.wall_time_s;
        if !next_money.is_finite() || !next_wall_time.is_finite() {
            return Err(ExecutionGovernanceError::InvalidUsage);
        }
        let next_tokens = self
            .tokens_used
            .checked_add(observed.usage.tokens)
            .ok_or(ExecutionGovernanceError::InvalidUsage)?;
        let next_attempts = self
            .attempts_used
            .checked_add(observed.usage.attempts)
            .ok_or(ExecutionGovernanceError::InvalidUsage)?;

        let over_limit = next_money > self.money_limit
            || next_tokens > self.token_limit
            || next_wall_time > self.wall_time_limit_s
            || next_attempts > self.attempt_limit;

        Ok(ExecutionBudgetObservation {
            money_observed: next_money,
            tokens_observed: next_tokens,
            wall_time_observed_s: next_wall_time,
            attempts_observed: next_attempts,
            over_limit,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionUsage {
    pub money: f64,
    pub tokens: u64,
    pub wall_time_s: f64,
    pub attempts: u64,
}

impl ExecutionUsage {
    pub fn validate(&self) -> Result<(), ExecutionGovernanceError> {
        if !self.money.is_finite()
            || !self.wall_time_s.is_finite()
            || self.money < 0.0
            || self.wall_time_s < 0.0
        {
            return Err(ExecutionGovernanceError::InvalidUsage);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionObservedUsage {
    pub usage: ExecutionUsage,
    pub evidence_basis: ExecutionUsageEvidenceBasis,
    pub evidence_ref: String,
}

impl ExecutionObservedUsage {
    pub fn validate(&self) -> Result<(), ExecutionGovernanceError> {
        self.usage.validate()?;
        if !matches!(
            self.evidence_basis,
            ExecutionUsageEvidenceBasis::IndependentObservation
                | ExecutionUsageEvidenceBasis::AdapterVerified
        ) {
            return Err(ExecutionGovernanceError::InvalidEvidenceBasis);
        }
        if self.evidence_ref.trim().is_empty() {
            return Err(ExecutionGovernanceError::BlankEvidenceRef);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionBudgetObservation {
    pub money_observed: f64,
    pub tokens_observed: u64,
    pub wall_time_observed_s: f64,
    pub attempts_observed: u64,
    pub over_limit: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionGateDecision {
    Proceed,
    RequireHuman,
    Block,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionGateResult {
    pub decision: ExecutionGateDecision,
    pub reason: String,
}

pub fn evaluate_pre_runtime_gate(
    policy: ExecutionPolicyEffect,
    risk: ExecutionRiskDecision,
    budget: &ExecutionBudget,
    requested_usage: &ExecutionUsage,
    applicable_human_approval: bool,
) -> ExecutionGateResult {
    if policy == ExecutionPolicyEffect::Deny {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::Block,
            reason: "policy denied execution".to_string(),
        };
    }
    if risk == ExecutionRiskDecision::Stop {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::Block,
            reason: "risk authority stopped execution".to_string(),
        };
    }
    if !budget.has_pre_runtime_capacity(requested_usage) {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::Block,
            reason: "execution budget cannot cover requested execution".to_string(),
        };
    }
    if risk == ExecutionRiskDecision::RequireHuman && !applicable_human_approval {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::RequireHuman,
            reason: "risk requires applicable human approval".to_string(),
        };
    }
    ExecutionGateResult {
        decision: ExecutionGateDecision::Proceed,
        reason: "policy, risk and execution budget permit execution".to_string(),
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RetryApprovalContext {
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub subject_state_id: String,
    pub policy_bundle_id: String,
    pub action: String,
    pub target: String,
    pub scope: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RetryGovernanceProjection {
    pub policy_denied: bool,
    pub risk_stopped: bool,
    pub budget_blocked: bool,
    pub human_approval_required: bool,
    pub human_approval_satisfied: bool,
    pub decision: ExecutionGateDecision,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RetryGovernanceBridgeError {
    HumanApprovalRequired,
}

fn approval_ticket_matches(
    candidate: &crate::ApprovalAuthorityTicket,
    current: &crate::ApprovalAuthorityTicket,
    context: &RetryApprovalContext,
    now_epoch: f64,
) -> bool {
    !candidate.revoked
        && !current.revoked
        && candidate.approval_id == current.approval_id
        && candidate.mission_id == current.mission_id
        && candidate.execution_id == current.execution_id
        && candidate.subject_state_id == current.subject_state_id
        && candidate.policy_bundle_id == current.policy_bundle_id
        && candidate.approver_id == current.approver_id
        && candidate.capability_id == current.capability_id
        && candidate.action == current.action
        && candidate.target == current.target
        && candidate.scope == current.scope
        && candidate.authority_epoch == current.authority_epoch
        && candidate.mission_id == context.mission_id
        && candidate.execution_id == context.execution_id
        && candidate.subject_state_id == context.subject_state_id
        && candidate.policy_bundle_id == context.policy_bundle_id
        && candidate.action == context.action
        && candidate.target == context.target
        && candidate.scope == context.scope
        && candidate
            .not_before_epoch
            .is_none_or(|not_before| now_epoch >= not_before)
        && current
            .not_before_epoch
            .is_none_or(|not_before| now_epoch >= not_before)
        && candidate
            .expires_at_epoch
            .is_none_or(|expires| now_epoch <= expires)
        && current
            .expires_at_epoch
            .is_none_or(|expires| now_epoch <= expires)
}

pub fn project_retry_governance(
    policy: ExecutionPolicyEffect,
    risk: ExecutionRiskDecision,
    budget: &ExecutionBudget,
    requested_usage: &ExecutionUsage,
    candidate_approval: Option<&crate::ApprovalAuthorityTicket>,
    approval_port: &dyn crate::ApprovalAuthorityPort,
    approval_context: &RetryApprovalContext,
    now_epoch: f64,
) -> RetryGovernanceProjection {
    let policy_denied = policy == ExecutionPolicyEffect::Deny;
    let risk_stopped = risk == ExecutionRiskDecision::Stop;
    let budget_blocked = !budget.has_pre_runtime_capacity(requested_usage);
    let human_approval_required = risk == ExecutionRiskDecision::RequireHuman;
    let human_approval_satisfied = if human_approval_required {
        candidate_approval.is_some_and(|candidate| {
            approval_port
                .current(&candidate.approval_id)
                .as_ref()
                .is_some_and(|current| {
                    approval_ticket_matches(candidate, current, approval_context, now_epoch)
                })
        })
    } else {
        false
    };

    let decision = if policy_denied || risk_stopped || budget_blocked {
        ExecutionGateDecision::Block
    } else if human_approval_required && !human_approval_satisfied {
        ExecutionGateDecision::RequireHuman
    } else {
        ExecutionGateDecision::Proceed
    };

    RetryGovernanceProjection {
        policy_denied,
        risk_stopped,
        budget_blocked,
        human_approval_required,
        human_approval_satisfied,
        decision,
    }
}

pub fn bind_retry_governance(
    facts: &crate::failure_causality::FailureCausalityFacts,
    governance: &RetryGovernanceProjection,
) -> Result<crate::failure_causality::FailureCausalityFacts, RetryGovernanceBridgeError> {
    if governance.decision == ExecutionGateDecision::RequireHuman {
        return Err(RetryGovernanceBridgeError::HumanApprovalRequired);
    }

    let mut bound = facts.clone();
    bound.policy_blocked = bound.policy_blocked || governance.policy_denied;
    bound.risk_blocked = bound.risk_blocked || governance.risk_stopped;
    bound.budget_blocked = bound.budget_blocked || governance.budget_blocked;
    Ok(bound)
}
