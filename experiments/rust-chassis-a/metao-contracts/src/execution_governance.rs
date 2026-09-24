use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::sync::Mutex;

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
        let next_wall = self.wall_time_used_s + request.wall_time_s;
        let Some(next_tokens) = self.tokens_used.checked_add(request.tokens) else {
            return false;
        };
        let Some(next_attempts) = self.attempts_used.checked_add(request.attempts) else {
            return false;
        };
        next_money.is_finite()
            && next_wall.is_finite()
            && next_money <= self.money_limit
            && next_tokens <= self.token_limit
            && next_wall <= self.wall_time_limit_s
            && next_attempts <= self.attempt_limit
    }
    pub fn observe_usage(
        &self,
        observed: &ExecutionObservedUsage,
    ) -> Result<ExecutionBudgetObservation, ExecutionGovernanceError> {
        self.validate()?;
        observed.validate()?;
        let money = self.money_used + observed.usage.money;
        let wall = self.wall_time_used_s + observed.usage.wall_time_s;
        if !money.is_finite() || !wall.is_finite() {
            return Err(ExecutionGovernanceError::InvalidUsage);
        }
        let tokens = self
            .tokens_used
            .checked_add(observed.usage.tokens)
            .ok_or(ExecutionGovernanceError::InvalidUsage)?;
        let attempts = self
            .attempts_used
            .checked_add(observed.usage.attempts)
            .ok_or(ExecutionGovernanceError::InvalidUsage)?;
        Ok(ExecutionBudgetObservation {
            money_observed: money,
            tokens_observed: tokens,
            wall_time_observed_s: wall,
            attempts_observed: attempts,
            over_limit: money > self.money_limit
                || tokens > self.token_limit
                || wall > self.wall_time_limit_s
                || attempts > self.attempt_limit,
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
            Err(ExecutionGovernanceError::InvalidUsage)
        } else {
            Ok(())
        }
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
            reason: "policy denied execution".into(),
        };
    }
    if risk == ExecutionRiskDecision::Stop {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::Block,
            reason: "risk authority stopped execution".into(),
        };
    }
    if !budget.has_pre_runtime_capacity(requested_usage) {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::Block,
            reason: "execution budget cannot cover requested execution".into(),
        };
    }
    if risk == ExecutionRiskDecision::RequireHuman && !applicable_human_approval {
        return ExecutionGateResult {
            decision: ExecutionGateDecision::RequireHuman,
            reason: "risk requires applicable human approval".into(),
        };
    }
    ExecutionGateResult {
        decision: ExecutionGateDecision::Proceed,
        reason: "policy, risk and execution budget permit execution".into(),
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
    now: f64,
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
        && candidate.not_before_epoch == current.not_before_epoch
        && candidate.expires_at_epoch == current.expires_at_epoch
        && candidate.mission_id == context.mission_id
        && candidate.execution_id == context.execution_id
        && candidate.subject_state_id == context.subject_state_id
        && candidate.policy_bundle_id == context.policy_bundle_id
        && candidate.action == context.action
        && candidate.target == context.target
        && candidate.scope == context.scope
        && candidate.not_before_epoch.is_none_or(|v| now >= v)
        && candidate.expires_at_epoch.map_or(true, |v| now <= v)
}
pub fn project_retry_governance(
    policy: ExecutionPolicyEffect,
    risk: ExecutionRiskDecision,
    budget: &ExecutionBudget,
    requested: &ExecutionUsage,
    candidate: Option<&crate::ApprovalAuthorityTicket>,
    port: &dyn crate::ApprovalAuthorityPort,
    ctx: &RetryApprovalContext,
    now: f64,
) -> RetryGovernanceProjection {
    let policy_denied = policy == ExecutionPolicyEffect::Deny;
    let risk_stopped = risk == ExecutionRiskDecision::Stop;
    let budget_blocked = !budget.has_pre_runtime_capacity(requested);
    let human_approval_required = risk == ExecutionRiskDecision::RequireHuman;
    let human_approval_satisfied = human_approval_required
        && candidate.is_some_and(|c| {
            port.current(&c.approval_id)
                .as_ref()
                .is_some_and(|cur| approval_ticket_matches(c, cur, ctx, now))
        });
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
    g: &RetryGovernanceProjection,
) -> Result<crate::failure_causality::FailureCausalityFacts, RetryGovernanceBridgeError> {
    if g.decision == ExecutionGateDecision::RequireHuman {
        return Err(RetryGovernanceBridgeError::HumanApprovalRequired);
    }
    let mut b = facts.clone();
    b.policy_blocked |= g.policy_denied;
    b.risk_blocked |= g.risk_stopped;
    b.budget_blocked |= g.budget_blocked;
    Ok(b)
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionAccountingOperation {
    pub operation_id: String,
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub execution_lineage_id: String,
    pub observed: ExecutionObservedUsage,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionSettlementDecision {
    Applied,
    Idempotent,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionAccountingError {
    InvalidOperation,
    InvalidObservedUsage,
    Conflict,
    StaleVersion,
    ArithmeticOverflow,
    CapacityExceeded,
    ReservationNotFound,
    ReservationInactive,
    ReservationBindingMismatch,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReservationStatus {
    Active,
    Released,
    Settled,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionBudgetReservation {
    pub reservation_id: String,
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub action: String,
    pub requested: ExecutionUsage,
    pub status: ReservationStatus,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReservationDecision {
    Reserved,
    Idempotent,
    Released,
    AlreadyReleased,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ExecutionAccountingSnapshot {
    pub version: u64,
    pub budget: ExecutionBudget,
    pub settlement_count: usize,
    pub active_reservation_count: usize,
    pub reserved: ExecutionUsage,
}
struct ExecutionAccountingState {
    version: u64,
    budget: ExecutionBudget,
    settlements: BTreeMap<String, ExecutionAccountingOperation>,
    reservations: BTreeMap<String, ExecutionBudgetReservation>,
}
pub struct ExecutionAccountingAuthority {
    state: Mutex<ExecutionAccountingState>,
}

fn zero_usage() -> ExecutionUsage {
    ExecutionUsage {
        money: 0.0,
        tokens: 0,
        wall_time_s: 0.0,
        attempts: 0,
    }
}
fn add_usage(
    a: &ExecutionUsage,
    b: &ExecutionUsage,
) -> Result<ExecutionUsage, ExecutionAccountingError> {
    let money = a.money + b.money;
    let wall = a.wall_time_s + b.wall_time_s;
    if !money.is_finite() || !wall.is_finite() {
        return Err(ExecutionAccountingError::ArithmeticOverflow);
    }
    Ok(ExecutionUsage {
        money,
        tokens: a
            .tokens
            .checked_add(b.tokens)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?,
        wall_time_s: wall,
        attempts: a
            .attempts
            .checked_add(b.attempts)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?,
    })
}
fn active_reserved(
    s: &ExecutionAccountingState,
) -> Result<ExecutionUsage, ExecutionAccountingError> {
    let mut total = zero_usage();
    for r in s
        .reservations
        .values()
        .filter(|r| r.status == ReservationStatus::Active)
    {
        total = add_usage(&total, &r.requested)?;
    }
    Ok(total)
}
fn capacity_with_reserved(
    s: &ExecutionAccountingState,
    request: &ExecutionUsage,
) -> Result<bool, ExecutionAccountingError> {
    request
        .validate()
        .map_err(|_| ExecutionAccountingError::InvalidObservedUsage)?;
    if !s.budget.money_limit.is_finite() || !s.budget.wall_time_limit_s.is_finite() {
        return Ok(false);
    }
    let reserved = active_reserved(s)?;
    let combined = add_usage(&reserved, request)?;
    let money = s.budget.money_used + combined.money;
    let wall = s.budget.wall_time_used_s + combined.wall_time_s;
    let tokens = s
        .budget
        .tokens_used
        .checked_add(combined.tokens)
        .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
    let attempts = s
        .budget
        .attempts_used
        .checked_add(combined.attempts)
        .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
    Ok(money.is_finite()
        && wall.is_finite()
        && money <= s.budget.money_limit
        && tokens <= s.budget.token_limit
        && wall <= s.budget.wall_time_limit_s
        && attempts <= s.budget.attempt_limit)
}
impl ExecutionAccountingAuthority {
    pub fn new(budget: ExecutionBudget) -> Result<Self, ExecutionAccountingError> {
        budget
            .validate()
            .map_err(|_| ExecutionAccountingError::InvalidObservedUsage)?;
        Ok(Self {
            state: Mutex::new(ExecutionAccountingState {
                version: 1,
                budget,
                settlements: BTreeMap::new(),
                reservations: BTreeMap::new(),
            }),
        })
    }
    pub fn snapshot(&self) -> ExecutionAccountingSnapshot {
        let s = self
            .state
            .lock()
            .expect("execution accounting mutex poisoned");
        let reserved = active_reserved(&s).unwrap_or_else(|_| zero_usage());
        ExecutionAccountingSnapshot {
            version: s.version,
            budget: s.budget.clone(),
            settlement_count: s.settlements.len(),
            active_reservation_count: s
                .reservations
                .values()
                .filter(|r| r.status == ReservationStatus::Active)
                .count(),
            reserved,
        }
    }
    pub fn reserve(
        &self,
        expected_version: u64,
        mut reservation: ExecutionBudgetReservation,
    ) -> Result<ReservationDecision, ExecutionAccountingError> {
        if reservation.reservation_id.trim().is_empty() || reservation.action.trim().is_empty() {
            return Err(ExecutionAccountingError::InvalidOperation);
        }
        reservation
            .requested
            .validate()
            .map_err(|_| ExecutionAccountingError::InvalidObservedUsage)?;
        reservation.status = ReservationStatus::Active;
        let mut s = self
            .state
            .lock()
            .expect("execution accounting mutex poisoned");
        if let Some(existing) = s.reservations.get(&reservation.reservation_id) {
            let mut normalized = existing.clone();
            normalized.status = ReservationStatus::Active;
            return if normalized == reservation && existing.status == ReservationStatus::Active {
                Ok(ReservationDecision::Idempotent)
            } else {
                Err(ExecutionAccountingError::Conflict)
            };
        }
        if expected_version != s.version {
            return Err(ExecutionAccountingError::StaleVersion);
        }
        if !capacity_with_reserved(&s, &reservation.requested)? {
            return Err(ExecutionAccountingError::CapacityExceeded);
        }
        s.reservations
            .insert(reservation.reservation_id.clone(), reservation);
        s.version = s
            .version
            .checked_add(1)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
        Ok(ReservationDecision::Reserved)
    }
    pub fn release(
        &self,
        expected_version: u64,
        reservation_id: &str,
    ) -> Result<ReservationDecision, ExecutionAccountingError> {
        let mut s = self
            .state
            .lock()
            .expect("execution accounting mutex poisoned");
        let status = s
            .reservations
            .get(reservation_id)
            .map(|r| r.status)
            .ok_or(ExecutionAccountingError::ReservationNotFound)?;
        if status == ReservationStatus::Released {
            return Ok(ReservationDecision::AlreadyReleased);
        }
        if status == ReservationStatus::Settled {
            return Err(ExecutionAccountingError::ReservationInactive);
        }
        if expected_version != s.version {
            return Err(ExecutionAccountingError::StaleVersion);
        }
        s.reservations
            .get_mut(reservation_id)
            .expect("reservation exists")
            .status = ReservationStatus::Released;
        s.version = s
            .version
            .checked_add(1)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
        Ok(ReservationDecision::Released)
    }
    pub fn settle(
        &self,
        expected_version: u64,
        op: ExecutionAccountingOperation,
    ) -> Result<ExecutionSettlementDecision, ExecutionAccountingError> {
        self.settle_inner(expected_version, None, op)
    }
    pub fn settle_reserved(
        &self,
        expected_version: u64,
        reservation_id: &str,
        op: ExecutionAccountingOperation,
    ) -> Result<ExecutionSettlementDecision, ExecutionAccountingError> {
        self.settle_inner(expected_version, Some(reservation_id), op)
    }
    fn settle_inner(
        &self,
        expected_version: u64,
        reservation_id: Option<&str>,
        op: ExecutionAccountingOperation,
    ) -> Result<ExecutionSettlementDecision, ExecutionAccountingError> {
        if op.operation_id.trim().is_empty() || op.execution_lineage_id.trim().is_empty() {
            return Err(ExecutionAccountingError::InvalidOperation);
        }
        op.observed
            .validate()
            .map_err(|_| ExecutionAccountingError::InvalidObservedUsage)?;
        let mut s = self
            .state
            .lock()
            .expect("execution accounting mutex poisoned");
        if let Some(existing) = s.settlements.get(&op.operation_id) {
            return if existing == &op {
                Ok(ExecutionSettlementDecision::Idempotent)
            } else {
                Err(ExecutionAccountingError::Conflict)
            };
        }
        if expected_version != s.version {
            return Err(ExecutionAccountingError::StaleVersion);
        }
        if let Some(id) = reservation_id {
            let r = s
                .reservations
                .get(id)
                .ok_or(ExecutionAccountingError::ReservationNotFound)?;
            if r.status != ReservationStatus::Active {
                return Err(ExecutionAccountingError::ReservationInactive);
            }
            if r.mission_id != op.mission_id || r.execution_id != op.execution_id {
                return Err(ExecutionAccountingError::ReservationBindingMismatch);
            }
        }
        let money = s.budget.money_used + op.observed.usage.money;
        let wall = s.budget.wall_time_used_s + op.observed.usage.wall_time_s;
        if !money.is_finite() || !wall.is_finite() {
            return Err(ExecutionAccountingError::ArithmeticOverflow);
        }
        let tokens = s
            .budget
            .tokens_used
            .checked_add(op.observed.usage.tokens)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
        let attempts = s
            .budget
            .attempts_used
            .checked_add(op.observed.usage.attempts)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
        s.budget.money_used = money;
        s.budget.tokens_used = tokens;
        s.budget.wall_time_used_s = wall;
        s.budget.attempts_used = attempts;
        if let Some(id) = reservation_id {
            s.reservations
                .get_mut(id)
                .expect("reservation exists")
                .status = ReservationStatus::Settled;
        }
        s.settlements.insert(op.operation_id.clone(), op);
        s.version = s
            .version
            .checked_add(1)
            .ok_or(ExecutionAccountingError::ArithmeticOverflow)?;
        Ok(ExecutionSettlementDecision::Applied)
    }
}
