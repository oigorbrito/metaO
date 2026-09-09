use std::collections::{BTreeMap, BTreeSet, VecDeque};

use metao_contracts::project_contract::{ContractId, ProjectContractBinding, ProjectId};

#[derive(Clone, Debug, PartialEq, Eq)]
struct WorkNode {
    id: String,
    dependencies: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct WorkGraphProposal {
    binding: ProjectContractBinding,
    proposer: String,
    nodes: Vec<WorkNode>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct PlanningAuthority {
    actor_id: String,
    project_id: ProjectId,
    contract_id: ContractId,
    contract_version: u32,
    contract_digest: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct ValidatedWorkGraph {
    binding: ProjectContractBinding,
    nodes: BTreeMap<String, WorkNode>,
    topological_order: Vec<String>,
    sealed_by: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct DispatchAuthorization {
    project_id: ProjectId,
    contract_id: ContractId,
    contract_version: u32,
    contract_digest: String,
    graph_sealed_by: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum GraphError {
    EmptyNodeId,
    DuplicateNodeId(String),
    OrphanDependency { node: String, dependency: String },
    Cycle,
    UnauthorizedPlanner,
    BindingMismatch,
}

fn binding() -> ProjectContractBinding {
    ProjectContractBinding {
        project_id: ProjectId("project-362".to_string()),
        contract_id: ContractId("contract-362".to_string()),
        version: 7,
        contract_digest: "sha256:contract-362-v7".to_string(),
    }
}

fn authority() -> PlanningAuthority {
    let binding = binding();
    PlanningAuthority {
        actor_id: "metao-planning-authority".to_string(),
        project_id: binding.project_id,
        contract_id: binding.contract_id,
        contract_version: binding.version,
        contract_digest: binding.contract_digest,
    }
}

fn node(id: &str, dependencies: &[&str]) -> WorkNode {
    WorkNode {
        id: id.to_string(),
        dependencies: dependencies.iter().map(|value| (*value).to_string()).collect(),
    }
}

fn validate_and_seal(
    proposal: WorkGraphProposal,
    authority: &PlanningAuthority,
) -> Result<ValidatedWorkGraph, GraphError> {
    if proposal.proposer != authority.actor_id {
        return Err(GraphError::UnauthorizedPlanner);
    }

    if proposal.binding.project_id != authority.project_id
        || proposal.binding.contract_id != authority.contract_id
        || proposal.binding.version != authority.contract_version
        || proposal.binding.contract_digest != authority.contract_digest
    {
        return Err(GraphError::BindingMismatch);
    }

    let mut nodes = BTreeMap::new();
    for work in proposal.nodes {
        if work.id.trim().is_empty() {
            return Err(GraphError::EmptyNodeId);
        }
        if nodes.insert(work.id.clone(), work).is_some() {
            return Err(GraphError::DuplicateNodeId(
                nodes.keys().next_back().cloned().unwrap_or_default(),
            ));
        }
    }

    for work in nodes.values() {
        for dependency in &work.dependencies {
            if !nodes.contains_key(dependency) {
                return Err(GraphError::OrphanDependency {
                    node: work.id.clone(),
                    dependency: dependency.clone(),
                });
            }
        }
    }

    let mut incoming: BTreeMap<String, usize> = nodes
        .iter()
        .map(|(id, work)| (id.clone(), work.dependencies.len()))
        .collect();
    let mut outgoing: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for work in nodes.values() {
        for dependency in &work.dependencies {
            outgoing
                .entry(dependency.clone())
                .or_default()
                .insert(work.id.clone());
        }
    }

    let mut ready: VecDeque<String> = incoming
        .iter()
        .filter_map(|(id, count)| (*count == 0).then_some(id.clone()))
        .collect();
    let mut order = Vec::with_capacity(nodes.len());

    while let Some(id) = ready.pop_front() {
        order.push(id.clone());
        if let Some(dependents) = outgoing.get(&id) {
            for dependent in dependents {
                let count = incoming.get_mut(dependent).expect("known dependent");
                *count -= 1;
                if *count == 0 {
                    ready.push_back(dependent.clone());
                }
            }
        }
    }

    if order.len() != nodes.len() {
        return Err(GraphError::Cycle);
    }

    Ok(ValidatedWorkGraph {
        binding: proposal.binding,
        nodes,
        topological_order: order,
        sealed_by: authority.actor_id.clone(),
    })
}

fn authorize_dispatch(
    graph: &ValidatedWorkGraph,
    authority: &PlanningAuthority,
) -> Result<DispatchAuthorization, GraphError> {
    if graph.sealed_by != authority.actor_id {
        return Err(GraphError::UnauthorizedPlanner);
    }
    if graph.binding.project_id != authority.project_id
        || graph.binding.contract_id != authority.contract_id
        || graph.binding.version != authority.contract_version
        || graph.binding.contract_digest != authority.contract_digest
    {
        return Err(GraphError::BindingMismatch);
    }
    Ok(DispatchAuthorization {
        project_id: graph.binding.project_id.clone(),
        contract_id: graph.binding.contract_id.clone(),
        contract_version: graph.binding.version,
        contract_digest: graph.binding.contract_digest.clone(),
        graph_sealed_by: graph.sealed_by.clone(),
    })
}

#[test]
fn spec_ready_binding_to_authoritative_validated_immutable_workgraph_allows_dispatch() {
    let auth = authority();
    let graph = validate_and_seal(
        WorkGraphProposal {
            binding: binding(),
            proposer: auth.actor_id.clone(),
            nodes: vec![node("discover", &[]), node("implement", &["discover"]), node("verify", &["implement"])],
        },
        &auth,
    )
    .expect("authoritative graph should validate");

    assert_eq!(graph.topological_order, vec!["discover", "implement", "verify"]);
    let dispatch = authorize_dispatch(&graph, &auth).expect("validated sealed graph should authorize dispatch");
    assert_eq!(dispatch.project_id, ProjectId("project-362".to_string()));
    assert_eq!(dispatch.contract_version, 7);
    assert_eq!(dispatch.contract_digest, "sha256:contract-362-v7");
    assert_eq!(dispatch.graph_sealed_by, "metao-planning-authority");
}

#[test]
fn cycle_is_rejected_before_dispatch_authorization() {
    let auth = authority();
    let result = validate_and_seal(
        WorkGraphProposal {
            binding: binding(),
            proposer: auth.actor_id.clone(),
            nodes: vec![node("a", &["b"]), node("b", &["a"])],
        },
        &auth,
    );
    assert_eq!(result, Err(GraphError::Cycle));
}

#[test]
fn orphan_dependency_is_rejected_before_dispatch_authorization() {
    let auth = authority();
    let result = validate_and_seal(
        WorkGraphProposal {
            binding: binding(),
            proposer: auth.actor_id.clone(),
            nodes: vec![node("build", &["missing-spec"])],
        },
        &auth,
    );
    assert_eq!(
        result,
        Err(GraphError::OrphanDependency {
            node: "build".to_string(),
            dependency: "missing-spec".to_string(),
        })
    );
}

#[test]
fn duplicate_node_ids_are_rejected() {
    let auth = authority();
    let result = validate_and_seal(
        WorkGraphProposal {
            binding: binding(),
            proposer: auth.actor_id.clone(),
            nodes: vec![node("same", &[]), node("same", &[])],
        },
        &auth,
    );
    assert!(matches!(result, Err(GraphError::DuplicateNodeId(_))));
}

#[test]
fn executor_produced_decomposition_never_becomes_authoritative_automatically() {
    let auth = authority();
    let result = validate_and_seal(
        WorkGraphProposal {
            binding: binding(),
            proposer: "runtime-executor-a".to_string(),
            nodes: vec![node("executor-plan", &[])],
        },
        &auth,
    );
    assert_eq!(result, Err(GraphError::UnauthorizedPlanner));
}

#[test]
fn contract_or_spec_drift_blocks_graph_sealing_and_dispatch() {
    let auth = authority();
    let mut stale = binding();
    stale.version = 6;
    stale.contract_digest = "sha256:contract-362-v6".to_string();
    let result = validate_and_seal(
        WorkGraphProposal {
            binding: stale,
            proposer: auth.actor_id.clone(),
            nodes: vec![node("build", &[])],
        },
        &auth,
    );
    assert_eq!(result, Err(GraphError::BindingMismatch));
}

#[test]
fn sealed_graph_has_no_mutation_surface_and_dispatch_remains_bound_to_exact_snapshot() {
    let auth = authority();
    let mut proposal = WorkGraphProposal {
        binding: binding(),
        proposer: auth.actor_id.clone(),
        nodes: vec![node("one", &[])],
    };
    let graph = validate_and_seal(proposal.clone(), &auth).expect("seal graph");

    proposal.nodes.push(node("late-executor-mutation", &["one"]));

    assert_eq!(graph.nodes.len(), 1);
    assert!(!graph.nodes.contains_key("late-executor-mutation"));
    assert!(authorize_dispatch(&graph, &auth).is_ok());
}
