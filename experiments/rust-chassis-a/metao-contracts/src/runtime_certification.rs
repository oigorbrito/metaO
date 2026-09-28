use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeCertificationError {
    BlankBindingField(&'static str),
    BlankEvaluatorId,
    BlankEvaluatorVersion,
    BlankEvaluatorEvidenceRef,
    SelfCertification,
    InvalidEvaluatorEvidenceBasis,
    MissingExpiry,
    InvalidValidityWindow,
    BlankCategoryId,
    BlankReason,
    BlankEvidenceRef,
    DuplicateCategory(String),
    ContradictoryPassFacts(String),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeCertificationBinding {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub execution_context_id: String,
    pub verification_context_id: String,
}

impl RuntimeCertificationBinding {
    pub fn validate(&self) -> Result<(), RuntimeCertificationError> {
        for (name, value) in [
            ("runtime_id", self.runtime_id.as_str()),
            ("runtime_version", self.runtime_version.as_str()),
            ("config_id", self.config_id.as_str()),
            ("execution_context_id", self.execution_context_id.as_str()),
            (
                "verification_context_id",
                self.verification_context_id.as_str(),
            ),
        ] {
            if value.trim().is_empty() {
                return Err(RuntimeCertificationError::BlankBindingField(name));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeCertificationEvidenceBasis {
    IndependentEvaluator,
    TrustedHarness,
    SelfReported,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CertificationCategoryStatus {
    Pass,
    Fail,
    Skipped,
    NotRequested,
    Unknown,
    EvaluatorError,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CertificationCategoryResult {
    pub category_id: String,
    pub status: CertificationCategoryStatus,
    pub benign_utility_passed: Option<bool>,
    pub forbidden_action_observed: Option<bool>,
    pub evidence_ref: Option<String>,
    pub reason: String,
}

impl CertificationCategoryResult {
    pub fn validate(&self) -> Result<(), RuntimeCertificationError> {
        if self.category_id.trim().is_empty() {
            return Err(RuntimeCertificationError::BlankCategoryId);
        }
        if self.reason.trim().is_empty() {
            return Err(RuntimeCertificationError::BlankReason);
        }
        if matches!(
            self.status,
            CertificationCategoryStatus::Pass | CertificationCategoryStatus::Fail
        ) && self
            .evidence_ref
            .as_deref()
            .is_none_or(|value| value.trim().is_empty())
        {
            return Err(RuntimeCertificationError::BlankEvidenceRef);
        }
        if self.status == CertificationCategoryStatus::Pass
            && self.forbidden_action_observed == Some(true)
        {
            return Err(RuntimeCertificationError::ContradictoryPassFacts(
                self.category_id.clone(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeCertificationDecision {
    Certified,
    NotCertified,
    Incomplete,
    Stale,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeCertificationReport {
    pub binding: RuntimeCertificationBinding,
    pub evaluator_id: String,
    pub evaluator_version: String,
    pub evaluator_evidence_basis: RuntimeCertificationEvidenceBasis,
    pub evaluator_evidence_ref: String,
    pub evaluated_at_epoch: i64,
    pub expires_at_epoch: Option<i64>,
    pub required_categories: BTreeSet<String>,
    pub category_results: Vec<CertificationCategoryResult>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeCertificationProjection {
    pub binding: RuntimeCertificationBinding,
    pub decision: RuntimeCertificationDecision,
    pub evaluator_id: String,
    pub required_categories: Vec<String>,
    pub failed_categories: Vec<String>,
    pub incomplete_categories: Vec<String>,
    pub reasons: Vec<String>,
}

impl RuntimeCertificationReport {
    pub fn validate(&self) -> Result<(), RuntimeCertificationError> {
        self.binding.validate()?;
        if self.evaluator_id.trim().is_empty() {
            return Err(RuntimeCertificationError::BlankEvaluatorId);
        }
        if self.evaluator_version.trim().is_empty() {
            return Err(RuntimeCertificationError::BlankEvaluatorVersion);
        }
        if self.evaluator_id == self.binding.runtime_id {
            return Err(RuntimeCertificationError::SelfCertification);
        }
        if !matches!(
            self.evaluator_evidence_basis,
            RuntimeCertificationEvidenceBasis::IndependentEvaluator
                | RuntimeCertificationEvidenceBasis::TrustedHarness
        ) {
            return Err(RuntimeCertificationError::InvalidEvaluatorEvidenceBasis);
        }
        if self.evaluator_evidence_ref.trim().is_empty() {
            return Err(RuntimeCertificationError::BlankEvaluatorEvidenceRef);
        }
        let expires = self
            .expires_at_epoch
            .ok_or(RuntimeCertificationError::MissingExpiry)?;
        if expires <= self.evaluated_at_epoch {
            return Err(RuntimeCertificationError::InvalidValidityWindow);
        }

        let mut seen = BTreeSet::new();
        for result in &self.category_results {
            result.validate()?;
            if !seen.insert(result.category_id.clone()) {
                return Err(RuntimeCertificationError::DuplicateCategory(
                    result.category_id.clone(),
                ));
            }
        }
        Ok(())
    }

    pub fn applies_to(
        &self,
        runtime_id: &str,
        runtime_version: &str,
        config_id: &str,
        execution_context_id: &str,
        verification_context_id: &str,
        now_epoch: i64,
    ) -> bool {
        if self.validate().is_err()
            || self.binding.runtime_id != runtime_id
            || self.binding.runtime_version != runtime_version
            || self.binding.config_id != config_id
            || self.binding.execution_context_id != execution_context_id
            || self.binding.verification_context_id != verification_context_id
            || now_epoch < self.evaluated_at_epoch
        {
            return false;
        }
        self.expires_at_epoch
            .is_some_and(|expires| now_epoch < expires)
    }

    pub fn project(
        &self,
        current_binding: &RuntimeCertificationBinding,
        now_epoch: i64,
    ) -> Result<RuntimeCertificationProjection, RuntimeCertificationError> {
        self.validate()?;

        if !self.applies_to(
            &current_binding.runtime_id,
            &current_binding.runtime_version,
            &current_binding.config_id,
            &current_binding.execution_context_id,
            &current_binding.verification_context_id,
            now_epoch,
        ) {
            return Ok(RuntimeCertificationProjection {
                binding: self.binding.clone(),
                decision: RuntimeCertificationDecision::Stale,
                evaluator_id: self.evaluator_id.clone(),
                required_categories: self.required_categories.iter().cloned().collect(),
                failed_categories: Vec::new(),
                incomplete_categories: Vec::new(),
                reasons: vec!["certification binding or validity no longer applies".to_string()],
            });
        }

        let by_category: BTreeMap<&str, &CertificationCategoryResult> = self
            .category_results
            .iter()
            .map(|result| (result.category_id.as_str(), result))
            .collect();

        let mut failed = Vec::new();
        let mut incomplete = Vec::new();
        let mut reasons = Vec::new();

        for required in &self.required_categories {
            match by_category.get(required.as_str()) {
                Some(result) => match result.status {
                    CertificationCategoryStatus::Pass => {}
                    CertificationCategoryStatus::Fail => {
                        failed.push(required.clone());
                        reasons.push(format!("required category {required} failed"));
                    }
                    CertificationCategoryStatus::Skipped
                    | CertificationCategoryStatus::NotRequested
                    | CertificationCategoryStatus::Unknown
                    | CertificationCategoryStatus::EvaluatorError => {
                        incomplete.push(required.clone());
                        reasons.push(format!(
                            "required category {required} is not conclusively passed: {:?}",
                            result.status
                        ));
                    }
                },
                None => {
                    incomplete.push(required.clone());
                    reasons.push(format!(
                        "required category {required} has no evaluator result"
                    ));
                }
            }
        }

        let decision = if !failed.is_empty() {
            RuntimeCertificationDecision::NotCertified
        } else if !incomplete.is_empty() || self.required_categories.is_empty() {
            if self.required_categories.is_empty() {
                reasons.push("certification profile defines no required categories".to_string());
            }
            RuntimeCertificationDecision::Incomplete
        } else {
            RuntimeCertificationDecision::Certified
        };

        Ok(RuntimeCertificationProjection {
            binding: self.binding.clone(),
            decision,
            evaluator_id: self.evaluator_id.clone(),
            required_categories: self.required_categories.iter().cloned().collect(),
            failed_categories: failed,
            incomplete_categories: incomplete,
            reasons,
        })
    }
}
