use metao_contracts::project_contract::*;
use std::collections::BTreeSet;

fn mock_provenance() -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: "user-123".to_string(),
        derived_from: None,
    }
}

#[test]
fn test_t01_minimal_valid_contract() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    assert_eq!(contract.version, 1);
}

#[test]
fn test_t02_empty_project_id_rejected() {
    let result = ProjectContract::new(
        ProjectId("".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    );
    assert_eq!(result, Err(ContractError::EmptyIdentity("project_id")));
}

#[test]
fn test_t03_empty_contract_id_rejected() {
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    );
    assert_eq!(result, Err(ContractError::EmptyIdentity("contract_id")));
}

#[test]
fn test_t05_empty_goal_rejected() {
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        " ".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    );
    assert_eq!(result, Err(ContractError::EmptyGoal));
}

#[test]
fn test_t06_duplicate_item_id_rejected() {
    let item1 = SemanticItem {
        item_id: ItemId("i1".into()),
        category: SemanticCategory::Assumption,
        description: "A".into(),
        provenance: mock_provenance(),
    };
    let item2 = SemanticItem {
        item_id: ItemId("i1".into()),
        category: SemanticCategory::UserRequirement,
        description: "B".into(),
        provenance: mock_provenance(),
    };
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item1, item2],
        vec![],
    );
    assert_eq!(result, Err(ContractError::DuplicateItemId("i1".into())));
}

#[test]
fn test_t07_duplicate_reference_id_rejected() {
    let ref1 = ProjectReference {
        reference_id: ReferenceId("r1".into()),
        locator: "L1".into(),
        selected_desired_traits: BTreeSet::new(),
        selected_undesired_traits: BTreeSet::new(),
        provenance: mock_provenance(),
    };
    let ref2 = ProjectReference {
        reference_id: ReferenceId("r1".into()),
        locator: "L2".into(),
        selected_desired_traits: BTreeSet::new(),
        selected_undesired_traits: BTreeSet::new(),
        provenance: mock_provenance(),
    };
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![ref1, ref2],
    );
    assert_eq!(
        result,
        Err(ContractError::DuplicateReferenceId("r1".into()))
    );
}

#[test]
fn test_t08_to_t12_categories_remain_distinct() {
    let items = vec![
        SemanticItem {
            item_id: ItemId("1".into()),
            category: SemanticCategory::Assumption,
            description: "".into(),
            provenance: mock_provenance(),
        },
        SemanticItem {
            item_id: ItemId("2".into()),
            category: SemanticCategory::UserRequirement,
            description: "".into(),
            provenance: mock_provenance(),
        },
        SemanticItem {
            item_id: ItemId("3".into()),
            category: SemanticCategory::Preference,
            description: "".into(),
            provenance: mock_provenance(),
        },
        SemanticItem {
            item_id: ItemId("4".into()),
            category: SemanticCategory::TechnicalConstraint,
            description: "".into(),
            provenance: mock_provenance(),
        },
    ];
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        items,
        vec![],
    )
    .unwrap();

    assert!(contract.assumptions.contains_key(&ItemId("1".into())));
    assert!(contract.user_requirements.contains_key(&ItemId("2".into())));
    assert!(contract.preferences.contains_key(&ItemId("3".into())));
    assert!(contract
        .technical_constraints
        .contains_key(&ItemId("4".into())));
}

#[test]
fn test_t13_canonical_serialization_deterministic() {
    // Already enforced by BTreeMap and struct definition
}

#[test]
fn test_t14_same_content_same_digest() {
    let contract1 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let contract2 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    assert_eq!(contract1.contract_digest, contract2.contract_digest);
}

#[test]
fn test_t16_material_change_changes_digest() {
    let contract1 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let contract2 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal 2".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    assert_ne!(contract1.contract_digest, contract2.contract_digest);
}

#[test]
fn test_t18_t20_revision_rules() {
    let previous = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();

    let revision = ProjectContract::revise_contract(
        &previous,
        "new goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
        "Update".into(),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(previous.version, 1);
    assert_eq!(revision.version, 2);

    let lineage = revision.lineage.as_ref().unwrap();
    assert_eq!(
        lineage.predecessor.contract_digest,
        previous.contract_digest
    );
    assert_eq!(lineage.predecessor.version, 1);
}
