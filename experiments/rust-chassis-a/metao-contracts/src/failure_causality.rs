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
