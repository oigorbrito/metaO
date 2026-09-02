use metao_contracts::{ItemId, ProjectContract, ProjectContractBinding};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct WorkUnitId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkUnit {
    pub work_unit_id: WorkUnitId,
    pub requirement_ids: BTreeSet<ItemId>,
    pub dependency_ids: BTreeSet<WorkUnitId>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkGraph {
    binding: ProjectContractBinding,
    units: BTreeMap<WorkUnitId, WorkUnit>,
    graph_digest: String,
    sealed: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum PlanningError {
    EmptyWorkUnitId,
    EmptyRequirementSet(WorkUnitId),
    UnknownRequirement(ItemId),
    UnknownDependency { unit: WorkUnitId, dependency: WorkUnitId },
    SelfDependency(WorkUnitId),
    DependencyCycle,
    BindingMismatch,
    GraphNotSealed,
    GraphDigestMismatch,
    UnitNotFound(WorkUnitId),
    PrerequisiteNotAccepted(WorkUnitId),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DispatchAuthorization {
    pub binding: ProjectContractBinding,
    pub work_unit_id: WorkUnitId,
    pub graph_digest: String,
}

impl WorkGraph {
    pub fn draft(contract: &ProjectContract, units: Vec<WorkUnit>) -> Result<Self, PlanningError> {
        let dto: metao_contracts::ProjectContractDto = contract.clone().into();
        let binding = ProjectContractBinding {
            project_id: dto.project_id.clone(),
            contract_id: dto.contract_id.clone(),
            version: dto.version,
            contract_digest: dto.contract_digest.clone(),
        };
        let requirements = all_requirement_ids(&dto);
        let mut map = BTreeMap::new();

        for unit in units {
            if unit.work_unit_id.0.trim().is_empty() {
                return Err(PlanningError::EmptyWorkUnitId);
            }
            if unit.requirement_ids.is_empty() {
                return Err(PlanningError::EmptyRequirementSet(unit.work_unit_id));
            }
            for requirement_id in &unit.requirement_ids {
                if !requirements.contains(requirement_id) {
                    return Err(PlanningError::UnknownRequirement(requirement_id.clone()));
                }
            }
            if unit.dependency_ids.contains(&unit.work_unit_id) {
                return Err(PlanningError::SelfDependency(unit.work_unit_id));
            }
            if map.insert(unit.work_unit_id.clone(), unit).is_some() {
                return Err(PlanningError::DependencyCycle);
            }
        }

        let mut graph = Self {
            binding,
            units: map,
            graph_digest: String::new(),
            sealed: false,
        };
        graph.validate_dag()?;
        graph.graph_digest = graph.calculate_digest();
        Ok(graph)
    }

    pub fn binding(&self) -> &ProjectContractBinding {
        &self.binding
    }

    pub fn units(&self) -> &BTreeMap<WorkUnitId, WorkUnit> {
        &self.units
    }

    pub fn graph_digest(&self) -> &str {
        &self.graph_digest
    }

    pub fn validate_dag(&self) -> Result<(), PlanningError> {
        for (unit_id, unit) in &self.units {
            for dependency in &unit.dependency_ids {
                if !self.units.contains_key(dependency) {
                    return Err(PlanningError::UnknownDependency {
                        unit: unit_id.clone(),
                        dependency: dependency.clone(),
                    });
                }
            }
        }

        let mut visiting = BTreeSet::new();
        let mut visited = BTreeSet::new();
        for unit_id in self.units.keys() {
            if !visited.contains(unit_id) {
                self.visit(unit_id, &mut visiting, &mut visited)?;
            }
        }
        Ok(())
    }

    fn visit(
        &self,
        unit_id: &WorkUnitId,
        visiting: &mut BTreeSet<WorkUnitId>,
        visited: &mut BTreeSet<WorkUnitId>,
    ) -> Result<(), PlanningError> {
        if visiting.contains(unit_id) {
            return Err(PlanningError::DependencyCycle);
        }
        if visited.contains(unit_id) {
            return Ok(());
        }
        visiting.insert(unit_id.clone());
        let unit = self.units.get(unit_id).expect("validated graph node");
        for dependency in &unit.dependency_ids {
            self.visit(dependency, visiting, visited)?;
        }
        visiting.remove(unit_id);
        visited.insert(unit_id.clone());
        Ok(())
    }

    pub fn seal(mut self) -> Result<Self, PlanningError> {
        self.validate_dag()?;
        self.graph_digest = self.calculate_digest();
        self.sealed = true;
        Ok(self)
    }

    pub fn is_sealed(&self) -> bool {
        self.sealed
    }

    pub fn authorize_dispatch(
        &self,
        work_unit_id: &WorkUnitId,
        accepted_units: &BTreeSet<WorkUnitId>,
        contract: &ProjectContract,
    ) -> Result<DispatchAuthorization, PlanningError> {
        if !self.sealed {
            return Err(PlanningError::GraphNotSealed);
        }
        let dto: metao_contracts::ProjectContractDto = contract.clone().into();
        let current = ProjectContractBinding {
            project_id: dto.project_id,
            contract_id: dto.contract_id,
            version: dto.version,
            contract_digest: dto.contract_digest,
        };
        if self.binding != current {
            return Err(PlanningError::BindingMismatch);
        }
        if self.calculate_digest() != self.graph_digest {
            return Err(PlanningError::GraphDigestMismatch);
        }
        let Some(unit) = self.units.get(work_unit_id) else {
            return Err(PlanningError::UnitNotFound(work_unit_id.clone()));
        };
        for dependency in &unit.dependency_ids {
            if !accepted_units.contains(dependency) {
                return Err(PlanningError::PrerequisiteNotAccepted(dependency.clone()));
            }
        }
        Ok(DispatchAuthorization {
            binding: self.binding.clone(),
            work_unit_id: work_unit_id.clone(),
            graph_digest: self.graph_digest.clone(),
        })
    }

    fn calculate_digest(&self) -> String {
        let canonical = serde_json::to_vec(&(&self.binding, &self.units)).expect("serializable graph");
        let digest = Sha256::digest(canonical);
        format!("sha256:{digest:x}")
    }
}

fn all_requirement_ids(dto: &metao_contracts::ProjectContractDto) -> BTreeSet<ItemId> {
    let mut ids = BTreeSet::new();
    for map in [
        &dto.required_capabilities,
        &dto.required_surfaces,
        &dto.user_requirements,
        &dto.technical_constraints,
        &dto.preferences,
        &dto.assumptions,
        &dto.out_of_scope,
        &dto.non_functional_requirements,
        &dto.acceptance_criteria,
        &dto.acceptance_tests,
        &dto.definition_of_done,
        &dto.human_decisions,
        &dto.unresolved_items,
    ] {
        ids.extend(map.keys().cloned());
    }
    ids
}

#[cfg(test)]
mod tests {
    use super::*;
    use metao_contracts::{
        Provenance, ProvenanceCategory, ProjectContract, SemanticCategory, SemanticItem,
    };

    fn contract() -> ProjectContract {
        ProjectContract::new(
            "p".into(),
            "c".into(),
            "goal".into(),
            BTreeSet::new(),
            vec![SemanticItem {
                item_id: ItemId("req".into()),
                category: SemanticCategory::UserRequirement,
                description: "required behavior".into(),
                provenance: Provenance {
                    category: ProvenanceCategory::UserExplicit,
                    source_id: "user".into(),
                    derived_from: None,
                    authorization: None,
                },
            }],
            vec![],
        )
        .expect("valid contract")
    }

    fn unit(id: &str, deps: &[&str]) -> WorkUnit {
        WorkUnit {
            work_unit_id: WorkUnitId(id.into()),
            requirement_ids: BTreeSet::from([ItemId("req".into())]),
            dependency_ids: deps.iter().map(|id| WorkUnitId((*id).into())).collect(),
        }
    }

    #[test]
    fn ac06_happy_path_seals_and_authorizes_ready_unit() {
        let contract = contract();
        let graph = WorkGraph::draft(&contract, vec![unit("a", &[]), unit("b", &["a"])])
            .expect("valid draft")
            .seal()
            .expect("sealed graph");
        let auth = graph
            .authorize_dispatch(&WorkUnitId("b".into()), &BTreeSet::from([WorkUnitId("a".into())]), &contract)
            .expect("dispatch authorized");
        assert_eq!(auth.work_unit_id, WorkUnitId("b".into()));
        assert_eq!(auth.graph_digest, graph.graph_digest());
        assert!(graph.is_sealed());
    }

    #[test]
    fn ac06_cycle_is_rejected() {
        let contract = contract();
        let result = WorkGraph::draft(&contract, vec![unit("a", &["b"]), unit("b", &["a"])])
            .and_then(WorkGraph::seal);
        assert_eq!(result, Err(PlanningError::DependencyCycle));
    }

    #[test]
    fn ac06_unknown_dependency_is_rejected() {
        let contract = contract();
        let result = WorkGraph::draft(&contract, vec![unit("a", &["missing"])])
            .and_then(WorkGraph::seal);
        assert_eq!(
            result,
            Err(PlanningError::UnknownDependency {
                unit: WorkUnitId("a".into()),
                dependency: WorkUnitId("missing".into()),
            })
        );
    }

    #[test]
    fn ac06_dispatch_fails_closed_without_accepted_prerequisite() {
        let contract = contract();
        let graph = WorkGraph::draft(&contract, vec![unit("a", &[]), unit("b", &["a"])])
            .expect("valid draft")
            .seal()
            .expect("sealed graph");
        let result = graph.authorize_dispatch(&WorkUnitId("b".into()), &BTreeSet::new(), &contract);
        assert_eq!(
            result,
            Err(PlanningError::PrerequisiteNotAccepted(WorkUnitId("a".into())))
        );
    }
}
