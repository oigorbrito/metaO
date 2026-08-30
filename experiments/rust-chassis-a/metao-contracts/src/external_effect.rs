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
        Ok(())
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
    pub external_postcondition_verified: bool,
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
        .any(|entry| entry.external_postcondition_verified);

    let (disposition, reason) = if has_verified_applied_postcondition
        || history
            .iter()
            .any(|entry| entry.outcome == ExternalEffectOutcome::Applied)
    {
        (
            EffectRetryDisposition::AlreadyApplied,
            "authoritative history or independent postcondition proves effect already applied",
        )
    } else {
        match latest.outcome {
            ExternalEffectOutcome::NotAttempted | ExternalEffectOutcome::NotApplied => (
                EffectRetryDisposition::SafeToRetry,
                "authoritative history proves effect was not applied",
            ),
            ExternalEffectOutcome::Ambiguous | ExternalEffectOutcome::Failed => {
                if intent
                    .idempotency_key
                    .as_deref()
                    .is_some_and(|value| !value.trim().is_empty())
                {
                    (
                        EffectRetryDisposition::SafeToRetry,
                        "external outcome is ambiguous but a stable idempotency key is preserved",
                    )
                } else if latest.outcome == ExternalEffectOutcome::Ambiguous {
                    (
                        EffectRetryDisposition::RequireHumanOrPolicy,
                        "ambiguous external outcome has no idempotency mechanism or proof",
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
    }
    Ok(())
}
