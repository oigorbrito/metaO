use crate::project_contract::{Provenance, SemanticCategory};
use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationPolicyError {
    BlankItemIdentity,
    BlankDescription,
    InvalidProvenance,
    InvalidSafeDefault,
    InvalidResolution,
}

impl fmt::Display for ClarificationPolicyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Materiality {
    Material,
    NonMaterial,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Reversibility {
    Reversible,
    Irreversible,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MaterialityReason {
    Destructive,
    RegulatoryOrSecurity,
    UserFixedTechnology,
    ScopeChanging,
    OtherMaterialImpact,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SafeDefault {
    pub value: String,
    pub rationale: String,
    pub provenance: Provenance,
}

impl SafeDefault {
    pub fn validate(&self) -> Result<(), ClarificationPolicyError> {
        if self.value.trim().is_empty() || self.rationale.trim().is_empty() {
            return Err(ClarificationPolicyError::InvalidSafeDefault);
        }
        self.provenance
            .validate()
            .map_err(|_| ClarificationPolicyError::InvalidSafeDefault)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnresolvedDiscoveryItem {
    pub item_id: String,
    pub description: String,
    pub materiality: Materiality,
    pub reversibility: Reversibility,
    pub materiality_reason: Option<MaterialityReason>,
    pub provenance: Provenance,
    pub safe_default: Option<SafeDefault>,
}

impl UnresolvedDiscoveryItem {
    pub fn validate(&self) -> Result<(), ClarificationPolicyError> {
        if self.item_id.trim().is_empty() {
            return Err(ClarificationPolicyError::BlankItemIdentity);
        }
        if self.description.trim().is_empty() {
            return Err(ClarificationPolicyError::BlankDescription);
        }
        self.provenance
            .validate()
            .map_err(|_| ClarificationPolicyError::InvalidProvenance)?;
        if let Some(default) = &self.safe_default {
            default.validate()?;
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClarificationAction {
    AskHuman,
    RecordSafeAssumption,
    NoAction,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssumptionCandidate {
    pub category: SemanticCategory,
    pub description: String,
    pub rationale: String,
    pub provenance: Provenance,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClarificationDecision {
    pub action: ClarificationAction,
    pub assumption: Option<AssumptionCandidate>,
    pub rationale: String,
}

pub struct ClarificationPolicy;

impl ClarificationPolicy {
    pub fn classify(
        item: &UnresolvedDiscoveryItem,
    ) -> Result<ClarificationDecision, ClarificationPolicyError> {
        item.validate()?;

        if item.materiality == Materiality::Material
            || item.reversibility == Reversibility::Irreversible
        {
            return Ok(ClarificationDecision {
                action: ClarificationAction::AskHuman,
                assumption: None,
                rationale: "material or irreversible ambiguity requires explicit human resolution"
                    .to_string(),
            });
        }

        match &item.safe_default {
            Some(default) => Ok(ClarificationDecision {
                action: ClarificationAction::RecordSafeAssumption,
                assumption: Some(AssumptionCandidate {
                    category: SemanticCategory::Assumption,
                    description: default.value.clone(),
                    rationale: default.rationale.clone(),
                    provenance: default.provenance.clone(),
                }),
                rationale: "non-material reversible ambiguity has an explicit safe default"
                    .to_string(),
            }),
            None => Ok(ClarificationDecision {
                action: ClarificationAction::AskHuman,
                assumption: None,
                rationale: "ambiguity has no explicit safe default and cannot auto-continue"
                    .to_string(),
            }),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ResolutionKind {
    HumanResolution,
    ExplicitWaiver,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExplicitResolution {
    pub kind: ResolutionKind,
    pub rationale: String,
    pub provenance: Provenance,
}

impl ExplicitResolution {
    pub fn validate(&self) -> Result<(), ClarificationPolicyError> {
        if self.rationale.trim().is_empty() {
            return Err(ClarificationPolicyError::InvalidResolution);
        }
        self.provenance
            .validate()
            .map_err(|_| ClarificationPolicyError::InvalidResolution)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResolvedClarification {
    pub original_item: UnresolvedDiscoveryItem,
    pub original_decision: ClarificationDecision,
    pub resolution: ExplicitResolution,
    pub next_action: ClarificationAction,
}

pub fn apply_explicit_resolution(
    item: &UnresolvedDiscoveryItem,
    decision: &ClarificationDecision,
    resolution: ExplicitResolution,
) -> Result<ResolvedClarification, ClarificationPolicyError> {
    item.validate()?;
    resolution.validate()?;

    Ok(ResolvedClarification {
        original_item: item.clone(),
        original_decision: decision.clone(),
        resolution,
        next_action: ClarificationAction::NoAction,
    })
}
