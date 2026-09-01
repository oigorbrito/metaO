use crate::clarification_policy::{
    apply_explicit_resolution, ClarificationAction, ClarificationPolicy, ExplicitResolution,
    UnresolvedDiscoveryItem,
};
use crate::project_contract::{
    ProjectContract, ProjectContractBinding, ProjectContractDto, Provenance,
};
use crate::tech_stack_intake::TechnicalPreferenceProfile;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DiscoveryState {
    IntentReceived,
    NeedsClarification,
    ReferenceIntake,
    TechnicalIntake,
    SpecReady,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DiscoveryCoordinatorError {
    DuplicateDiscoveryItem(String),
    UnknownResolution(String),
    UnexpectedResolution(String),
    InvalidClarification(String),
    InvalidTechnicalProfile,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveryBlocker {
    pub blocker_id: String,
    pub reason: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveryAssumptionRecord {
    pub source_item_id: String,
    pub description: String,
    pub rationale: String,
    pub provenance: Provenance,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveryTransition {
    pub sequence: u64,
    pub from: DiscoveryState,
    pub to: DiscoveryState,
    pub reason: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveryCoordinatorInput {
    pub contract: ProjectContract,
    pub discovery_items: Vec<UnresolvedDiscoveryItem>,
    pub explicit_resolutions: BTreeMap<String, ExplicitResolution>,
    pub reference_intake_pending: bool,
    pub technical_profile: Option<TechnicalPreferenceProfile>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveryEvaluation {
    pub binding: ProjectContractBinding,
    pub state: DiscoveryState,
    pub blockers: Vec<DiscoveryBlocker>,
    pub assumptions: Vec<DiscoveryAssumptionRecord>,
    pub transitions: Vec<DiscoveryTransition>,
}
impl DiscoveryEvaluation {
    pub fn applies_to(&self, binding: &ProjectContractBinding) -> bool {
        &self.binding == binding
    }
}
pub struct DiscoveryCoordinator;

impl DiscoveryCoordinator {
    pub fn evaluate(
        input: &DiscoveryCoordinatorInput,
    ) -> Result<DiscoveryEvaluation, DiscoveryCoordinatorError> {
        if let Some(profile) = &input.technical_profile {
            profile
                .validate()
                .map_err(|_| DiscoveryCoordinatorError::InvalidTechnicalProfile)?;
        }
        let mut items_by_id = BTreeMap::new();
        for item in &input.discovery_items {
            if items_by_id.insert(item.item_id.clone(), item).is_some() {
                return Err(DiscoveryCoordinatorError::DuplicateDiscoveryItem(
                    item.item_id.clone(),
                ));
            }
        }
        for resolution_id in input.explicit_resolutions.keys() {
            if !items_by_id.contains_key(resolution_id) {
                return Err(DiscoveryCoordinatorError::UnknownResolution(
                    resolution_id.clone(),
                ));
            }
        }
        let mut blockers = BTreeMap::<String, String>::new();
        let mut assumptions = BTreeMap::<String, DiscoveryAssumptionRecord>::new();
        for (item_id, item) in &items_by_id {
            let decision = ClarificationPolicy::classify(item)
                .map_err(|_| DiscoveryCoordinatorError::InvalidClarification(item_id.clone()))?;
            match decision.action {
                ClarificationAction::AskHuman => {
                    if let Some(resolution) = input.explicit_resolutions.get(item_id) {
                        apply_explicit_resolution(item, &decision, resolution.clone()).map_err(
                            |_| DiscoveryCoordinatorError::InvalidClarification(item_id.clone()),
                        )?;
                    } else {
                        blockers.insert(
                            format!("discovery:{item_id}"),
                            "material or otherwise non-defaultable ambiguity remains unresolved"
                                .to_string(),
                        );
                    }
                }
                ClarificationAction::RecordSafeAssumption => {
                    if input.explicit_resolutions.contains_key(item_id) {
                        return Err(DiscoveryCoordinatorError::UnexpectedResolution(
                            item_id.clone(),
                        ));
                    }
                    let assumption = decision.assumption.ok_or_else(|| {
                        DiscoveryCoordinatorError::InvalidClarification(item_id.clone())
                    })?;
                    assumptions.insert(
                        item_id.clone(),
                        DiscoveryAssumptionRecord {
                            source_item_id: item_id.clone(),
                            description: assumption.description,
                            rationale: assumption.rationale,
                            provenance: assumption.provenance,
                        },
                    );
                }
                ClarificationAction::NoAction => {
                    if input.explicit_resolutions.contains_key(item_id) {
                        return Err(DiscoveryCoordinatorError::UnexpectedResolution(
                            item_id.clone(),
                        ));
                    }
                }
            }
        }
        let binding = input.contract.binding();
        let dto: ProjectContractDto = input.contract.clone().into();
        add_contract_readiness_blockers(&dto, &mut blockers);
        let blockers: Vec<_> = blockers
            .into_iter()
            .map(|(blocker_id, reason)| DiscoveryBlocker { blocker_id, reason })
            .collect();
        let assumptions: Vec<_> = assumptions.into_values().collect();
        let state = if !blockers.is_empty() {
            DiscoveryState::NeedsClarification
        } else if input.reference_intake_pending {
            DiscoveryState::ReferenceIntake
        } else if input.technical_profile.is_none() {
            DiscoveryState::TechnicalIntake
        } else {
            DiscoveryState::SpecReady
        };
        let transitions = vec![DiscoveryTransition {
            sequence: 1,
            from: DiscoveryState::IntentReceived,
            to: state,
            reason: transition_reason(state).to_string(),
        }];
        Ok(DiscoveryEvaluation {
            binding,
            state,
            blockers,
            assumptions,
            transitions,
        })
    }
}

fn add_contract_readiness_blockers(
    dto: &ProjectContractDto,
    blockers: &mut BTreeMap<String, String>,
) {
    for item_id in dto.unresolved_items.keys() {
        blockers.insert(
            format!("contract-unresolved:{}", item_id.0),
            "ProjectContract contains an unresolved semantic item".to_string(),
        );
    }
    let has_scope = !dto.required_capabilities.is_empty()
        || !dto.required_surfaces.is_empty()
        || !dto.user_requirements.is_empty();
    if !has_scope {
        blockers.insert(
            "contract:scope".to_string(),
            "ProjectContract lacks explicit required scope for planning".to_string(),
        );
    }
    let has_acceptance = !dto.acceptance_criteria.is_empty() || !dto.acceptance_tests.is_empty();
    if !has_acceptance {
        blockers.insert(
            "contract:acceptance".to_string(),
            "ProjectContract lacks explicit acceptance criteria or tests".to_string(),
        );
    }
    if dto.definition_of_done.is_empty() {
        blockers.insert(
            "contract:definition-of-done".to_string(),
            "ProjectContract lacks an explicit Definition of Done".to_string(),
        );
    }
}

fn transition_reason(state: DiscoveryState) -> &'static str {
    match state {
        DiscoveryState::IntentReceived => "intent received",
        DiscoveryState::NeedsClarification => {
            "one or more material ProjectContract/discovery blockers remain"
        }
        DiscoveryState::ReferenceIntake => "reference intake is explicitly pending",
        DiscoveryState::TechnicalIntake => "technical decision mode/profile is not yet recorded",
        DiscoveryState::SpecReady => {
            "contract scope, acceptance, completion and discovery inputs are ready for planning"
        }
    }
}

pub fn assumption_source_ids(evaluation: &DiscoveryEvaluation) -> BTreeSet<String> {
    evaluation
        .assumptions
        .iter()
        .map(|record| record.source_item_id.clone())
        .collect()
}
