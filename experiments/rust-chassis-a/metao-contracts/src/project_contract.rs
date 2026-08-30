use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractError {
    EmptyIdentity(&'static str),
    VersionZero,
    VersionRegression,
    SameVersionReplacement,
    SkippedVersion,
    DuplicateItemId(String),
    DuplicateReferenceId(String),
    EmptyGoal,
    EmptyRequiredItem(&'static str),
    SelfSupersession,
    PredecessorBindingMismatch,
    InvalidProvenance,
    SemanticCategoryMismatch,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ProjectId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ContractId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ItemId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ReferenceId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProvenanceCategory {
    UserExplicit,
    UserConfirmed,
    ReferenceDerived,
    MetaoAssumption,
    MetaoRecommendation,
    SystemDefault,
    ImportedExistingConstraint,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Provenance {
    pub category: ProvenanceCategory,
    pub source_id: String,
    pub derived_from: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum SemanticCategory {
    UserRequirement,
    Assumption,
    Reference,
    Preference,
    TechnicalConstraint,
    NonFunctionalRequirement,
    AcceptanceCriterion,
    AcceptanceTest,
    HumanDecision,
    UnresolvedItem,
    OutOfScope,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SemanticItem {
    pub item_id: ItemId,
    pub category: SemanticCategory,
    pub description: String,
    pub provenance: Provenance,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectReference {
    pub reference_id: ReferenceId,
    pub locator: String,
    pub selected_desired_traits: BTreeSet<String>,
    pub selected_undesired_traits: BTreeSet<String>,
    pub provenance: Provenance,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectContractBinding {
    pub project_id: ProjectId,
    pub contract_id: ContractId,
    pub version: u32,
    pub contract_digest: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContractLineage {
    pub predecessor: ProjectContractBinding,
    pub revision_rationale: String,
    pub revision_provenance: Provenance,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectContract {
    pub project_id: ProjectId,
    pub contract_id: ContractId,
    pub version: u32,
    pub project_goal: String,
    pub target_users: BTreeSet<String>,

    pub required_capabilities: BTreeMap<ItemId, SemanticItem>,
    pub required_surfaces: BTreeMap<ItemId, SemanticItem>,
    pub user_requirements: BTreeMap<ItemId, SemanticItem>,
    pub technical_constraints: BTreeMap<ItemId, SemanticItem>,
    pub preferences: BTreeMap<ItemId, SemanticItem>,
    pub assumptions: BTreeMap<ItemId, SemanticItem>,
    pub out_of_scope: BTreeMap<ItemId, SemanticItem>,
    pub non_functional_requirements: BTreeMap<ItemId, SemanticItem>,
    pub acceptance_criteria: BTreeMap<ItemId, SemanticItem>,
    pub acceptance_tests: BTreeMap<ItemId, SemanticItem>,
    pub definition_of_done: BTreeMap<ItemId, SemanticItem>,
    pub human_decisions: BTreeMap<ItemId, SemanticItem>,
    pub unresolved_items: BTreeMap<ItemId, SemanticItem>,

    pub references: BTreeMap<ReferenceId, ProjectReference>,

    pub lineage: Option<ContractLineage>,
    pub contract_digest: String,
}

impl ProjectContract {
    pub fn new(
        project_id: ProjectId,
        contract_id: ContractId,
        project_goal: String,
        target_users: BTreeSet<String>,
        mut items: Vec<SemanticItem>,
        mut references: Vec<ProjectReference>,
    ) -> Result<Self, ContractError> {
        if project_id.0.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("project_id"));
        }
        if contract_id.0.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("contract_id"));
        }
        if project_goal.trim().is_empty() {
            return Err(ContractError::EmptyGoal);
        }

        let mut contract = Self {
            project_id,
            contract_id,
            version: 1,
            project_goal,
            target_users,
            required_capabilities: BTreeMap::new(),
            required_surfaces: BTreeMap::new(),
            user_requirements: BTreeMap::new(),
            technical_constraints: BTreeMap::new(),
            preferences: BTreeMap::new(),
            assumptions: BTreeMap::new(),
            out_of_scope: BTreeMap::new(),
            non_functional_requirements: BTreeMap::new(),
            acceptance_criteria: BTreeMap::new(),
            acceptance_tests: BTreeMap::new(),
            definition_of_done: BTreeMap::new(),
            human_decisions: BTreeMap::new(),
            unresolved_items: BTreeMap::new(),
            references: BTreeMap::new(),
            lineage: None,
            contract_digest: String::new(),
        };

        for item in items.drain(..) {
            contract.add_item(item)?;
        }
        for reference in references.drain(..) {
            contract.add_reference(reference)?;
        }

        contract.contract_digest = contract.calculate_digest();
        Ok(contract)
    }

    fn add_item(&mut self, item: SemanticItem) -> Result<(), ContractError> {
        if self.contains_item(&item.item_id) {
            return Err(ContractError::DuplicateItemId(item.item_id.0.clone()));
        }
        match item.category {
            SemanticCategory::UserRequirement => {
                self.user_requirements.insert(item.item_id.clone(), item);
            }
            SemanticCategory::Assumption => {
                self.assumptions.insert(item.item_id.clone(), item);
            }
            SemanticCategory::Reference => return Err(ContractError::SemanticCategoryMismatch), // Handled separately
            SemanticCategory::Preference => {
                self.preferences.insert(item.item_id.clone(), item);
            }
            SemanticCategory::TechnicalConstraint => {
                self.technical_constraints
                    .insert(item.item_id.clone(), item);
            }
            SemanticCategory::NonFunctionalRequirement => {
                self.non_functional_requirements
                    .insert(item.item_id.clone(), item);
            }
            SemanticCategory::AcceptanceCriterion => {
                self.acceptance_criteria.insert(item.item_id.clone(), item);
            }
            SemanticCategory::AcceptanceTest => {
                self.acceptance_tests.insert(item.item_id.clone(), item);
            }
            SemanticCategory::HumanDecision => {
                self.human_decisions.insert(item.item_id.clone(), item);
            }
            SemanticCategory::UnresolvedItem => {
                self.unresolved_items.insert(item.item_id.clone(), item);
            }
            SemanticCategory::OutOfScope => {
                self.out_of_scope.insert(item.item_id.clone(), item);
            }
        }
        Ok(())
    }

    fn add_reference(&mut self, reference: ProjectReference) -> Result<(), ContractError> {
        if self.references.contains_key(&reference.reference_id) {
            return Err(ContractError::DuplicateReferenceId(
                reference.reference_id.0.clone(),
            ));
        }
        self.references
            .insert(reference.reference_id.clone(), reference);
        Ok(())
    }

    fn contains_item(&self, id: &ItemId) -> bool {
        self.required_capabilities.contains_key(id)
            || self.required_surfaces.contains_key(id)
            || self.user_requirements.contains_key(id)
            || self.technical_constraints.contains_key(id)
            || self.preferences.contains_key(id)
            || self.assumptions.contains_key(id)
            || self.out_of_scope.contains_key(id)
            || self.non_functional_requirements.contains_key(id)
            || self.acceptance_criteria.contains_key(id)
            || self.acceptance_tests.contains_key(id)
            || self.definition_of_done.contains_key(id)
            || self.human_decisions.contains_key(id)
            || self.unresolved_items.contains_key(id)
    }

    pub fn binding(&self) -> ProjectContractBinding {
        ProjectContractBinding {
            project_id: self.project_id.clone(),
            contract_id: self.contract_id.clone(),
            version: self.version,
            contract_digest: self.contract_digest.clone(),
        }
    }

    pub fn calculate_digest(&self) -> String {
        let mut clone = self.clone();
        clone.contract_digest = String::new();
        let serialized = serde_json::to_string(&clone).expect("Serialization failed");
        let mut hasher = Sha256::new();
        hasher.update(serialized.as_bytes());
        let result = hasher.finalize();
        result.iter().map(|b| format!("{:02x}", b)).collect()
    }

    pub fn revise_contract(
        previous: &ProjectContract,
        project_goal: String,
        target_users: BTreeSet<String>,
        items: Vec<SemanticItem>,
        references: Vec<ProjectReference>,
        revision_rationale: String,
        revision_provenance: Provenance,
    ) -> Result<Self, ContractError> {
        if previous.version < 1 {
            return Err(ContractError::VersionZero);
        }

        let mut new_contract = Self::new(
            previous.project_id.clone(),
            previous.contract_id.clone(),
            project_goal,
            target_users,
            items,
            references,
        )?;

        new_contract.version = previous.version + 1;
        new_contract.lineage = Some(ContractLineage {
            predecessor: previous.binding(),
            revision_rationale,
            revision_provenance,
        });

        new_contract.contract_digest = new_contract.calculate_digest();
        Ok(new_contract)
    }
}
