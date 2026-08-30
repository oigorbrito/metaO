use crate::project_contract::Provenance;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum TechStackDecisionMode {
    UserFixed,
    UserPreferred,
    MetaoRecommended,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Technology {
    pub id: String,
}

impl Technology {
    pub fn new(id: impl Into<String>) -> Result<Self, TechStackError> {
        let id = id.into().trim().to_lowercase();
        if id.is_empty() {
            return Err(TechStackError::BlankTechnologyIdentity);
        }
        Ok(Self { id })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum TechStackError {
    BlankTechnologyIdentity,
    InvalidProvenance,
    MissingRationale,
    ConflictRequiredForbidden(String),
    ConflictPreferredForbidden(String),
    ConflictRequiredPreferred(String),
    UserFixedOverrideForbidden,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct TechnicalPreferenceProfile {
    pub mode: TechStackDecisionMode,
    pub required_languages: BTreeSet<Technology>,
    pub preferred_languages: BTreeSet<Technology>,
    pub required_frameworks: BTreeSet<Technology>,
    pub preferred_frameworks: BTreeSet<Technology>,
    pub forbidden_technologies: BTreeSet<Technology>,
    pub frontend_preference: Option<String>,
    pub backend_preference: Option<String>,
    pub database_preference: Option<String>,
    pub mobile_requirement: Option<String>,
    pub deployment_target: Option<String>,
    pub hosting_constraints: Option<String>,
    pub cost_constraints: Option<String>,
    pub team_environment_constraints: Option<String>,
    pub rationale: Option<String>,
    pub provenance: Provenance,
}

impl TechnicalPreferenceProfile {
    pub fn validate(&self) -> Result<(), TechStackError> {
        self.provenance.validate().map_err(|_| TechStackError::InvalidProvenance)?;
        if matches!(self.mode, TechStackDecisionMode::UserPreferred | TechStackDecisionMode::MetaoRecommended)
            && self.rationale.as_deref().map(str::trim).filter(|s| !s.is_empty()).is_none()
        {
            return Err(TechStackError::MissingRationale);
        }

        for required in self.required_languages.iter().chain(self.required_frameworks.iter()) {
            if self.forbidden_technologies.contains(required) {
                return Err(TechStackError::ConflictRequiredForbidden(required.id.clone()));
            }
            if self.preferred_languages.contains(required) || self.preferred_frameworks.contains(required) {
                return Err(TechStackError::ConflictRequiredPreferred(required.id.clone()));
            }
        }
        for preferred in self.preferred_languages.iter().chain(self.preferred_frameworks.iter()) {
            if self.forbidden_technologies.contains(preferred) {
                return Err(TechStackError::ConflictPreferredForbidden(preferred.id.clone()));
            }
        }
        Ok(())
    }

    pub fn explicit_override(
        &self,
        replacement: TechnicalPreferenceProfile,
        rationale: impl Into<String>,
        decision_provenance: Provenance,
    ) -> Result<TechnicalPreferenceProfile, TechStackError> {
        if self.mode == TechStackDecisionMode::UserFixed {
            return Err(TechStackError::UserFixedOverrideForbidden);
        }
        decision_provenance.validate().map_err(|_| TechStackError::InvalidProvenance)?;
        let rationale = rationale.into();
        if rationale.trim().is_empty() {
            return Err(TechStackError::MissingRationale);
        }
        replacement.validate()?;
        Ok(replacement)
    }
}
