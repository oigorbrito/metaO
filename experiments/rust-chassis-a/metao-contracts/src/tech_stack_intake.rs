use crate::project_contract::Provenance;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TechStackDecisionMode {
    UserFixed,
    UserPreferred,
    MetaoRecommended,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize, PartialOrd, Ord)]
pub struct Technology {
    pub id: String, // Normalized identifier
}

impl Technology {
    pub fn new(id: impl Into<String>) -> Self {
        Self {
            id: id.into().trim().to_lowercase(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    pub fn validate(&self) -> Result<(), &'static str> {
        // Validation rules based on requirements
        if self.mode != TechStackDecisionMode::UserFixed && self.rationale.is_none() {
            return Err("Rationale is required for non-UserFixed mode");
        }

        self.provenance
            .validate()
            .map_err(|_| "Invalid provenance")?;

        // 6. Required vs forbidden conflict
        let forbidden = &self.forbidden_technologies;
        for req in self
            .required_languages
            .iter()
            .chain(self.required_frameworks.iter())
        {
            if forbidden.contains(req) {
                return Err("Conflict: Technology is both required and forbidden");
            }
        }

        // 7. Preferred vs forbidden conflict
        for pref in self
            .preferred_languages
            .iter()
            .chain(self.preferred_frameworks.iter())
        {
            if forbidden.contains(pref) {
                return Err("Conflict: Technology is both preferred and forbidden");
            }
        }

        // T07. required != preferred
        for req in self
            .required_languages
            .iter()
            .chain(self.required_frameworks.iter())
        {
            if self.preferred_languages.contains(req) || self.preferred_frameworks.contains(req) {
                return Err("Conflict: Technology is both required and preferred");
            }
        }

        // 13. Reject blank tech identities
        if self.required_languages.iter().any(|t| t.id.is_empty())
            || self.preferred_languages.iter().any(|t| t.id.is_empty())
            || self.required_frameworks.iter().any(|t| t.id.is_empty())
            || self.preferred_frameworks.iter().any(|t| t.id.is_empty())
            || self.forbidden_technologies.iter().any(|t| t.id.is_empty())
        {
            return Err("Technology identity cannot be blank");
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::project_contract::ProvenanceCategory;

    fn dummy_provenance() -> Provenance {
        Provenance {
            category: ProvenanceCategory::UserExplicit,
            source_id: "test".to_string(),
            derived_from: None,
            authorization: None,
        }
    }

    #[test]
    fn test_valid_profile() {
        let profile = TechnicalPreferenceProfile {
            mode: TechStackDecisionMode::UserFixed,
            required_languages: BTreeSet::from([Technology::new("python")]),
            preferred_languages: BTreeSet::new(),
            required_frameworks: BTreeSet::new(),
            preferred_frameworks: BTreeSet::new(),
            forbidden_technologies: BTreeSet::new(),
            frontend_preference: None,
            backend_preference: None,
            database_preference: None,
            mobile_requirement: None,
            deployment_target: None,
            hosting_constraints: None,
            cost_constraints: None,
            team_environment_constraints: None,
            rationale: None,
            provenance: dummy_provenance(),
        };
        assert!(profile.validate().is_ok());
    }

    #[test]
    fn test_conflict_required_forbidden() {
        let profile = TechnicalPreferenceProfile {
            mode: TechStackDecisionMode::UserFixed,
            required_languages: BTreeSet::from([Technology::new("python")]),
            preferred_languages: BTreeSet::new(),
            required_frameworks: BTreeSet::new(),
            preferred_frameworks: BTreeSet::new(),
            forbidden_technologies: BTreeSet::from([Technology::new("python")]),
            frontend_preference: None,
            backend_preference: None,
            database_preference: None,
            mobile_requirement: None,
            deployment_target: None,
            hosting_constraints: None,
            cost_constraints: None,
            team_environment_constraints: None,
            rationale: None,
            provenance: dummy_provenance(),
        };
        assert!(profile.validate().is_err());
    }

    #[test]
    fn test_t07_required_preferred_conflict() {
        let profile = TechnicalPreferenceProfile {
            mode: TechStackDecisionMode::UserFixed,
            required_languages: BTreeSet::from([Technology::new("python")]),
            preferred_languages: BTreeSet::from([Technology::new("python")]),
            required_frameworks: BTreeSet::new(),
            preferred_frameworks: BTreeSet::new(),
            forbidden_technologies: BTreeSet::new(),
            frontend_preference: None,
            backend_preference: None,
            database_preference: None,
            mobile_requirement: None,
            deployment_target: None,
            hosting_constraints: None,
            cost_constraints: None,
            team_environment_constraints: None,
            rationale: None,
            provenance: dummy_provenance(),
        };
        assert!(profile.validate().is_err());
    }

    #[test]
    fn test_t12_user_preferred_no_rationale_fails() {
        let profile = TechnicalPreferenceProfile {
            mode: TechStackDecisionMode::UserPreferred,
            required_languages: BTreeSet::from([Technology::new("python")]),
            preferred_languages: BTreeSet::new(),
            required_frameworks: BTreeSet::new(),
            preferred_frameworks: BTreeSet::new(),
            forbidden_technologies: BTreeSet::new(),
            frontend_preference: None,
            backend_preference: None,
            database_preference: None,
            mobile_requirement: None,
            deployment_target: None,
            hosting_constraints: None,
            cost_constraints: None,
            team_environment_constraints: None,
            rationale: None, // Missing rationale
            provenance: dummy_provenance(),
        };
        assert!(profile.validate().is_err());
    }
}
