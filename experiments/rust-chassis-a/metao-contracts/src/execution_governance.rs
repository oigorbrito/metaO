use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionGovernanceError {
    InvalidBudget,
    InvalidUsage,
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
        if self.money_limit < 0.0
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
        self.validate().is_ok()
            && request.is_non_negative()
            && self.money_used + request.money <= self.money_limit
            && self.tokens_used.saturating_add(request.tokens) <= self.token_limit
            && self.wall_time_used_s + request.wall_time_s <= self.wall_time_limit_s
            && self.attempts_used.saturating_add(request.attempts) <= self.attempt_limit
    }

    pub fn observe_usage(&self, observed: &ExecutionUsage) -> ExecutionBudgetObservation {
        let next_money = self.money_used + observed.money;
        let next_tokens = self.tokens_used.saturating_add(observed.tokens);
        let next_wall_time = self.wall_time_used_s + observed.wall_time_s;
        let next_attempts = self.attempts_used.saturating_add(observed.attempts);
        let over_limit = observed.is_non_negative()
            && (next_money > self.money_limit
                || next_tokens > self.token_limit
                || next_wall_time > self.wall_time_limit_s
                || next_attempts > self.attempt_limit);

        ExecutionBudgetObservation {
            money_observed: next_money,
            tokens_observed: next_tokens,
            wall_time_observed_s: next_wall_time,
            attempts_observed: next_attempts,
            over_limit,
        }
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
    fn is_non_negative(&self) -> bool {
        self.money >= 0.0 && self.wall_time_s >= 0.0
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
