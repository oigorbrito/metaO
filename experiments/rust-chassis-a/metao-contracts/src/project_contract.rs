use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

use std::fmt;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractError {
    EmptyIdentity(&'static str),
    VersionZero,
    DuplicateItemId(String),
    DuplicateReferenceId(String),
    EmptyGoal,
    EmptyDescription,
    InvalidProvenance,
    ProvenanceAuthorizationDepthExceeded,
    InvalidBindingDigest,
    InvalidVersionLineage,
    InvalidPredecessorBinding,
    EmptyRevisionRationale,
    InvalidReferenceTrait(&'static str),
    ConflictingReferenceTrait(String),
}

impl fmt::Display for ContractError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
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

const MAX_PROVENANCE_AUTHORIZATION_DEPTH: usize = 8;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Provenance {
    pub category: ProvenanceCategory,
    pub source_id: String,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub derived_from: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub authorization: Option<Box<Provenance>>,
}

impl Provenance {
    pub fn validate(&self) -> Result<(), ContractError> {
        self.validate_internal(0)
    }

    fn validate_internal(&self, depth: usize) -> Result<(), ContractError> {
        if depth > MAX_PROVENANCE_AUTHORIZATION_DEPTH {
            return Err(ContractError::ProvenanceAuthorizationDepthExceeded);
        }
        if self.source_id.trim().is_empty() {
            return Err(ContractError::InvalidProvenance);
        }
        if let Some(auth) = &self.authorization {
            auth.validate_internal(depth + 1)?;
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum SemanticCategory {
    UserRequirement,
    Assumption,
    Preference,
    TechnicalConstraint,
    RequiredCapability,
    RequiredSurface,
    NonFunctionalRequirement,
    AcceptanceCriterion,
    AcceptanceTest,
    DefinitionOfDone,
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
    pub selected_desired_traits: BTreeMap<String, String>,
    pub selected_undesired_traits: BTreeMap<String, String>,
    pub provenance: Provenance,
}

impl ProjectReference {
    pub fn validate(&self) -> Result<(), ContractError> {
        if self.reference_id.0.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("reference_id"));
        }
        if self.locator.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("locator"));
        }
        self.provenance.validate()?;

        for (id, desc) in &self.selected_desired_traits {
            if id.trim().is_empty() {
                return Err(ContractError::InvalidReferenceTrait(
                    "Blank desired trait id",
                ));
            }
            if desc.trim().is_empty() {
                return Err(ContractError::InvalidReferenceTrait(
                    "Blank desired trait description",
                ));
            }
        }
        for (id, desc) in &self.selected_undesired_traits {
            if id.trim().is_empty() {
                return Err(ContractError::InvalidReferenceTrait(
                    "Blank undesired trait id",
                ));
            }
            if desc.trim().is_empty() {
                return Err(ContractError::InvalidReferenceTrait(
                    "Blank undesired trait description",
                ));
            }
        }
        for id in self.selected_desired_traits.keys() {
            if self.selected_undesired_traits.contains_key(id) {
                return Err(ContractError::ConflictingReferenceTrait(id.clone()));
            }
        }
        Ok(())
    }
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
pub struct ProjectContractDto {
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

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "ProjectContractDto", into = "ProjectContractDto")]
pub struct ProjectContract {
    project_id: ProjectId,
    contract_id: ContractId,
    version: u32,
    project_goal: String,
    target_users: BTreeSet<String>,

    required_capabilities: BTreeMap<ItemId, SemanticItem>,
    required_surfaces: BTreeMap<ItemId, SemanticItem>,
    user_requirements: BTreeMap<ItemId, SemanticItem>,
    technical_constraints: BTreeMap<ItemId, SemanticItem>,
    preferences: BTreeMap<ItemId, SemanticItem>,
    assumptions: BTreeMap<ItemId, SemanticItem>,
    out_of_scope: BTreeMap<ItemId, SemanticItem>,
    non_functional_requirements: BTreeMap<ItemId, SemanticItem>,
    acceptance_criteria: BTreeMap<ItemId, SemanticItem>,
    acceptance_tests: BTreeMap<ItemId, SemanticItem>,
    definition_of_done: BTreeMap<ItemId, SemanticItem>,
    human_decisions: BTreeMap<ItemId, SemanticItem>,
    unresolved_items: BTreeMap<ItemId, SemanticItem>,

    references: BTreeMap<ReferenceId, ProjectReference>,

    lineage: Option<ContractLineage>,
    contract_digest: String,
}

impl From<ProjectContract> for ProjectContractDto {
    fn from(contract: ProjectContract) -> Self {
        Self {
            project_id: contract.project_id,
            contract_id: contract.contract_id,
            version: contract.version,
            project_goal: contract.project_goal,
            target_users: contract.target_users,
            required_capabilities: contract.required_capabilities,
            required_surfaces: contract.required_surfaces,
            user_requirements: contract.user_requirements,
            technical_constraints: contract.technical_constraints,
            preferences: contract.preferences,
            assumptions: contract.assumptions,
            out_of_scope: contract.out_of_scope,
            non_functional_requirements: contract.non_functional_requirements,
            acceptance_criteria: contract.acceptance_criteria,
            acceptance_tests: contract.acceptance_tests,
            definition_of_done: contract.definition_of_done,
            human_decisions: contract.human_decisions,
            unresolved_items: contract.unresolved_items,
            references: contract.references,
            lineage: contract.lineage,
            contract_digest: contract.contract_digest,
        }
    }
}

impl TryFrom<ProjectContractDto> for ProjectContract {
    type Error = ContractError;

    fn try_from(dto: ProjectContractDto) -> Result<Self, Self::Error> {
        let mut items = vec![];
        items.extend(dto.required_capabilities.into_values());
        items.extend(dto.required_surfaces.into_values());
        items.extend(dto.user_requirements.into_values());
        items.extend(dto.technical_constraints.into_values());
        items.extend(dto.preferences.into_values());
        items.extend(dto.assumptions.into_values());
        items.extend(dto.out_of_scope.into_values());
        items.extend(dto.non_functional_requirements.into_values());
        items.extend(dto.acceptance_criteria.into_values());
        items.extend(dto.acceptance_tests.into_values());
        items.extend(dto.definition_of_done.into_values());
        items.extend(dto.human_decisions.into_values());
        items.extend(dto.unresolved_items.into_values());

        let references: Vec<_> = dto.references.into_values().collect();

        let mut valid_target_users = BTreeSet::new();
        for tu in dto.target_users {
            if tu.trim().is_empty() {
                return Err(ContractError::EmptyIdentity("target_user"));
            }
            valid_target_users.insert(tu);
        }

        let contract = if let Some(lineage) = dto.lineage {
            if dto.version < 2 {
                return Err(ContractError::InvalidVersionLineage);
            }
            if lineage.predecessor.project_id != dto.project_id {
                return Err(ContractError::InvalidPredecessorBinding);
            }
            if lineage.predecessor.contract_id != dto.contract_id {
                return Err(ContractError::InvalidPredecessorBinding);
            }
            if lineage.predecessor.version + 1 != dto.version {
                return Err(ContractError::InvalidPredecessorBinding);
            }
            if lineage.predecessor.contract_digest.trim().is_empty() {
                return Err(ContractError::InvalidPredecessorBinding);
            }
            if lineage.revision_rationale.trim().is_empty() {
                return Err(ContractError::EmptyRevisionRationale);
            }
            lineage.revision_provenance.validate()?;

            let mut c = Self::new_internal(
                dto.project_id,
                dto.contract_id,
                dto.project_goal,
                valid_target_users,
                items,
                references,
            )?;
            c.version = dto.version;
            c.lineage = Some(lineage);
            c.contract_digest = c.calculate_digest();
            c
        } else {
            if dto.version != 1 {
                return Err(ContractError::InvalidVersionLineage);
            }
            Self::new(
                dto.project_id,
                dto.contract_id,
                dto.project_goal,
                valid_target_users,
                items,
                references,
            )?
        };

        if contract.contract_digest != dto.contract_digest {
            return Err(ContractError::InvalidBindingDigest);
        }
        Ok(contract)
    }
}

impl ProjectContract {
    fn new_internal(
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
        for tu in &target_users {
            if tu.trim().is_empty() {
                return Err(ContractError::EmptyIdentity("target_user"));
            }
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

        Ok(contract)
    }

    pub fn new(
        project_id: ProjectId,
        contract_id: ContractId,
        project_goal: String,
        target_users: BTreeSet<String>,
        items: Vec<SemanticItem>,
        references: Vec<ProjectReference>,
    ) -> Result<Self, ContractError> {
        let mut contract = Self::new_internal(
            project_id,
            contract_id,
            project_goal,
            target_users,
            items,
            references,
        )?;
        contract.contract_digest = contract.calculate_digest();
        Ok(contract)
    }

    fn add_item(&mut self, item: SemanticItem) -> Result<(), ContractError> {
        if item.item_id.0.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("item_id"));
        }
        if item.description.trim().is_empty() {
            return Err(ContractError::EmptyDescription);
        }
        item.provenance.validate()?;

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
            SemanticCategory::Preference => {
                self.preferences.insert(item.item_id.clone(), item);
            }
            SemanticCategory::TechnicalConstraint => {
                self.technical_constraints
                    .insert(item.item_id.clone(), item);
            }
            SemanticCategory::RequiredCapability => {
                self.required_capabilities
                    .insert(item.item_id.clone(), item);
            }
            SemanticCategory::RequiredSurface => {
                self.required_surfaces.insert(item.item_id.clone(), item);
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
            SemanticCategory::DefinitionOfDone => {
                self.definition_of_done.insert(item.item_id.clone(), item);
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
        reference.validate()?;

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

    fn calculate_digest(&self) -> String {
        let mut clone_dto: ProjectContractDto = self.clone().into();
        clone_dto.contract_digest = String::new();
        let serialized = serde_json::to_string(&clone_dto).expect("Serialization failed");
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
        revision_provenance.validate()?;

        let mut new_contract = Self::new_internal(
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

    // Accessors
    pub fn version(&self) -> u32 {
        self.version
    }
    pub fn project_goal(&self) -> &str {
        &self.project_goal
    }
    pub fn contract_digest(&self) -> &str {
        &self.contract_digest
    }
    pub fn assumptions(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.assumptions
    }
    pub fn user_requirements(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.user_requirements
    }
    pub fn technical_constraints(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.technical_constraints
    }
    pub fn preferences(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.preferences
    }
    pub fn required_capabilities(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.required_capabilities
    }
    pub fn required_surfaces(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.required_surfaces
    }
    pub fn definition_of_done(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.definition_of_done
    }
    pub fn acceptance_criteria(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.acceptance_criteria
    }
    pub fn acceptance_tests(&self) -> &BTreeMap<ItemId, SemanticItem> {
        &self.acceptance_tests
    }
    pub fn lineage(&self) -> Option<&ContractLineage> {
        self.lineage.as_ref()
    }
}
