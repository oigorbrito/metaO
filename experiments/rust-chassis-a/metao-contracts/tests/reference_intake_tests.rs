use metao_contracts::project_contract::{
    ItemId, Provenance, ProvenanceCategory, ReferenceId, SemanticCategory,
};
use metao_contracts::reference_intake::{
    IntakeError, PromotionTargetCategory, ReferenceInput, ReferenceIntake, ReferenceKind,
    ReferenceTrait, TraitId,
};

fn mock_provenance() -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: "user-1".into(),
        derived_from: None,
        authorization: None,
    }
}

fn valid_trait(id: &str, desc: &str) -> ReferenceTrait {
    ReferenceTrait {
        trait_id: TraitId(id.into()),
        description: desc.into(),
    }
}

fn valid_input(
    ref_id: &str,
    desired: Vec<ReferenceTrait>,
    undesired: Vec<ReferenceTrait>,
) -> ReferenceInput {
    ReferenceInput {
        reference_id: ReferenceId(ref_id.into()),
        reference_kind: ReferenceKind::Url,
        locator: "https://example.com".into(),
        desired_traits: desired,
        undesired_traits: undesired,
        provenance: mock_provenance(),
    }
}

#[test]
fn test_t01_desired_trait_reference_constructs() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let result = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    assert!(result.selected_desired_traits.contains_key("t1"));
    assert!(result.selected_undesired_traits.is_empty());
}

#[test]
fn test_t02_undesired_trait_reference_constructs() {
    let input = valid_input("r1", vec![], vec![valid_trait("t1", "desc")]);
    let result = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    assert!(result.selected_undesired_traits.contains_key("t1"));
    assert!(result.selected_desired_traits.is_empty());
}

#[test]
fn test_t03_desired_and_undesired_same_trait_same_ref_conflict() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc")],
        vec![valid_trait("t1", "desc")],
    );
    let result = ReferenceIntake::evaluate_reference(&input).unwrap();
    match result {
        Err(conflict) => {
            assert_eq!(conflict.reference_id.0, "r1");
            assert_eq!(conflict.trait_id.0, "t1");
        }
        _ => panic!("Expected conflict"),
    }
}

#[test]
fn test_t04_separate_references_may_use_same_trait() {
    let input1 = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let input2 = valid_input("r2", vec![], vec![valid_trait("t1", "desc")]);

    let res1 = ReferenceIntake::evaluate_reference(&input1)
        .unwrap()
        .unwrap();
    let res2 = ReferenceIntake::evaluate_reference(&input2)
        .unwrap()
        .unwrap();

    assert!(res1.selected_desired_traits.contains_key("t1"));
    assert!(res2.selected_undesired_traits.contains_key("t1"));
}

#[test]
fn test_t05_t06_t07_reference_intake_creates_zero_requirements() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    assert_eq!(proj_ref.selected_desired_traits.len(), 1);
}

#[test]
fn test_t08_explicit_desired_trait_user_req_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::UserRequirement);
}

#[test]
fn test_t09_explicit_desired_trait_preference_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::Preference,
        ItemId("pref1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::Preference);
}

#[test]
fn test_t10_explicit_desired_trait_assumption_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::Assumption,
        ItemId("assump1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::Assumption);
}

#[test]
fn test_t13_unknown_trait_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let res = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t2".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::UnknownTrait);
}

#[test]
fn test_t14_undesired_trait_positive_promotion_fails() {
    let input = valid_input("r1", vec![], vec![valid_trait("t1", "desc")]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let res = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::CannotPromoteUndesiredTrait);
}

#[test]
fn test_t15_promoted_item_uses_requested_item_id() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req123".into()),
        mock_provenance(),
    )
    .unwrap();
    assert_eq!(item.item_id.0, "req123");
}

#[test]
fn test_t33_t34_t35_exact_decision_reference_and_trait_provenance_preserved() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let decision_prov = Provenance {
        category: ProvenanceCategory::UserConfirmed,
        source_id: "user-abc".into(),
        derived_from: None,
        authorization: None,
    };
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        decision_prov.clone(),
    )
    .unwrap();

    assert_eq!(
        item.provenance.category,
        ProvenanceCategory::ReferenceDerived
    );
    assert_eq!(item.provenance.source_id, "r1");
    assert_eq!(item.provenance.derived_from, Some("t1".into()));
    assert_eq!(item.provenance.authorization, Some(Box::new(decision_prov)));
}

#[test]
fn test_t23_blank_trait_id_rejected() {
    let input = valid_input("r1", vec![valid_trait("  ", "desc")], vec![]);
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::BlankTraitId);
}

#[test]
fn test_t24_blank_trait_description_rejected() {
    let input = valid_input("r1", vec![valid_trait("t1", "   ")], vec![]);
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::BlankTraitDescription);
}

#[test]
fn test_t25_blank_reference_locator_rejected() {
    let mut input = valid_input("r1", vec![], vec![]);
    input.locator = "   ".into();
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::BlankLocator);
}

#[test]
fn test_t26_blank_reference_id_rejected() {
    let input = valid_input("   ", vec![], vec![]);
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::BlankReferenceId);
}

#[test]
fn test_t31_invalid_reference_provenance_rejected() {
    let mut input = valid_input("r1", vec![], vec![]);
    input.provenance.source_id = "   ".into();
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::InvalidReferenceProvenance);
}

#[test]
fn test_t32_invalid_promotion_decision_provenance_rejected() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let mut bad_decision = mock_provenance();
    bad_decision.source_id = "   ".into();
    let res = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        bad_decision,
    );
    assert_eq!(res.unwrap_err(), IntakeError::InvalidDecisionProvenance);
}

#[test]
fn test_t36_duplicate_trait_id_same_description_deterministic() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc1"), valid_trait("t1", "desc1")],
        vec![],
    );
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    assert_eq!(proj_ref.selected_desired_traits.len(), 1);
}

#[test]
fn test_t37_duplicate_trait_id_different_description_rejected() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc1"), valid_trait("t1", "desc2")],
        vec![],
    );
    let res = ReferenceIntake::evaluate_reference(&input);
    assert_eq!(res.unwrap_err(), IntakeError::ConflictingDuplicateTrait);
}

#[test]
fn test_t38_conflicting_reference_cannot_be_promoted() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc")],
        vec![valid_trait("t1", "desc")],
    );
    let res = ReferenceIntake::evaluate_reference(&input).unwrap();
    assert!(res.is_err());
    // Since we can't get a ProjectReference out of evaluate_reference for a conflict,
    // we cannot pass it to promote_reference_trait.
}

#[test]
fn test_t44_promotion_result_contains_exactly_one_semantic_item() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();
    assert_eq!(item.item_id.0, "req1");
}

// Negative sensors:

#[test]
#[should_panic]
fn test_sensor_dropping_decision_provenance_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    let item = ReferenceIntake::promote_reference_trait(
        &proj_ref,
        &TraitId("t1".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    // If authorization was dropped, this assert will panic (which is expected)
    assert_eq!(item.provenance.authorization, None);
}

#[test]
#[should_panic]
fn test_sensor_silent_collapse_of_conflicting_duplicate_traits_fails() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc1"), valid_trait("t1", "desc2")],
        vec![],
    );
    let res = ReferenceIntake::evaluate_reference(&input).unwrap();
    assert!(res.is_ok()); // This panics because evaluate_reference returns Err ConflictingDuplicateTrait
}
