use metao_contracts::clarification_policy::{
    ExplicitResolution, Materiality, MaterialityReason, ResolutionKind, Reversibility,
    UnresolvedDiscoveryItem,
};
use metao_contracts::discovery_coordinator::{
    DiscoveryCoordinator, DiscoveryCoordinatorInput, DiscoveryEvaluation, DiscoveryState,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, Provenance, ProvenanceCategory,
    SemanticCategory, SemanticItem,
};
use metao_contracts::tech_stack_intake::{TechStackDecisionMode, TechnicalPreferenceProfile};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

fn provenance(category: ProvenanceCategory, source: &str) -> Provenance {
    Provenance {
        category,
        source_id: source.to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn semantic_item(id: &str, category: SemanticCategory, description: &str) -> SemanticItem {
    SemanticItem {
        item_id: ItemId(id.to_string()),
        category,
        description: description.to_string(),
        provenance: provenance(ProvenanceCategory::UserExplicit, "user"),
    }
}

fn ready_contract() -> ProjectContract {
    let mut users = BTreeSet::new();
    users.insert("buyer".to_string());
    ProjectContract::new(
        ProjectId("project-persisted-discovery".to_string()),
        ContractId("contract-persisted-discovery".to_string()),
        "Build a marketplace".to_string(),
        users,
        vec![
            semantic_item(
                "cap-listings",
                SemanticCategory::RequiredCapability,
                "Users can create and browse listings",
            ),
            semantic_item(
                "accept-listings",
                SemanticCategory::AcceptanceCriterion,
                "Listing creation and browsing work end to end",
            ),
            semantic_item(
                "dod-marketplace",
                SemanticCategory::DefinitionOfDone,
                "Frontend, backend and persistence obligations are integrated",
            ),
        ],
        vec![],
    )
    .expect("valid test contract")
}

fn technical_profile() -> TechnicalPreferenceProfile {
    TechnicalPreferenceProfile {
        mode: TechStackDecisionMode::MetaoRecommended,
        required_languages: BTreeSet::new(),
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
        rationale: Some("metaO may recommend a stack after scope is ready".to_string()),
        provenance: provenance(ProvenanceCategory::MetaoRecommendation, "discovery"),
    }
}

fn material_item() -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: "mobile-scope".to_string(),
        description: "Choose whether native mobile is in MVP scope".to_string(),
        materiality: Materiality::Material,
        reversibility: Reversibility::Reversible,
        materiality_reason: Some(MaterialityReason::ScopeChanging),
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-request"),
        safe_default: None,
    }
}

fn explicit_resolution() -> ExplicitResolution {
    ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "User selected responsive web only for the MVP".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "user-answer"),
    }
}

fn persisted_input() -> DiscoveryCoordinatorInput {
    DiscoveryCoordinatorInput {
        contract: ready_contract(),
        discovery_items: vec![material_item()],
        explicit_resolutions: BTreeMap::from([("mobile-scope".to_string(), explicit_resolution())]),
        reference_intake_pending: false,
        technical_profile: Some(technical_profile()),
    }
}

#[test]
fn discovery_input_and_audit_evaluation_survive_durable_reopen() {
    let input = persisted_input();
    let evaluation = DiscoveryCoordinator::evaluate(&input).expect("initial discovery evaluation");
    assert_eq!(evaluation.state, DiscoveryState::SpecReady);

    let payload = serde_json::json!({
        "input": input,
        "evaluation": evaluation,
    });

    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let path = std::env::temp_dir().join(format!("metao-discovery-{unique}.json"));
    fs::write(
        &path,
        serde_json::to_vec_pretty(&payload).expect("serialize snapshot"),
    )
    .expect("persist discovery snapshot");

    let reopened: Value =
        serde_json::from_slice(&fs::read(&path).expect("read snapshot")).expect("decode snapshot");
    let reopened_input: DiscoveryCoordinatorInput =
        serde_json::from_value(reopened["input"].clone()).expect("decode input");
    let reopened_evaluation: DiscoveryEvaluation =
        serde_json::from_value(reopened["evaluation"].clone()).expect("decode evaluation");

    let reevaluated =
        DiscoveryCoordinator::evaluate(&reopened_input).expect("reevaluate reopened discovery");

    assert_eq!(reopened_evaluation, reevaluated);
    assert_eq!(reevaluated.state, DiscoveryState::SpecReady);
    assert!(reevaluated.applies_to(&reopened_input.contract.binding()));
    assert_eq!(reevaluated.transitions.len(), 1);

    fs::remove_file(path).expect("remove test snapshot");
}

#[test]
fn reopened_contract_revision_cannot_reuse_old_readiness() {
    let input = persisted_input();
    let evaluation = DiscoveryCoordinator::evaluate(&input).expect("initial discovery evaluation");
    let mut newer_binding = input.contract.binding();
    newer_binding.version += 1;
    newer_binding.contract_digest = "different-contract-generation".to_string();

    assert!(!evaluation.applies_to(&newer_binding));
}
