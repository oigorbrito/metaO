use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionStageEvidenceError {
    BlankStageId,
    BlankReason,
    BlankEvidenceRef,
    InvalidEvidenceBasis,
    DuplicateStage(String),
    SequenceGap { expected: u64, actual: u64 },
    InvalidExecutionClaim,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionStageStatus {
    Pass,
    Blocked,
    Failed,
    Skipped,
    NotRequested,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionStageEvidenceBasis {
    IndependentObservation,
    AdapterVerified,
    SelfReported,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionStageEvidence {
    pub stage_id: String,
    pub sequence: u64,
    pub requested: bool,
    pub executed: bool,
    pub status: ExecutionStageStatus,
    pub reason: String,
    pub evidence_basis: ExecutionStageEvidenceBasis,
    pub evidence_ref: Option<String>,
}

impl ExecutionStageEvidence {
    pub fn validate(&self) -> Result<(), ExecutionStageEvidenceError> {
        if self.stage_id.trim().is_empty() {
            return Err(ExecutionStageEvidenceError::BlankStageId);
        }
        if self.reason.trim().is_empty() {
            return Err(ExecutionStageEvidenceError::BlankReason);
        }

        match self.status {
            ExecutionStageStatus::Pass | ExecutionStageStatus::Failed => {
                if !self.requested || !self.executed {
                    return Err(ExecutionStageEvidenceError::InvalidExecutionClaim);
                }
                if !matches!(
                    self.evidence_basis,
                    ExecutionStageEvidenceBasis::IndependentObservation
                        | ExecutionStageEvidenceBasis::AdapterVerified
                ) {
                    return Err(ExecutionStageEvidenceError::InvalidEvidenceBasis);
                }
                if self
                    .evidence_ref
                    .as_deref()
                    .is_none_or(|value| value.trim().is_empty())
                {
                    return Err(ExecutionStageEvidenceError::BlankEvidenceRef);
                }
            }
            ExecutionStageStatus::Blocked | ExecutionStageStatus::Skipped => {
                if !self.requested || self.executed {
                    return Err(ExecutionStageEvidenceError::InvalidExecutionClaim);
                }
            }
            ExecutionStageStatus::NotRequested => {
                if self.requested || self.executed {
                    return Err(ExecutionStageEvidenceError::InvalidExecutionClaim);
                }
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionStageReport {
    pub stages: Vec<ExecutionStageEvidence>,
    pub passed: usize,
    pub blocked: usize,
    pub failed: usize,
    pub skipped: usize,
    pub not_requested: usize,
}

pub fn project_execution_stages(
    stages: &[ExecutionStageEvidence],
) -> Result<ExecutionStageReport, ExecutionStageEvidenceError> {
    let mut ids = BTreeSet::new();
    let mut ordered = stages.to_vec();
    ordered.sort_by_key(|stage| stage.sequence);

    for (index, stage) in ordered.iter().enumerate() {
        stage.validate()?;
        if !ids.insert(stage.stage_id.clone()) {
            return Err(ExecutionStageEvidenceError::DuplicateStage(
                stage.stage_id.clone(),
            ));
        }
        let expected = index as u64 + 1;
        if stage.sequence != expected {
            return Err(ExecutionStageEvidenceError::SequenceGap {
                expected,
                actual: stage.sequence,
            });
        }
    }

    let count = |status| ordered.iter().filter(|stage| stage.status == status).count();

    Ok(ExecutionStageReport {
        stages: ordered,
        passed: count(ExecutionStageStatus::Pass),
        blocked: count(ExecutionStageStatus::Blocked),
        failed: count(ExecutionStageStatus::Failed),
        skipped: count(ExecutionStageStatus::Skipped),
        not_requested: count(ExecutionStageStatus::NotRequested),
    })
}
