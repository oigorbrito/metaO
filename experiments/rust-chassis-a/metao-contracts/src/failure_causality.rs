use crate::{ExecutionId, MissionId};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum FactualExecutionOutcome {
    Succeeded,
    Cancelled,
    Timeout,
    Failed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum FailureClass {
    None,
    Transient,
    Permanent,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum FailureClassificationBasis {
    AuthoritativeObservation,
    AdapterNormalization,
    CallerDeclared,
    Missing,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryStatus {
    NotRequired,
    NotAttempted,
    Complete,
    Incomplete,
    Failed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RetryEligibility {
    Eligible,
    Ineligible,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FailureCausalityFacts {
    pub original_outcome: FactualExecutionOutcome,
    pub failure_class: FailureClass,
    pub failure_class_basis: FailureClassificationBasis,
    pub failure_class_evidence_ref: Option<String>,
    pub recovery_required: bool,
    pub recovery_status: RecoveryStatus,
    pub current_attempt: u64,
    pub max_attempts: u64,
    pub policy_blocked: bool,
    pub risk_blocked: bool,
    pub budget_blocked: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RetryEligibilityProjection {
    pub original_outcome: FactualExecutionOutcome,
    pub failure_class: FailureClass,
    pub failure_class_basis: FailureClassificationBasis,
    pub failure_class_evidence_ref: Option<String>,
    pub recovery_required: bool,
    pub recovery_status: RecoveryStatus,
    pub eligibility: RetryEligibility,
    pub next_attempt: Option<u64>,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRetryAuthorityState {
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub retry_lineage_id: String,
    pub current_attempt: u64,
    pub max_attempts: u64,
    pub state_version: u64,
    pub evidence_ref: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRetryAttemptClaim {
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub retry_lineage_id: String,
    pub current_attempt: u64,
    pub max_attempts: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionRetryAuthorityError {
    InvalidAuthoritativeState,
    BindingMismatch,
    AttemptStateMismatch,
}

impl ExecutionRetryAuthorityState {
    pub fn validate(&self) -> Result<(), ExecutionRetryAuthorityError> {
        if self.retry_lineage_id.trim().is_empty()
            || self.evidence_ref.trim().is_empty()
            || self.current_attempt == 0
            || self.max_attempts == 0
            || self.current_attempt > self.max_attempts
            || self.state_version == 0
        {
            return Err(ExecutionRetryAuthorityError::InvalidAuthoritativeState);
        }
        Ok(())
    }
}

pub fn bind_execution_retry_authority(
    facts: &FailureCausalityFacts,
    claim: &ExecutionRetryAttemptClaim,
    authoritative: &ExecutionRetryAuthorityState,
) -> Result<FailureCausalityFacts, ExecutionRetryAuthorityError> {
    authoritative.validate()?;

    if claim.mission_id != authoritative.mission_id
        || claim.execution_id != authoritative.execution_id
        || claim.retry_lineage_id.trim().is_empty()
        || claim.retry_lineage_id != authoritative.retry_lineage_id
    {
        return Err(ExecutionRetryAuthorityError::BindingMismatch);
    }

    if claim.current_attempt != authoritative.current_attempt
        || claim.max_attempts != authoritative.max_attempts
        || facts.current_attempt != authoritative.current_attempt
        || facts.max_attempts != authoritative.max_attempts
    {
        return Err(ExecutionRetryAuthorityError::AttemptStateMismatch);
    }

    let mut bound = facts.clone();
    bound.current_attempt = authoritative.current_attempt;
    bound.max_attempts = authoritative.max_attempts;
    Ok(bound)
}

fn has_factual_transient_evidence(facts: &FailureCausalityFacts) -> bool {
    matches!(
        facts.failure_class_basis,
        FailureClassificationBasis::AuthoritativeObservation
            | FailureClassificationBasis::AdapterNormalization
    ) && facts
        .failure_class_evidence_ref
        .as_deref()
        .is_some_and(|value| !value.trim().is_empty())
}

fn recovery_allows_retry(facts: &FailureCausalityFacts) -> bool {
    if facts.recovery_required {
        facts.recovery_status == RecoveryStatus::Complete
    } else {
        matches!(
            facts.recovery_status,
            RecoveryStatus::NotRequired | RecoveryStatus::Complete
        )
    }
}

pub fn evaluate_retry_eligibility(facts: &FailureCausalityFacts) -> RetryEligibilityProjection {
    let ineligible = |reason: &str| RetryEligibilityProjection {
        original_outcome: facts.original_outcome,
        failure_class: facts.failure_class,
        failure_class_basis: facts.failure_class_basis,
        failure_class_evidence_ref: facts.failure_class_evidence_ref.clone(),
        recovery_required: facts.recovery_required,
        recovery_status: facts.recovery_status,
        eligibility: RetryEligibility::Ineligible,
        next_attempt: None,
        reason: reason.to_string(),
    };

    if facts.current_attempt == 0
        || facts.max_attempts == 0
        || facts.current_attempt >= facts.max_attempts
    {
        return ineligible("execution attempt budget is exhausted or invalid");
    }
    if facts.policy_blocked {
        return ineligible("policy blocks retry");
    }
    if facts.risk_blocked {
        return ineligible("risk authority blocks retry");
    }
    if facts.budget_blocked {
        return ineligible("execution budget blocks retry");
    }
    if matches!(
        facts.original_outcome,
        FactualExecutionOutcome::Succeeded | FactualExecutionOutcome::Cancelled
    ) {
        return ineligible("original execution outcome is not retryable");
    }
    if !recovery_allows_retry(facts) {
        return ineligible("required recovery is absent, incomplete, failed, or inconsistent");
    }
    if facts.failure_class != FailureClass::Transient {
        return ineligible("failure is not factually classified as transient");
    }
    if !has_factual_transient_evidence(facts) {
        return ineligible("transient classification lacks authoritative factual evidence");
    }

    RetryEligibilityProjection {
        original_outcome: facts.original_outcome,
        failure_class: facts.failure_class,
        failure_class_basis: facts.failure_class_basis,
        failure_class_evidence_ref: facts.failure_class_evidence_ref.clone(),
        recovery_required: facts.recovery_required,
        recovery_status: facts.recovery_status,
        eligibility: RetryEligibility::Eligible,
        next_attempt: Some(facts.current_attempt + 1),
        reason: "factual transient failure is eligible for a later controlled retry decision"
            .to_string(),
    }
}
