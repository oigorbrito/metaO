use metao_contracts::clarification_policy::{
    ExplicitResolution, Materiality, MaterialityReason, ResolutionKind, Reversibility, SafeDefault,
    UnresolvedDiscoveryItem,
};
use metao_contracts::discovery_coordinator::{
    assumption_source_ids, DiscoveryCoordinator, DiscoveryCoordinatorError,
    DiscoveryCoordinatorInput, DiscoveryState,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, ProjectReference, Provenance,
    ProvenanceCategory, ReferenceId, SemanticCategory, SemanticItem,
};
use metao_contracts::tech_stack_intake::{
    TechStackDecisionMode, TechnicalPreferenceProfile, Technology,
};
use std::collections::{BTreeMap, BTreeSet};

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
fn contract(items: Vec<SemanticItem>, references: Vec<ProjectReference>) -> ProjectContract {
    let mut users = BTreeSet::new();
    users.insert("buyer".to_string());
    ProjectContract::new(
        ProjectId("project-marketplace".to_string()),
        ContractId("contract-marketplace".to_string()),
        "Build a marketplace".to_string(),
        users,
        items,
        references,
    )
    .expect("valid test contract")
}
fn ready_contract(extra: Vec<SemanticItem>) -> ProjectContract {
    let mut items = vec![
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
    ];
    items.extend(extra);
    contract(items, vec![])
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
        rationale: Some("metaO may recommend a stack after product scope is ready".to_string()),
        provenance: provenance(ProvenanceCategory::MetaoRecommendation, "discovery"),
    }
}
fn base_input(contract: ProjectContract) -> DiscoveryCoordinatorInput {
    DiscoveryCoordinatorInput {
        contract,
        discovery_items: vec![],
        explicit_resolutions: BTreeMap::new(),
        reference_intake_pending: false,
        technical_profile: Some(technical_profile()),
    }
}
fn material_scope_item(id: &str) -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: id.to_string(),
        description: "Choose whether native mobile is in MVP scope".to_string(),
        materiality: Materiality::Material,
        reversibility: Reversibility::Reversible,
        materiality_reason: Some(MaterialityReason::ScopeChanging),
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-request"),
        safe_default: None,
    }
}
fn safe_default_item(id: &str) -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: id.to_string(),
        description: "Choose local display naming".to_string(),
        materiality: Materiality::NonMaterial,
        reversibility: Reversibility::Reversible,
        materiality_reason: None,
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-request"),
        safe_default: Some(SafeDefault {
            value: "Use a conventional local label".to_string(),
            rationale: "Presentation-only choice is reversible".to_string(),
            provenance: provenance(ProvenanceCategory::SystemDefault, "safe-default-policy"),
        }),
    }
}
fn explicit_resolution() -> ExplicitResolution {
    ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "User selected responsive web only for the MVP".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "user-answer"),
    }
}

#[test]
fn vague_contract_is_not_spec_ready() {
    let result = DiscoveryCoordinator::evaluate(&base_input(contract(vec![], vec![]))).unwrap();
    assert_eq!(result.state, DiscoveryState::NeedsClarification);
    let ids: BTreeSet<_> = result
        .blockers
        .iter()
        .map(|b| b.blocker_id.as_str())
        .collect();
    assert!(ids.contains("contract:scope"));
    assert!(ids.contains("contract:acceptance"));
    assert!(ids.contains("contract:definition-of-done"));
}
#[test]
fn material_unresolved_item_blocks_spec_ready() {
    let mut input = base_input(ready_contract(vec![]));
    input
        .discovery_items
        .push(material_scope_item("mobile-scope"));
    let result = DiscoveryCoordinator::evaluate(&input).unwrap();
    assert_eq!(result.state, DiscoveryState::NeedsClarification);
    assert!(result
        .blockers
        .iter()
        .any(|b| b.blocker_id == "discovery:mobile-scope"));
}
#[test]
fn explicit_resolution_allows_deterministic_reevaluation() {
    let mut input = base_input(ready_contract(vec![]));
    input
        .discovery_items
        .push(material_scope_item("mobile-scope"));
    input
        .explicit_resolutions
        .insert("mobile-scope".into(), explicit_resolution());
    let first = DiscoveryCoordinator::evaluate(&input).unwrap();
    let second = DiscoveryCoordinator::evaluate(&input).unwrap();
    assert_eq!(first.state, DiscoveryState::SpecReady);
    assert_eq!(first, second);
}
#[test]
fn safe_reversible_default_records_one_assumption_without_human_loop() {
    let mut input = base_input(ready_contract(vec![]));
    input
        .discovery_items
        .push(safe_default_item("display-label"));
    let result = DiscoveryCoordinator::evaluate(&input).unwrap();
    assert_eq!(result.state, DiscoveryState::SpecReady);
    assert_eq!(result.assumptions.len(), 1);
    assert_eq!(
        assumption_source_ids(&result),
        BTreeSet::from(["display-label".to_string()])
    );
}
#[test]
fn pending_reference_intake_cannot_be_skipped_by_other_ready_inputs() {
    let mut input = base_input(ready_contract(vec![]));
    input.reference_intake_pending = true;
    assert_eq!(
        DiscoveryCoordinator::evaluate(&input).unwrap().state,
        DiscoveryState::ReferenceIntake
    );
}
#[test]
fn missing_technical_profile_yields_technical_intake_not_spec_ready() {
    let mut input = base_input(ready_contract(vec![]));
    input.technical_profile = None;
    assert_eq!(
        DiscoveryCoordinator::evaluate(&input).unwrap().state,
        DiscoveryState::TechnicalIntake
    );
}
#[test]
fn technical_profile_alone_cannot_mint_spec_ready() {
    assert_eq!(
        DiscoveryCoordinator::evaluate(&base_input(contract(vec![], vec![])))
            .unwrap()
            .state,
        DiscoveryState::NeedsClarification
    );
}
#[test]
fn project_contract_unresolved_item_remains_a_readiness_blocker() {
    let unresolved = semantic_item(
        "payment-scope",
        SemanticCategory::UnresolvedItem,
        "Decide whether payment processing is in scope",
    );
    let result =
        DiscoveryCoordinator::evaluate(&base_input(ready_contract(vec![unresolved]))).unwrap();
    assert_eq!(result.state, DiscoveryState::NeedsClarification);
    assert!(result
        .blockers
        .iter()
        .any(|b| b.blocker_id == "contract-unresolved:payment-scope"));
}
#[test]
fn reference_presence_does_not_become_required_scope() {
    let reference = ProjectReference {
        reference_id: ReferenceId("olx".into()),
        locator: "https://example.test/reference".into(),
        selected_desired_traits: BTreeMap::from([(
            "simple-listing".into(),
            "simple listing flow".into(),
        )]),
        selected_undesired_traits: BTreeMap::new(),
        provenance: provenance(ProvenanceCategory::UserExplicit, "user-reference"),
    };
    let items = vec![
        semantic_item(
            "accept",
            SemanticCategory::AcceptanceCriterion,
            "Acceptance is explicit",
        ),
        semantic_item(
            "dod",
            SemanticCategory::DefinitionOfDone,
            "Definition of Done is explicit",
        ),
    ];
    let result =
        DiscoveryCoordinator::evaluate(&base_input(contract(items, vec![reference]))).unwrap();
    assert_eq!(result.state, DiscoveryState::NeedsClarification);
    assert!(result
        .blockers
        .iter()
        .any(|b| b.blocker_id == "contract:scope"));
}
#[test]
fn readiness_is_bound_to_exact_contract_identity_version_and_digest() {
    let input = base_input(ready_contract(vec![]));
    let result = DiscoveryCoordinator::evaluate(&input).unwrap();
    assert!(result.applies_to(&input.contract.binding()));
    let mut changed = input.contract.binding();
    changed.version += 1;
    changed.contract_digest = "new-contract-digest".into();
    assert!(!result.applies_to(&changed));
}
#[test]
fn discovery_item_order_does_not_change_result() {
    let first = safe_default_item("display-a");
    let second = safe_default_item("display-b");
    let mut left = base_input(ready_contract(vec![]));
    left.discovery_items = vec![first.clone(), second.clone()];
    let mut right = base_input(ready_contract(vec![]));
    right.discovery_items = vec![second, first];
    assert_eq!(
        DiscoveryCoordinator::evaluate(&left).unwrap(),
        DiscoveryCoordinator::evaluate(&right).unwrap()
    );
}
#[test]
fn invalid_technical_profile_fails_closed() {
    let mut input = base_input(ready_contract(vec![]));
    let mut invalid = technical_profile();
    invalid.rationale = None;
    invalid
        .preferred_languages
        .insert(Technology::new("rust").unwrap());
    input.technical_profile = Some(invalid);
    assert_eq!(
        DiscoveryCoordinator::evaluate(&input),
        Err(DiscoveryCoordinatorError::InvalidTechnicalProfile)
    );
}
#[test]
fn resolution_for_safe_default_is_rejected_instead_of_rewriting_history() {
    let mut input = base_input(ready_contract(vec![]));
    input
        .discovery_items
        .push(safe_default_item("display-label"));
    input
        .explicit_resolutions
        .insert("display-label".into(), explicit_resolution());
    assert_eq!(
        DiscoveryCoordinator::evaluate(&input),
        Err(DiscoveryCoordinatorError::UnexpectedResolution(
            "display-label".into()
        ))
    );
}
#[test]
fn result_schema_contains_no_mission_or_runtime_acceptance_authority() {
    let result = DiscoveryCoordinator::evaluate(&base_input(ready_contract(vec![]))).unwrap();
    let serialized = serde_json::to_string(&result).unwrap();
    assert!(!serialized.contains("AcceptanceDecision"));
    assert!(!serialized.contains("mission_accepted"));
    assert!(!serialized.contains("runtime_id"));
}
