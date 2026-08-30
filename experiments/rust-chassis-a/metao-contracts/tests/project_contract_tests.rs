use metao_contracts::project_contract::*;
use std::collections::{BTreeMap, BTreeSet};

fn mock_provenance() -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: "user-123".to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn valid_item(id: &str, cat: SemanticCategory) -> SemanticItem {
    SemanticItem {
        item_id: ItemId(id.into()),
        category: cat,
        description: "Valid desc".into(),
        provenance: mock_provenance(),
    }
}

fn valid_ref(id: &str) -> ProjectReference {
    ProjectReference {
        reference_id: ReferenceId(id.into()),
        locator: "loc".into(),
        selected_desired_traits: BTreeMap::new(),
        selected_undesired_traits: BTreeMap::new(),
        provenance: mock_provenance(),
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
    assert_eq!(contract.version(), 1);
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
    assert_eq!(
        result.unwrap_err(),
        ContractError::EmptyIdentity("project_id")
    );
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
    assert_eq!(
        result.unwrap_err(),
        ContractError::EmptyIdentity("contract_id")
    );
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
    assert_eq!(result.unwrap_err(), ContractError::EmptyGoal);
}

#[test]
fn test_t06_duplicate_item_id_rejected() {
    let item1 = valid_item("i1", SemanticCategory::Assumption);
    let item2 = valid_item("i1", SemanticCategory::UserRequirement);
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item1, item2],
        vec![],
    );
    assert_eq!(
        result.unwrap_err(),
        ContractError::DuplicateItemId("i1".into())
    );
}

#[test]
fn test_t07_duplicate_reference_id_rejected() {
    let ref1 = valid_ref("r1");
    let ref2 = valid_ref("r1");
    let result = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![ref1, ref2],
    );
    assert_eq!(
        result.unwrap_err(),
        ContractError::DuplicateReferenceId("r1".into())
    );
}

#[test]
fn test_t08_to_t12d_categories_remain_distinct() {
    let items = vec![
        valid_item("1", SemanticCategory::Assumption),
        valid_item("2", SemanticCategory::UserRequirement),
        valid_item("3", SemanticCategory::Preference),
        valid_item("4", SemanticCategory::TechnicalConstraint),
        valid_item("5", SemanticCategory::RequiredCapability),
        valid_item("6", SemanticCategory::RequiredSurface),
        valid_item("7", SemanticCategory::DefinitionOfDone),
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

    assert!(contract.assumptions().contains_key(&ItemId("1".into())));
    assert!(!contract
        .user_requirements()
        .contains_key(&ItemId("1".into()))); // Negative sensor
    assert!(contract
        .user_requirements()
        .contains_key(&ItemId("2".into())));
    assert!(contract.preferences().contains_key(&ItemId("3".into())));
    assert!(contract
        .technical_constraints()
        .contains_key(&ItemId("4".into())));
    assert!(contract
        .required_capabilities()
        .contains_key(&ItemId("5".into())));
    assert!(!contract
        .user_requirements()
        .contains_key(&ItemId("5".into()))); // Negative sensor
    assert!(contract
        .required_surfaces()
        .contains_key(&ItemId("6".into())));
    assert!(contract
        .definition_of_done()
        .contains_key(&ItemId("7".into())));
}

#[test]
fn test_t13_t14_same_content_same_digest() {
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
    assert_eq!(contract1.contract_digest(), contract2.contract_digest());
}

#[test]
fn test_t15_unordered_equivalent_input_same_digest() {
    let item1 = valid_item("i1", SemanticCategory::UserRequirement);
    let item2 = valid_item("i2", SemanticCategory::Assumption);
    let contract1 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item1.clone(), item2.clone()],
        vec![],
    )
    .unwrap();
    let contract2 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item2, item1],
        vec![],
    )
    .unwrap();
    assert_eq!(contract1.contract_digest(), contract2.contract_digest());
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
    assert_ne!(contract1.contract_digest(), contract2.contract_digest());
}

#[test]
fn test_t17_provenance_change_changes_digest() {
    let item1 = valid_item("i1", SemanticCategory::Assumption);
    let mut item2 = item1.clone();
    item2.provenance.source_id = "user-456".into();

    let contract1 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item1],
        vec![],
    )
    .unwrap();
    let contract2 = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![item2],
        vec![],
    )
    .unwrap();
    assert_ne!(contract1.contract_digest(), contract2.contract_digest());
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

    assert_eq!(previous.version(), 1);
    assert_eq!(revision.version(), 2);

    let lineage = revision.lineage().unwrap();
    assert_eq!(
        lineage.predecessor.contract_digest,
        previous.contract_digest()
    );
    assert_eq!(lineage.predecessor.version, 1);

    // Test t17B and t17C implicitly: revision has diff version and lineage, so digest differs
    assert_ne!(previous.contract_digest(), revision.contract_digest());
}

#[test]
fn test_t24_binding_contains_exact_fields() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let binding = contract.binding();
    assert_eq!(binding.project_id.0, "p1");
    assert_eq!(binding.contract_id.0, "c1");
    assert_eq!(binding.version, 1);
    assert_eq!(binding.contract_digest, contract.contract_digest());
}

#[test]
fn test_t25_acceptance_criterion_and_test_remain_distinct() {
    let items = vec![
        valid_item("1", SemanticCategory::AcceptanceCriterion),
        valid_item("2", SemanticCategory::AcceptanceTest),
    ];
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        items,
        vec![],
    )
    .unwrap();
    assert!(contract
        .acceptance_criteria()
        .contains_key(&ItemId("1".into())));
    assert!(!contract
        .acceptance_criteria()
        .contains_key(&ItemId("2".into())));
    assert!(contract
        .acceptance_tests()
        .contains_key(&ItemId("2".into())));
}

#[test]
fn test_t30_canonical_round_trip() {
    let items = vec![valid_item("1", SemanticCategory::UserRequirement)];
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        items,
        vec![],
    )
    .unwrap();

    let dto: ProjectContractDto = contract.clone().into();
    let json = serde_json::to_string(&dto).unwrap();
    let parsed_dto: ProjectContractDto = serde_json::from_str(&json).unwrap();
    let contract2: ProjectContract = parsed_dto.try_into().unwrap();

    assert_eq!(contract.contract_digest(), contract2.contract_digest());
    assert!(contract2
        .user_requirements()
        .contains_key(&ItemId("1".into())));
}

#[test]
fn test_t31_empty_provenance_source_rejected() {
    let mut item = valid_item("1", SemanticCategory::UserRequirement);
    item.provenance.source_id = "   ".into();
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t32_empty_item_id_rejected() {
    let item = valid_item("   ", SemanticCategory::UserRequirement);
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert_eq!(res.unwrap_err(), ContractError::EmptyIdentity("item_id"));
}

#[test]
fn test_t33_empty_reference_id_rejected() {
    let ref1 = valid_ref("   ");
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::EmptyIdentity("reference_id")
    );
}

#[test]
fn test_t34_empty_description_rejected() {
    let mut item = valid_item("1", SemanticCategory::UserRequirement);
    item.description = "   ".into();
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert_eq!(res.unwrap_err(), ContractError::EmptyDescription);
}

#[test]
fn test_t35_empty_locator_rejected() {
    let mut ref1 = valid_ref("1");
    ref1.locator = "   ".into();
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(res.unwrap_err(), ContractError::EmptyIdentity("locator"));
}

#[test]
fn test_t36_stale_digest_rejected() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut dto: ProjectContractDto = contract.into();
    dto.contract_digest = "stale_hash".into();
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidBindingDigest);
}

#[test]
fn test_t38_initial_dto_version_1_no_lineage_pass() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let dto: ProjectContractDto = contract.clone().into();
    let res: Result<ProjectContract, _> = dto.try_into();
    assert!(res.is_ok());
}

#[test]
fn test_t39_initial_dto_version_2_no_lineage_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut dto: ProjectContractDto = contract.into();
    dto.version = 2;
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidVersionLineage);
}

#[test]
fn test_t40_revised_dto_version_1_with_lineage_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 1;
    dto.lineage = Some(ContractLineage {
        predecessor: contract.binding(),
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidVersionLineage);
}

#[test]
fn test_t41_revised_dto_version_0_with_lineage_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 0;
    dto.lineage = Some(ContractLineage {
        predecessor: contract.binding(),
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidVersionLineage);
}

#[test]
fn test_t42_predecessor_version_not_n_minus_1_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut predecessor = contract.binding();
    predecessor.version = 0;
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidPredecessorBinding);
}

#[test]
fn test_t43_predecessor_project_id_mismatch_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut predecessor = contract.binding();
    predecessor.project_id = ProjectId("p2".into());
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidPredecessorBinding);
}

#[test]
fn test_t44_predecessor_contract_id_mismatch_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut predecessor = contract.binding();
    predecessor.contract_id = ContractId("c2".into());
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidPredecessorBinding);
}

#[test]
fn test_t45_empty_predecessor_digest_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut predecessor = contract.binding();
    predecessor.contract_digest = "   ".into();
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "r".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidPredecessorBinding);
}

#[test]
fn test_t46_blank_revision_rationale_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let predecessor = contract.binding();
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "   ".into(),
        revision_provenance: mock_provenance(),
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::EmptyRevisionRationale);
}

#[test]
fn test_t47_invalid_revision_provenance_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let predecessor = contract.binding();
    let mut dto: ProjectContractDto = contract.clone().into();
    dto.version = 2;
    let mut prov = mock_provenance();
    prov.source_id = "   ".into();
    dto.lineage = Some(ContractLineage {
        predecessor,
        revision_rationale: "r".into(),
        revision_provenance: prov,
    });
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t48_valid_revision_dto_round_trip_pass() {
    let previous = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let revision = ProjectContract::revise_contract(
        &previous,
        "g2".into(),
        BTreeSet::new(),
        vec![],
        vec![],
        "r".into(),
        mock_provenance(),
    )
    .unwrap();

    let dto: ProjectContractDto = revision.clone().into();
    let json = serde_json::to_string(&dto).unwrap();
    let parsed_dto: ProjectContractDto = serde_json::from_str(&json).unwrap();
    let contract: ProjectContract = parsed_dto.try_into().unwrap();

    assert_eq!(revision.contract_digest(), contract.contract_digest());
}

#[test]
fn test_t49_public_revise_contract_output_serialize_deserialize_identical() {
    let previous = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "g".into(),
        BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let revision = ProjectContract::revise_contract(
        &previous,
        "g2".into(),
        BTreeSet::new(),
        vec![],
        vec![],
        "r".into(),
        mock_provenance(),
    )
    .unwrap();

    let dto: ProjectContractDto = revision.clone().into();
    let res: Result<ProjectContract, _> = dto.try_into();
    assert!(res.is_ok());

    let deserialized = res.unwrap();
    assert_eq!(
        deserialized.binding().contract_digest,
        revision.binding().contract_digest
    );
}

#[test]
fn test_t50_direct_project_reference_blank_desired_trait_id_fail() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_desired_traits
        .insert("   ".into(), "desc".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::InvalidReferenceTrait("Blank desired trait id")
    );
}

#[test]
fn test_t51_direct_project_reference_blank_desired_description_fail() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_desired_traits
        .insert("t1".into(), "   ".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::InvalidReferenceTrait("Blank desired trait description")
    );
}

#[test]
fn test_t52_direct_project_reference_blank_undesired_trait_id_fail() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_undesired_traits
        .insert("   ".into(), "desc".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::InvalidReferenceTrait("Blank undesired trait id")
    );
}

#[test]
fn test_t53_direct_project_reference_blank_undesired_description_fail() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_undesired_traits
        .insert("t1".into(), "   ".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::InvalidReferenceTrait("Blank undesired trait description")
    );
}

#[test]
fn test_t54_direct_desired_undesired_same_trait_fail() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_desired_traits
        .insert("t1".into(), "desc".into());
    ref1.selected_undesired_traits
        .insert("t1".into(), "desc".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::ConflictingReferenceTrait("t1".into())
    );
}

#[test]
fn test_t55_direct_valid_project_reference_pass() {
    let mut ref1 = valid_ref("r1");
    ref1.selected_desired_traits
        .insert("t1".into(), "desc".into());
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert!(res.is_ok());
}

#[test]
fn test_t56_semantic_item_nested_authorization_blank_source_fail() {
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let mut bad_auth = mock_provenance();
    bad_auth.source_id = "   ".into();
    item.provenance.authorization = Some(Box::new(bad_auth));
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t57_project_reference_nested_authorization_blank_source_fail() {
    let mut ref1 = valid_ref("r1");
    let mut bad_auth = mock_provenance();
    bad_auth.source_id = "   ".into();
    ref1.provenance.authorization = Some(Box::new(bad_auth));
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![ref1],
    );
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t58_revision_provenance_nested_authorization_blank_source_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut bad_auth = mock_provenance();
    bad_auth.source_id = "   ".into();
    let mut rev_prov = mock_provenance();
    rev_prov.authorization = Some(Box::new(bad_auth));
    let res = ProjectContract::revise_contract(
        &contract,
        "g2".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![],
        "r".into(),
        rev_prov,
    );
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t59_dto_nested_authorization_blank_source_fail() {
    let contract = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![],
        vec![],
    )
    .unwrap();
    let mut dto: ProjectContractDto = contract.into();
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let mut bad_auth = mock_provenance();
    bad_auth.source_id = "   ".into();
    item.provenance.authorization = Some(Box::new(bad_auth));
    dto.user_requirements.insert(item.item_id.clone(), item);
    let res: Result<ProjectContract, _> = dto.try_into();
    assert_eq!(res.unwrap_err(), ContractError::InvalidProvenance);
}

#[test]
fn test_t60_nested_valid_authorization_pass() {
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let auth = mock_provenance();
    item.provenance.authorization = Some(Box::new(auth));
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert!(res.is_ok());
}

#[test]
fn test_t61_nested_nested_valid_authorization_pass() {
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let mut auth = mock_provenance();
    let auth2 = mock_provenance();
    auth.authorization = Some(Box::new(auth2));
    item.provenance.authorization = Some(Box::new(auth));
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert!(res.is_ok());
}

#[test]
fn test_t62_authorization_depth_boundary_valid_pass() {
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let mut current = item.provenance.clone();
    for _ in 0..8 {
        let mut next = mock_provenance();
        next.authorization = Some(Box::new(current));
        current = next;
    }
    item.provenance = current;
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert!(res.is_ok());
}

#[test]
fn test_t63_authorization_depth_limit_fail() {
    let mut item = valid_item("i1", SemanticCategory::UserRequirement);
    let mut current = item.provenance.clone();
    for _ in 0..9 {
        let mut next = mock_provenance();
        next.authorization = Some(Box::new(current));
        current = next;
    }
    item.provenance = current;
    let res = ProjectContract::new(
        ProjectId("p1".into()),
        ContractId("c1".into()),
        "goal".into(),
        std::collections::BTreeSet::new(),
        vec![item],
        vec![],
    );
    assert_eq!(
        res.unwrap_err(),
        ContractError::ProvenanceAuthorizationDepthExceeded
    );
}
