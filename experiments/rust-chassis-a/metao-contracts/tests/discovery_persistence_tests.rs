use metao_contracts::clarification_policy::{
    ExplicitResolution, Materiality, MaterialityReason, ResolutionKind, Reversibility,
    UnresolvedDiscoveryItem,
};
use metao_contracts::discovery_coordinator::{
    DiscoveryCoordinator, DiscoveryCoordinatorInput, DiscoveryState,
};
use metao_contracts::discovery_persistence::{
    DiscoveryPersistenceError, DiscoverySnapshot, DiscoveryStateStore, FileDiscoveryStateStore,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, ProjectReference, Provenance,
    ProvenanceCategory, ReferenceId, SemanticCategory, SemanticItem,
};
use metao_contracts::tech_stack_intake::{TechStackDecisionMode, TechnicalPreferenceProfile};
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
    let reference = ProjectReference {
        reference_id: ReferenceId("marketplace-reference".to_string()),
        locator: "https://example.test/marketplace-reference".to_string(),
        selected_desired_traits: BTreeMap::from([(
            "durable-listings".to_string(),
            "Listings survive process restart".to_string(),
        )]),
        selected_undesired_traits: BTreeMap::new(),
        provenance: provenance(ProvenanceCategory::UserExplicit, "reference-intake"),
    };
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
        vec![reference],
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

fn safe_assumption_item() -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: "visual-label".to_string(),
        description: "Choose whether the listing card label says newest or recent".to_string(),
        materiality: Materiality::NonMaterial,
        reversibility: Reversibility::Reversible,
        materiality_reason: None,
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-request"),
        safe_default: Some(metao_contracts::clarification_policy::SafeDefault {
            value: "Use Recent listings".to_string(),
            rationale: "Copy can change later without changing product scope".to_string(),
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

fn persisted_input() -> DiscoveryCoordinatorInput {
    DiscoveryCoordinatorInput {
        contract: ready_contract(),
        discovery_items: vec![material_item(), safe_assumption_item()],
        explicit_resolutions: BTreeMap::from([("mobile-scope".to_string(), explicit_resolution())]),
        reference_intake_pending: false,
        technical_profile: Some(technical_profile()),
    }
}

fn unresolved_input() -> DiscoveryCoordinatorInput {
    DiscoveryCoordinatorInput {
        contract: ready_contract(),
        discovery_items: vec![material_item(), safe_assumption_item()],
        explicit_resolutions: BTreeMap::new(),
        reference_intake_pending: false,
        technical_profile: Some(technical_profile()),
    }
}

fn temp_store() -> FileDiscoveryStateStore {
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    FileDiscoveryStateStore::new(
        std::env::temp_dir().join(format!("metao-discovery-store-{unique}")),
    )
}

#[test]
fn discovery_save_reopen_and_resume_survive_durable_store_boundary() {
    let input = persisted_input();
    let snapshot = DiscoverySnapshot::capture(input.clone()).expect("capture discovery snapshot");
    let store = temp_store();
    let path = store.snapshot_path(&snapshot.binding);
    store.save(&snapshot).expect("persist discovery snapshot");
    assert!(path.exists(), "snapshot must cross the filesystem boundary");

    drop(snapshot);

    let reopened_store = FileDiscoveryStateStore::new(store.root().to_path_buf());
    let reopened = reopened_store
        .load(&input.contract.binding())
        .expect("load persisted discovery snapshot")
        .expect("snapshot exists");
    let resumed = reopened.resume().expect("resume from reopened snapshot");
    let expected =
        DiscoveryCoordinator::evaluate(&input).expect("canonical deterministic reevaluation");

    assert_eq!(reopened.evaluation, expected);
    assert_eq!(resumed, expected);
    assert_eq!(resumed.state, DiscoveryState::SpecReady);
    assert!(resumed.applies_to(&input.contract.binding()));
    assert_eq!(resumed.assumptions.len(), 1);
    assert_eq!(resumed.transitions.len(), 1);
    assert_eq!(
        reopened
            .input
            .explicit_resolutions
            .get("mobile-scope")
            .expect("human answer survives")
            .rationale,
        "User selected responsive web only for the MVP"
    );

    let repeated = reopened_store
        .load(&input.contract.binding())
        .expect("load persisted discovery snapshot again")
        .expect("snapshot exists")
        .resume()
        .expect("repeat resume");
    assert_eq!(repeated, resumed);

    fs::remove_dir_all(store.root()).expect("remove test store");
}

#[test]
fn reopened_contract_revision_cannot_reuse_old_readiness() {
    let input = persisted_input();
    let snapshot = DiscoverySnapshot::capture(input.clone()).expect("capture discovery snapshot");
    let store = temp_store();
    store.save(&snapshot).expect("persist discovery snapshot");

    let mut newer_binding = input.contract.binding();
    newer_binding.version += 1;
    newer_binding.contract_digest = "different-contract-generation".to_string();

    assert_eq!(
        store
            .load(&newer_binding)
            .expect("mismatched binding is absent"),
        None
    );
    assert!(!snapshot
        .resume()
        .expect("old snapshot still resumes for old binding")
        .applies_to(&newer_binding));

    fs::remove_dir_all(store.root()).expect("remove test store");
}

#[test]
fn corrupt_persisted_payload_fails_closed() {
    let input = persisted_input();
    let snapshot = DiscoverySnapshot::capture(input.clone()).expect("capture discovery snapshot");
    let store = temp_store();
    store.save(&snapshot).expect("persist discovery snapshot");
    fs::write(
        store.snapshot_path(&input.contract.binding()),
        b"{not valid json",
    )
    .expect("corrupt snapshot");

    let result = store.load(&input.contract.binding());

    assert!(matches!(result, Err(DiscoveryPersistenceError::Decode(_))));
    fs::remove_dir_all(store.root()).expect("remove test store");
}

#[test]
fn missing_persisted_state_is_explicit_and_not_spec_ready() {
    let input = persisted_input();
    let store = temp_store();

    assert_eq!(
        store
            .load(&input.contract.binding())
            .expect("missing is explicit"),
        None
    );
}

#[test]
fn unresolved_material_decision_still_blocks_after_reopen() {
    let input = unresolved_input();
    let snapshot = DiscoverySnapshot::capture(input.clone()).expect("capture blocked snapshot");
    assert_eq!(
        snapshot.evaluation.state,
        DiscoveryState::NeedsClarification
    );

    let store = temp_store();
    store
        .save(&snapshot)
        .expect("persist blocked discovery snapshot");
    let reopened = FileDiscoveryStateStore::new(store.root().to_path_buf())
        .load(&input.contract.binding())
        .expect("load persisted blocked snapshot")
        .expect("snapshot exists");
    let resumed = reopened.resume().expect("resume blocked snapshot");

    assert_eq!(resumed.state, DiscoveryState::NeedsClarification);
    assert!(resumed
        .blockers
        .iter()
        .any(|blocker| blocker.blocker_id == "discovery:mobile-scope"));

    fs::remove_dir_all(store.root()).expect("remove test store");
}

#[test]
fn persistence_contract_contains_no_runtime_or_framework_authority() {
    let input = persisted_input();
    let snapshot = DiscoverySnapshot::capture(input).expect("capture discovery snapshot");
    let json = serde_json::to_string(&snapshot).expect("serialize snapshot");

    assert!(!json.contains("runtime_id"));
    assert!(!json.contains("orchestrator"));
    assert!(!json.contains("sdk"));
}
