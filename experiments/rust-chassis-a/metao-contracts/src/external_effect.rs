use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExternalEffectError {
    BlankEffectId,
    BlankMissionId,
    BlankLogicalOperation,
    BlankExpectedPostcondition,
    BlankHistoryRecordId,
    BlankExecutionId,
    MissingAuthoritativeHistory,
    DuplicateHistoryRecord(String),
    HistorySequenceGap { expected: u64, actual: u64 },
    EffectBindingMismatch,
    IdempotencyKeyMismatch,
    InvalidIdempotencyAssurance,
    InvalidPostconditionEvidence,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExternalEffectOutcome {
    NotAttempted,
    Applied,
    NotApplied,
    Ambiguous,
    Failed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum IdempotencyAssurance {
    None,
    KeyDeclared,
    EnforcementVerified,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum PostconditionEvidenceBasis {
    None,
    IndependentExternalObservation,
    AdapterVerified,
    CallerDeclared,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum EffectRetryDisposition {
    SafeToRetry,
    AlreadyApplied,
    BlockedAmbiguous,
    RequireHumanOrPolicy,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectIntent {
    pub effect_id: String,
    pub mission_id: String,
    pub logical_operation: String,
    pub idempotency_key: Option<String>,
    pub idempotency_assurance: IdempotencyAssurance,
    pub idempotency_evidence_ref: Option<String>,
    pub expected_postcondition: String,
}

impl EffectIntent {
    pub fn validate(&self) -> Result<(), ExternalEffectError> {
        if self.effect_id.trim().is_empty() {
            return Err(ExternalEffectError::BlankEffectId);
        }
        if self.mission_id.trim().is_empty() {
            return Err(ExternalEffectError::BlankMissionId);
        }
        if self.logical_operation.trim().is_empty() {
            return Err(ExternalEffectError::BlankLogicalOperation);
        }
        if self.expected_postcondition.trim().is_empty() {
            return Err(ExternalEffectError::BlankExpectedPostcondition);
        }

        let has_key = self
            .idempotency_key
            .as_deref()
            .is_some_and(|value| !value.trim().is_empty());
        let has_evidence = self
            .idempotency_evidence_ref
            .as_deref()
            .is_some_and(|value| !value.trim().is_empty());

        match self.idempotency_assurance {
            IdempotencyAssurance::None => {
                if has_key || has_evidence {
                    return Err(ExternalEffectError::InvalidIdempotencyAssurance);
                }
            }
            IdempotencyAssurance::KeyDeclared => {
                if !has_key || has_evidence {
                    return Err(ExternalEffectError::InvalidIdempotencyAssurance);
                }
            }
            IdempotencyAssurance::EnforcementVerified => {
                if !has_key || !has_evidence {
                    return Err(ExternalEffectError::InvalidIdempotencyAssurance);
                }
            }
        }
        Ok(())
    }

    fn has_verified_idempotency_enforcement(&self) -> bool {
        self.idempotency_assurance == IdempotencyAssurance::EnforcementVerified
            && self
                .idempotency_evidence_ref
                .as_deref()
                .is_some_and(|value| !value.trim().is_empty())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectHistoryEntry {
    pub record_id: String,
    pub sequence: u64,
    pub effect_id: String,
    pub idempotency_key: Option<String>,
    pub execution_id: String,
    pub outcome: ExternalEffectOutcome,
    pub postcondition_evidence_basis: PostconditionEvidenceBasis,
    pub postcondition_evidence_ref: Option<String>,
}

impl EffectHistoryEntry {
    fn has_independently_verified_postcondition(&self) -> bool {
        matches!(
            self.postcondition_evidence_basis,
            PostconditionEvidenceBasis::IndependentExternalObservation
                | PostconditionEvidenceBasis::AdapterVerified
        ) && self
            .postcondition_evidence_ref
            .as_deref()
            .is_some_and(|value| !value.trim().is_empty())
    }

    fn validate_postcondition_evidence(&self) -> Result<(), ExternalEffectError> {
        let has_ref = self
            .postcondition_evidence_ref
            .as_deref()
            .is_some_and(|value| !value.trim().is_empty());
        match self.postcondition_evidence_basis {
            PostconditionEvidenceBasis::None => {
                if has_ref {
                    return Err(ExternalEffectError::InvalidPostconditionEvidence);
                }
            }
            PostconditionEvidenceBasis::IndependentExternalObservation
            | PostconditionEvidenceBasis::AdapterVerified => {
                if !has_ref {
                    return Err(ExternalEffectError::InvalidPostconditionEvidence);
                }
            }
            PostconditionEvidenceBasis::CallerDeclared => {}
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectRetryDecision {
    pub effect_id: String,
    pub disposition: EffectRetryDisposition,
    pub authoritative_history_len: usize,
    pub reason: String,
}

pub fn evaluate_effect_retry(
    intent: &EffectIntent,
    history: &[EffectHistoryEntry],
) -> Result<EffectRetryDecision, ExternalEffectError> {
    intent.validate()?;
    validate_history(intent, history)?;

    let latest = history
        .last()
        .ok_or(ExternalEffectError::MissingAuthoritativeHistory)?;

    let has_verified_applied_postcondition = history
        .iter()
        .any(EffectHistoryEntry::has_independently_verified_postcondition);

    let (disposition, reason) = if has_verified_applied_postcondition
        || history
            .iter()
            .any(|entry| entry.outcome == ExternalEffectOutcome::Applied)
    {
        (
            EffectRetryDisposition::AlreadyApplied,
            "authoritative history or independently verified postcondition proves effect already applied",
        )
    } else {
        match latest.outcome {
            ExternalEffectOutcome::NotAttempted | ExternalEffectOutcome::NotApplied => (
                EffectRetryDisposition::SafeToRetry,
                "authoritative history proves effect was not applied",
            ),
            ExternalEffectOutcome::Ambiguous => {
                if intent.has_verified_idempotency_enforcement() {
                    (
                        EffectRetryDisposition::SafeToRetry,
                        "external outcome is ambiguous but external idempotency enforcement is independently evidenced",
                    )
                } else {
                    (
                        EffectRetryDisposition::RequireHumanOrPolicy,
                        "ambiguous external outcome lacks verified idempotency enforcement or postcondition proof",
                    )
                }
            }
            ExternalEffectOutcome::Failed => {
                if intent.has_verified_idempotency_enforcement() {
                    (
                        EffectRetryDisposition::SafeToRetry,
                        "failed attempt remains ambiguous, but external idempotency enforcement is independently evidenced",
                    )
                } else {
                    (
                        EffectRetryDisposition::BlockedAmbiguous,
                        "failed attempt does not prove the external effect was absent",
                    )
                }
            }
            ExternalEffectOutcome::Applied => unreachable!("handled by authoritative applied history"),
        }
    };

    Ok(EffectRetryDecision {
        effect_id: intent.effect_id.clone(),
        disposition,
        authoritative_history_len: history.len(),
        reason: reason.to_string(),
    })
}

fn validate_history(
    intent: &EffectIntent,
    history: &[EffectHistoryEntry],
) -> Result<(), ExternalEffectError> {
    if history.is_empty() {
        return Err(ExternalEffectError::MissingAuthoritativeHistory);
    }

    let mut record_ids = BTreeSet::new();
    for (index, entry) in history.iter().enumerate() {
        if entry.record_id.trim().is_empty() {
            return Err(ExternalEffectError::BlankHistoryRecordId);
        }
        if entry.execution_id.trim().is_empty() {
            return Err(ExternalEffectError::BlankExecutionId);
        }
        if !record_ids.insert(entry.record_id.clone()) {
            return Err(ExternalEffectError::DuplicateHistoryRecord(
                entry.record_id.clone(),
            ));
        }

        let expected_sequence = index as u64 + 1;
        if entry.sequence != expected_sequence {
            return Err(ExternalEffectError::HistorySequenceGap {
                expected: expected_sequence,
                actual: entry.sequence,
            });
        }
        if entry.effect_id != intent.effect_id {
            return Err(ExternalEffectError::EffectBindingMismatch);
        }
        if entry.idempotency_key != intent.idempotency_key {
            return Err(ExternalEffectError::IdempotencyKeyMismatch);
        }
        entry.validate_postcondition_evidence()?;
    }
    Ok(())
}
