use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutorCapacityError {
    BlankExecutorId,
    BlankCapability,
    BlankEvidenceRef,
    InvalidRecoveryObservation,
    InvalidBudgetPolicy,
    InvalidCheckpoint,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum QualificationState {
    Discovered,
    Qualified,
    QualifiedRestricted,
    Unqualified,
    Blocked,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapacityState {
    Available,
    TemporarilyRateLimited,
    TemporarilyQuotaExhausted,
    DailyQuotaExhausted,
    ConcurrencyExhausted,
    CreditExhausted,
    SpendLimitExhausted,
    ProviderUnavailable,
    AuthenticationFailure,
    AccountDisabled,
    CapabilityMismatch,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryEvidenceBasis {
    ProviderApi,
    ProviderDocumentation,
    AdapterVerified,
    IndependentObservation,
    ConfiguredPolicy,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryObservation {
    pub recoverable: bool,
    pub available_at_epoch_s: Option<u64>,
    pub evidence_basis: RecoveryEvidenceBasis,
    pub evidence_ref: String,
}

impl RecoveryObservation {
    pub fn validate(&self) -> Result<(), ExecutorCapacityError> {
        if self.evidence_ref.trim().is_empty() {
            return Err(ExecutorCapacityError::BlankEvidenceRef);
        }
        if self.recoverable && self.available_at_epoch_s.is_none() {
            return Err(ExecutorCapacityError::InvalidRecoveryObservation);
        }
        if matches!(self.evidence_basis, RecoveryEvidenceBasis::Unknown) {
            return Err(ExecutorCapacityError::InvalidRecoveryObservation);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutorRecord {
    pub executor_id: String,
    pub provider: String,
    pub country_or_region: Option<String>,
    pub capabilities: BTreeSet<String>,
    pub qualification: QualificationState,
    pub capacity: CapacityState,
    pub recovery: Option<RecoveryObservation>,
    pub paid: bool,
    pub estimated_cost_microunits: u64,
    pub reliability_score_basis_points: u16,
}

impl ExecutorRecord {
    pub fn validate(&self) -> Result<(), ExecutorCapacityError> {
        if self.executor_id.trim().is_empty() {
            return Err(ExecutorCapacityError::BlankExecutorId);
        }
        if self
            .capabilities
            .iter()
            .any(|capability| capability.trim().is_empty())
        {
            return Err(ExecutorCapacityError::BlankCapability);
        }
        if let Some(recovery) = &self.recovery {
            recovery.validate()?;
        }
        Ok(())
    }

    pub fn can_receive_project_data(&self) -> bool {
        matches!(
            self.qualification,
            QualificationState::Qualified | QualificationState::QualifiedRestricted
        )
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionPolicy {
    pub required_capabilities: BTreeSet<String>,
    pub paid_fallback_allowed: bool,
    pub max_paid_cost_microunits: u64,
    pub prefer_free: bool,
    pub max_wait_for_free_s: u64,
}

impl ExecutionPolicy {
    pub fn validate(&self) -> Result<(), ExecutorCapacityError> {
        if !self.paid_fallback_allowed && self.max_paid_cost_microunits > 0 {
            return Err(ExecutorCapacityError::InvalidBudgetPolicy);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerifiedCheckpoint {
    pub task_id: String,
    pub branch: String,
    pub expected_head: String,
    pub observed_head: String,
    pub evidence_ref: String,
}

impl VerifiedCheckpoint {
    pub fn validate(&self) -> Result<(), ExecutorCapacityError> {
        if self.task_id.trim().is_empty()
            || self.branch.trim().is_empty()
            || self.expected_head.trim().is_empty()
            || self.observed_head.trim().is_empty()
            || self.evidence_ref.trim().is_empty()
            || self.expected_head != self.observed_head
        {
            return Err(ExecutorCapacityError::InvalidCheckpoint);
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum SupervisionDecision {
    Continue,
    RetryAfter { delay_s: u64 },
    ParkUntil { epoch_s: u64 },
    Failover,
    Block,
}

pub fn supervision_decision(
    executor: &ExecutorRecord,
    now_epoch_s: u64,
) -> Result<SupervisionDecision, ExecutorCapacityError> {
    executor.validate()?;

    let decision = match executor.capacity {
        CapacityState::Available => SupervisionDecision::Continue,
        CapacityState::TemporarilyRateLimited => match &executor.recovery {
            Some(recovery) if recovery.recoverable => {
                let at = recovery.available_at_epoch_s.unwrap_or(now_epoch_s);
                SupervisionDecision::RetryAfter {
                    delay_s: at.saturating_sub(now_epoch_s),
                }
            }
            _ => SupervisionDecision::Failover,
        },
        CapacityState::TemporarilyQuotaExhausted
        | CapacityState::DailyQuotaExhausted
        | CapacityState::ConcurrencyExhausted => match &executor.recovery {
            Some(recovery) if recovery.recoverable => SupervisionDecision::ParkUntil {
                epoch_s: recovery.available_at_epoch_s.unwrap_or(now_epoch_s),
            },
            _ => SupervisionDecision::Failover,
        },
        CapacityState::CreditExhausted
        | CapacityState::SpendLimitExhausted
        | CapacityState::ProviderUnavailable => SupervisionDecision::Failover,
        CapacityState::AuthenticationFailure
        | CapacityState::AccountDisabled
        | CapacityState::CapabilityMismatch
        | CapacityState::Unknown => SupervisionDecision::Block,
    };

    Ok(decision)
}

fn hard_eligible(
    executor: &ExecutorRecord,
    policy: &ExecutionPolicy,
) -> Result<bool, ExecutorCapacityError> {
    executor.validate()?;
    policy.validate()?;

    if !executor.can_receive_project_data() {
        return Ok(false);
    }
    if executor.reliability_score_basis_points > 10_000 {
        return Ok(false);
    }
    if !policy
        .required_capabilities
        .is_subset(&executor.capabilities)
    {
        return Ok(false);
    }
    if executor.paid
        && (!policy.paid_fallback_allowed
            || executor.estimated_cost_microunits > policy.max_paid_cost_microunits)
    {
        return Ok(false);
    }
    Ok(matches!(executor.capacity, CapacityState::Available))
}

pub fn select_executor<'a>(
    executors: &'a [ExecutorRecord],
    policy: &ExecutionPolicy,
) -> Result<Option<&'a ExecutorRecord>, ExecutorCapacityError> {
    policy.validate()?;
    let mut candidates = Vec::new();
    for executor in executors {
        if hard_eligible(executor, policy)? {
            candidates.push(executor);
        }
    }

    candidates.sort_by(|left, right| {
        let left_paid_penalty = if policy.prefer_free && left.paid {
            1u8
        } else {
            0u8
        };
        let right_paid_penalty = if policy.prefer_free && right.paid {
            1u8
        } else {
            0u8
        };
        left_paid_penalty
            .cmp(&right_paid_penalty)
            .then_with(|| {
                right
                    .reliability_score_basis_points
                    .cmp(&left.reliability_score_basis_points)
            })
            .then_with(|| {
                left.estimated_cost_microunits
                    .cmp(&right.estimated_cost_microunits)
            })
            .then_with(|| left.executor_id.cmp(&right.executor_id))
    });

    Ok(candidates.into_iter().next())
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionTransition {
    ContinueCurrent,
    WaitForRecovery {
        executor_id: String,
        available_at_epoch_s: u64,
    },
    Reassign {
        executor_id: String,
    },
    Block,
}

pub fn plan_execution_transition(
    current: &ExecutorRecord,
    alternatives: &[ExecutorRecord],
    policy: &ExecutionPolicy,
    now_epoch_s: u64,
) -> Result<ExecutionTransition, ExecutorCapacityError> {
    current.validate()?;
    policy.validate()?;

    if matches!(current.capacity, CapacityState::Available) {
        return Ok(ExecutionTransition::ContinueCurrent);
    }

    let free_alternatives: Vec<ExecutorRecord> = alternatives
        .iter()
        .filter(|candidate| !candidate.paid)
        .cloned()
        .collect();
    if let Some(candidate) = select_executor(&free_alternatives, policy)? {
        return Ok(ExecutionTransition::Reassign {
            executor_id: candidate.executor_id.clone(),
        });
    }

    if !current.paid {
        if let Some(recovery) = &current.recovery {
            if recovery.recoverable {
                if let Some(available_at_epoch_s) = recovery.available_at_epoch_s {
                    let wait_s = available_at_epoch_s.saturating_sub(now_epoch_s);
                    if wait_s <= policy.max_wait_for_free_s {
                        return Ok(ExecutionTransition::WaitForRecovery {
                            executor_id: current.executor_id.clone(),
                            available_at_epoch_s,
                        });
                    }
                }
            }
        }
    }

    if let Some(candidate) = select_executor(alternatives, policy)? {
        return Ok(ExecutionTransition::Reassign {
            executor_id: candidate.executor_id.clone(),
        });
    }

    Ok(ExecutionTransition::Block)
}

pub fn authorize_handoff(checkpoint: &VerifiedCheckpoint) -> Result<(), ExecutorCapacityError> {
    checkpoint.validate()
}

pub fn executor_completion_implies_acceptance(_executor_completed: bool) -> bool {
    false
}
