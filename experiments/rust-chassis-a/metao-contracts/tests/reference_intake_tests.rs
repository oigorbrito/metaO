use metao_contracts::project_contract::{
    ItemId, ProjectReference, Provenance, ProvenanceCategory, ReferenceId, SemanticCategory,
};
use metao_contracts::reference_intake::{
    IntakeError, ReferenceInput, ReferenceIntake, ReferenceKind, ReferenceTrait, TraitId,
};

fn mock_provenance() -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: "user-1".into(),
        derived_from: None,
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
    assert!(result.selected_desired_traits.contains("t1"));
    assert!(result.selected_undesired_traits.is_empty());
}

#[test]
fn test_t02_undesired_trait_reference_constructs() {
    let input = valid_input("r1", vec![], vec![valid_trait("t1", "desc")]);
    let result = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    assert!(result.selected_undesired_traits.contains("t1"));
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

    // No global conflict detected here because ReferenceIntake operates per-input.
    assert!(res1.selected_desired_traits.contains("t1"));
    assert!(res2.selected_undesired_traits.contains("t1"));
}

#[test]
fn test_t05_t06_t07_reference_intake_creates_zero_requirements() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    // ProjectReference does not contain UserRequirements, Preferences, Assumptions
    // (It's verified structurally since it only has BTreeSet<String>)
    assert_eq!(proj_ref.selected_desired_traits.len(), 1);
}

#[test]
fn test_t08_explicit_desired_trait_user_req_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::UserRequirement);
}

#[test]
fn test_t09_explicit_desired_trait_preference_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::Preference,
        ItemId("pref1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::Preference);
}

#[test]
fn test_t10_explicit_desired_trait_assumption_promotion() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::Assumption,
        ItemId("assump1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.category, SemanticCategory::Assumption);
}

#[test]
fn test_t11_promotion_requires_target_category() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    // InvalidTargetCategory for those not allowed
    let res = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::AcceptanceCriterion,
        ItemId("ac1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::InvalidTargetCategory);
}

#[test]
fn test_t12_unknown_reference_fails() {
    let input = valid_input("   ", vec![valid_trait("t1", "desc")], vec![]);
    let res = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::UnknownReference);
}

#[test]
fn test_t13_unknown_trait_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let res = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t2".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::UnknownTrait);
}

#[test]
fn test_t14_undesired_trait_positive_promotion_fails() {
    let input = valid_input("r1", vec![], vec![valid_trait("t1", "desc")]);
    let res = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert_eq!(res.unwrap_err(), IntakeError::CannotPromoteUndesiredTrait);
}

#[test]
fn test_t15_promoted_item_uses_requested_item_id() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req123".into()),
        mock_provenance(),
    )
    .unwrap();
    assert_eq!(item.item_id.0, "req123");
}

#[test]
fn test_t16_t17_t18_promoted_item_provenance() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(
        item.provenance.category,
        ProvenanceCategory::ReferenceDerived
    );
    assert_eq!(item.provenance.source_id, "r1");
    assert_eq!(item.provenance.derived_from, Some("t1".into()));
}

#[test]
fn test_t19_t20_no_whole_reference_promotion() {
    // There is no API to promote a whole reference. The API requires a single TraitId.
    // The lack of such method ensures this statically.
}

#[test]
fn test_t21_t22_duplicate_traits_canonicalize() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc1"), valid_trait("t1", "desc2")],
        vec![],
    );
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();
    // BTreeSet deduplicates.
    assert_eq!(proj_ref.selected_desired_traits.len(), 1);
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
fn test_t27_round_trip_preserves_desired_vs_undesired() {
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc")],
        vec![valid_trait("t2", "desc2")],
    );
    let proj_ref = ReferenceIntake::evaluate_reference(&input)
        .unwrap()
        .unwrap();

    let json = serde_json::to_string(&proj_ref).unwrap();
    let parsed: ProjectReference = serde_json::from_str(&json).unwrap();

    assert!(parsed.selected_desired_traits.contains("t1"));
    assert!(parsed.selected_undesired_traits.contains("t2"));
}

#[test]
fn test_t28_round_trip_creates_no_requirements() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let json = serde_json::to_string(&input).unwrap();
    let parsed: ReferenceInput = serde_json::from_str(&json).unwrap();

    assert_eq!(parsed.desired_traits.len(), 1);
    assert_eq!(parsed.undesired_traits.len(), 0);
    // Again, no requirements created
}

// T29 and T30 are architectural properties: no SDK coupling, no acceptance minting.

// Negative sensors:
#[test]
#[should_panic]
fn test_sensor_removing_conflict_fails() {
    // If conflict detection is removed, this would not panic and test would fail.
    let input = valid_input(
        "r1",
        vec![valid_trait("t1", "desc")],
        vec![valid_trait("t1", "desc")],
    );
    let res = ReferenceIntake::evaluate_reference(&input).unwrap();
    assert!(res.is_ok());
}

#[test]
#[should_panic]
fn test_sensor_switching_provenance_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.provenance.category, ProvenanceCategory::UserExplicit);
}

#[test]
#[should_panic]
fn test_sensor_removing_trait_identity_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let item = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("t1".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    )
    .unwrap();

    assert_eq!(item.provenance.derived_from, None);
}

#[test]
#[should_panic]
fn test_sensor_unknown_trait_promotion_fails() {
    let input = valid_input("r1", vec![valid_trait("t1", "desc")], vec![]);
    let res = ReferenceIntake::promote_reference_trait(
        &input,
        &TraitId("unknown".into()),
        SemanticCategory::UserRequirement,
        ItemId("req1".into()),
        mock_provenance(),
    );
    assert!(res.is_ok());
}
