use serde::{Deserialize, Serialize};

use crate::project_contract::{
    ItemId, ProjectReference, Provenance, ProvenanceCategory, ReferenceId, SemanticCategory,
    SemanticItem,
};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum IntakeError {
    BlankTraitId,
    BlankTraitDescription,
    BlankReferenceId,
    BlankLocator,
    UnknownReference,
    UnknownTrait,
    CannotPromoteUndesiredTrait,
    MissingTargetCategory,
    InvalidTargetCategory,
    DuplicateTargetItemId,
    ConflictDesiredAndUndesired(String, String),
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

        let mut desired = BTreeSet::new();
        for t in &input.desired_traits {
            if t.trait_id.0.trim().is_empty() {
                return Err(IntakeError::BlankTraitId);
            }
            if t.description.trim().is_empty() {
                return Err(IntakeError::BlankTraitDescription);
            }
            desired.insert(t.trait_id.0.clone());
        }

        let mut undesired = BTreeSet::new();
        for t in &input.undesired_traits {
            if t.trait_id.0.trim().is_empty() {
                return Err(IntakeError::BlankTraitId);
            }
            if t.description.trim().is_empty() {
                return Err(IntakeError::BlankTraitDescription);
            }
            undesired.insert(t.trait_id.0.clone());
        }

        for d in &desired {
            if undesired.contains(d) {
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
        input: &ReferenceInput,
        trait_id: &TraitId,
        target_category: SemanticCategory,
        new_item_id: ItemId,
        _decision_provenance: Provenance,
    ) -> Result<SemanticItem, IntakeError> {
        if input.reference_id.0.trim().is_empty() {
            return Err(IntakeError::UnknownReference); // Or BlankReferenceId
        }

        // Validate target category
        match target_category {
            SemanticCategory::UserRequirement
            | SemanticCategory::Preference
            | SemanticCategory::Assumption
            | SemanticCategory::TechnicalConstraint => {}
            _ => return Err(IntakeError::InvalidTargetCategory),
        }

        // Check if undesired
        if input
            .undesired_traits
            .iter()
            .any(|t| t.trait_id == *trait_id)
        {
            return Err(IntakeError::CannotPromoteUndesiredTrait);
        }

        // Find in desired
        let found_trait = input
            .desired_traits
            .iter()
            .find(|t| t.trait_id == *trait_id)
            .ok_or(IntakeError::UnknownTrait)?;

        // Ensure provenance preserves source reference and trait
        // "Use existing: ProvenanceCategory::ReferenceDerived and source/derived_from fields where sufficient."
        // source_id = reference_id, derived_from = Some(trait_id)
        let provenance = Provenance {
            category: ProvenanceCategory::ReferenceDerived,
            source_id: input.reference_id.0.clone(),
            derived_from: Some(found_trait.trait_id.0.clone()),
        };

        Ok(SemanticItem {
            item_id: new_item_id,
            category: target_category,
            description: found_trait.description.clone(),
            provenance,
        })
    }
}
