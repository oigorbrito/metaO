use serde::{Deserialize, Serialize};

use crate::project_contract::{
    ContractError as ProjectContractError, ItemId, Provenance, SemanticCategory, SemanticItem,
};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationPolicyError {
    EmptyIdentity(&'static str),
    EmptyDescription,
    InvalidProvenance,
    InvalidSafeDefault(&'static str),
    InvalidDisposition(&'static str),
}

impl From<ProjectContractError> for ClarificationPolicyError {
    fn from(_: ProjectContractError) -> Self {
        Self::InvalidProvenance
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Materiality {
    Material,
    NonMaterial,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Reversibility {
    Reversible,
    Irreversible,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationConcern {
    General,
    DestructiveChoice,
    RegulatoryOrSecurity,
    UserFixedTechnology,
    ScopeChanging,
}

impl ClarificationConcern {
    pub fn requires_materiality(self) -> bool {
        matches!(
            self,
            Self::DestructiveChoice
                | Self::RegulatoryOrSecurity
                | Self::UserFixedTechnology
                | Self::ScopeChanging
        )
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SafeDefault {
    pub description: String,
    pub rationale: String,
    pub provenance: Provenance,
}

impl SafeDefault {
    pub fn validate(&self) -> Result<(), ClarificationPolicyError> {
        if self.description.trim().is_empty() {
            return Err(ClarificationPolicyError::InvalidSafeDefault(
                "blank default description",
            ));
        }
        if self.rationale.trim().is_empty() {
            return Err(ClarificationPolicyError::InvalidSafeDefault(
                "blank default rationale",
            ));
        }
        self.provenance.validate()?;
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnresolvedDiscoveryItem {
    pub item_id: ItemId,
    pub description: String,
    pub materiality: Materiality,
    pub reversibility: Reversibility,
    pub concern: ClarificationConcern,
    pub provenance: Provenance,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub safe_default: Option<SafeDefault>,
}

impl UnresolvedDiscoveryItem {
    pub fn validate(&self) -> Result<(), ClarificationPolicyError> {
        if self.item_id.0.trim().is_empty() {
            return Err(ClarificationPolicyError::EmptyIdentity("item_id"));
        }
        if self.description.trim().is_empty() {
            return Err(ClarificationPolicyError::EmptyDescription);
        }
        self.provenance.validate()?;
        if let Some(default) = &self.safe_default {
            default.validate()?;
        }
        if self.concern.requires_materiality() && self.materiality != Materiality::Material {
            return Err(ClarificationPolicyError::InvalidDisposition(
                "high-impact concern must be material",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationDisposition {
    Unresolved,
    Resolved {
        resolution: String,
        provenance: Provenance,
    },
    Waived {
        rationale: String,
        provenance: Provenance,
    },
}

impl ClarificationDisposition {
    fn validate(&self) -> Result<(), ClarificationPolicyError> {
        match self {
            Self::Unresolved => Ok(()),
            Self::Resolved {
                resolution,
                provenance,
            } => {
                if resolution.trim().is_empty() {
                    return Err(ClarificationPolicyError::InvalidDisposition(
                        "blank resolution",
                    ));
                }
                provenance.validate()?;
                Ok(())
            }
            Self::Waived {
                rationale,
                provenance,
            } => {
                if rationale.trim().is_empty() {
                    return Err(ClarificationPolicyError::InvalidDisposition(
                        "blank waiver rationale",
                    ));
                }
                provenance.validate()?;
                Ok(())
            }
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationAction {
    AskHuman,
    RecordSafeAssumption,
    NoAction,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssumptionCandidate {
    pub source_item_id: ItemId,
    pub description: String,
    pub rationale: String,
    pub provenance: Provenance,
}

impl AssumptionCandidate {
    pub fn as_semantic_item(&self) -> SemanticItem {
        SemanticItem {
            item_id: self.source_item_id.clone(),
            category: SemanticCategory::Assumption,
            description: self.description.clone(),
            provenance: self.provenance.clone(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClarificationPolicyResult {
    pub source_item_id: ItemId,
    pub action: ClarificationAction,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub assumption: Option<AssumptionCandidate>,
    pub reason: String,
}

pub fn classify_clarification(
    item: &UnresolvedDiscoveryItem,
    disposition: &ClarificationDisposition,
) -> Result<ClarificationPolicyResult, ClarificationPolicyError> {
    item.validate()?;
    disposition.validate()?;

    if !matches!(disposition, ClarificationDisposition::Unresolved) {
        return Ok(ClarificationPolicyResult {
            source_item_id: item.item_id.clone(),
            action: ClarificationAction::NoAction,
            assumption: None,
            reason: "item explicitly resolved or waived".to_string(),
        });
    }

    if item.materiality == Materiality::Material
        || item.reversibility == Reversibility::Irreversible
    {
        return Ok(ClarificationPolicyResult {
            source_item_id: item.item_id.clone(),
            action: ClarificationAction::AskHuman,
            assumption: None,
            reason: "material or irreversible ambiguity requires human clarification".to_string(),
        });
    }

    let Some(default) = &item.safe_default else {
        return Ok(ClarificationPolicyResult {
            source_item_id: item.item_id.clone(),
            action: ClarificationAction::AskHuman,
            assumption: None,
            reason: "no explicit safe default is available".to_string(),
        });
    };

    Ok(ClarificationPolicyResult {
        source_item_id: item.item_id.clone(),
        action: ClarificationAction::RecordSafeAssumption,
        assumption: Some(AssumptionCandidate {
            source_item_id: item.item_id.clone(),
            description: default.description.clone(),
            rationale: default.rationale.clone(),
            provenance: default.provenance.clone(),
        }),
        reason: "non-material reversible ambiguity has an explicit safe default".to_string(),
    })
}
