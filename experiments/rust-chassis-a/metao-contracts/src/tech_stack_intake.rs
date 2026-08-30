use crate::project_contract::Provenance;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TechStackIntakeError {
    BlankTechnologyIdentity,
    InvalidProvenance,
    MissingRationale,
    ConflictRequiredForbidden,
    ConflictPreferredForbidden,
    ConflictRequiredPreferred,
    UserFixedOverrideForbidden,
}

impl fmt::Display for TechStackIntakeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TechStackDecisionMode {
    UserFixed,
    UserPreferred,
    MetaoRecommended,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize, PartialOrd, Ord)]
pub struct Technology {
    id: String,
}

impl Technology {
    pub fn new(id: impl Into<String>) -> Result<Self, TechStackIntakeError> {
        let id = id.into().trim().to_lowercase();
        if id.is_empty() {
            return Err(TechStackIntakeError::BlankTechnologyIdentity);
        }
        Ok(Self { id })
    }

    pub fn as_str(&self) -> &str {
        &self.id
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
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
    pub fn validate(&self) -> Result<(), TechStackIntakeError> {
        if self.mode != TechStackDecisionMode::UserFixed {
            validate_rationale(self.rationale.as_deref())?;
        }
        validate_provenance(&self.provenance)?;

        let required = self
            .required_languages
            .iter()
            .chain(self.required_frameworks.iter());
        for technology in required {
            if self.forbidden_technologies.contains(technology) {
                return Err(TechStackIntakeError::ConflictRequiredForbidden);
            }
            if self.preferred_languages.contains(technology)
                || self.preferred_frameworks.contains(technology)
            {
                return Err(TechStackIntakeError::ConflictRequiredPreferred);
            }
        }

        for technology in self
            .preferred_languages
            .iter()
            .chain(self.preferred_frameworks.iter())
        {
            if self.forbidden_technologies.contains(technology) {
                return Err(TechStackIntakeError::ConflictPreferredForbidden);
            }
        }

        Ok(())
    }

    pub fn explicit_override(
        &self,
        mut replacement: TechnicalPreferenceProfile,
        rationale: impl Into<String>,
        provenance: Provenance,
    ) -> Result<TechnicalPreferenceProfile, TechStackIntakeError> {
        if self.mode == TechStackDecisionMode::UserFixed {
            return Err(TechStackIntakeError::UserFixedOverrideForbidden);
        }

        let rationale = rationale.into();
        validate_rationale(Some(&rationale))?;
        validate_provenance(&provenance)?;

        replacement.rationale = Some(rationale);
        replacement.provenance = provenance;
        replacement.validate()?;
        Ok(replacement)
    }
}

fn validate_rationale(rationale: Option<&str>) -> Result<(), TechStackIntakeError> {
    match rationale {
        Some(value) if !value.trim().is_empty() => Ok(()),
        _ => Err(TechStackIntakeError::MissingRationale),
    }
}

fn validate_provenance(provenance: &Provenance) -> Result<(), TechStackIntakeError> {
    provenance
        .validate()
        .map_err(|_| TechStackIntakeError::InvalidProvenance)
}
