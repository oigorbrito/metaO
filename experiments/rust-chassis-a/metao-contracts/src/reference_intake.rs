use serde::{Deserialize, Serialize};

use crate::project_contract::{
    ItemId, ProjectReference, Provenance, ProvenanceCategory, ReferenceId, SemanticCategory,
    SemanticItem,
};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum IntakeError {
    BlankTraitId,
    BlankTraitDescription,
    BlankReferenceId,
    BlankLocator,
    UnknownTrait,
    CannotPromoteUndesiredTrait,
    ConflictingDuplicateTrait,
    InvalidReferenceProvenance,
    InvalidDecisionProvenance,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum PromotionTargetCategory {
    UserRequirement,
    Preference,
    Assumption,
}

impl From<PromotionTargetCategory> for SemanticCategory {
    fn from(cat: PromotionTargetCategory) -> Self {
        match cat {
            PromotionTargetCategory::UserRequirement => SemanticCategory::UserRequirement,
            PromotionTargetCategory::Preference => SemanticCategory::Preference,
            PromotionTargetCategory::Assumption => SemanticCategory::Assumption,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct TraitId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReferenceTrait {
    pub trait_id: TraitId,
    pub description: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReferenceKind {
    Url,
    Repository,
    Document,
    Image,
    Wireframe,
    Other(String),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReferenceInput {
    pub reference_id: ReferenceId,
    pub reference_kind: ReferenceKind,
    pub locator: String,
    pub desired_traits: Vec<ReferenceTrait>,
    pub undesired_traits: Vec<ReferenceTrait>,
    pub provenance: Provenance,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReferenceConflict {
    pub reference_id: ReferenceId,
    pub trait_id: TraitId,
    pub reason: String,
}

pub struct ReferenceIntake;

impl ReferenceIntake {
    pub fn evaluate_reference(
        input: &ReferenceInput,
    ) -> Result<Result<ProjectReference, ReferenceConflict>, IntakeError> {
        if input.reference_id.0.trim().is_empty() {
            return Err(IntakeError::BlankReferenceId);
        }
        if input.locator.trim().is_empty() {
            return Err(IntakeError::BlankLocator);
        }
        if input.provenance.source_id.trim().is_empty() {
            return Err(IntakeError::InvalidReferenceProvenance);
        }

        let mut desired = BTreeMap::new();
        for t in &input.desired_traits {
            if t.trait_id.0.trim().is_empty() {
                return Err(IntakeError::BlankTraitId);
            }
            if t.description.trim().is_empty() {
                return Err(IntakeError::BlankTraitDescription);
            }
            if let Some(existing_desc) = desired.get(&t.trait_id.0) {
                if existing_desc != &t.description {
                    return Err(IntakeError::ConflictingDuplicateTrait);
                }
            } else {
                desired.insert(t.trait_id.0.clone(), t.description.clone());
            }
        }

        let mut undesired = BTreeMap::new();
        for t in &input.undesired_traits {
            if t.trait_id.0.trim().is_empty() {
                return Err(IntakeError::BlankTraitId);
            }
            if t.description.trim().is_empty() {
                return Err(IntakeError::BlankTraitDescription);
            }
            if let Some(existing_desc) = undesired.get(&t.trait_id.0) {
                if existing_desc != &t.description {
                    return Err(IntakeError::ConflictingDuplicateTrait);
                }
            } else {
                undesired.insert(t.trait_id.0.clone(), t.description.clone());
            }
        }

        for d in desired.keys() {
            if undesired.contains_key(d) {
                return Ok(Err(ReferenceConflict {
                    reference_id: input.reference_id.clone(),
                    trait_id: TraitId(d.clone()),
                    reason: "Trait is both desired and undesired on the same reference".into(),
                }));
            }
        }

        Ok(Ok(ProjectReference {
            reference_id: input.reference_id.clone(),
            locator: input.locator.clone(),
            selected_desired_traits: desired,
            selected_undesired_traits: undesired,
            provenance: input.provenance.clone(),
        }))
    }

    pub fn promote_reference_trait(
        project_reference: &ProjectReference,
        trait_id: &TraitId,
        target_category: PromotionTargetCategory,
        new_item_id: ItemId,
        decision_provenance: Provenance,
    ) -> Result<SemanticItem, IntakeError> {
        if decision_provenance.source_id.trim().is_empty() {
            return Err(IntakeError::InvalidDecisionProvenance);
        }

        // Check if undesired
        if project_reference
            .selected_undesired_traits
            .contains_key(&trait_id.0)
        {
            return Err(IntakeError::CannotPromoteUndesiredTrait);
        }

        // Find in desired
        let description = project_reference
            .selected_desired_traits
            .get(&trait_id.0)
            .ok_or(IntakeError::UnknownTrait)?;

        // Ensure provenance preserves source reference and trait, and the explicit decision
        let provenance = Provenance {
            category: ProvenanceCategory::ReferenceDerived,
            source_id: project_reference.reference_id.0.clone(),
            derived_from: Some(trait_id.0.clone()),
            authorization: Some(Box::new(decision_provenance)),
        };

        Ok(SemanticItem {
            item_id: new_item_id,
            category: target_category.into(),
            description: description.clone(),
            provenance,
        })
    }
}
