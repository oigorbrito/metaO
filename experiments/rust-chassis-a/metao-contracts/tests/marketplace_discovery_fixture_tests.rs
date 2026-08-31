use serde_json::Value;
use std::collections::BTreeSet;

const FIXTURE: &str = include_str!("fixtures/marketplace_discovery_case.v1.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("marketplace fixture must be valid JSON")
}

#[test]
fn marketplace_fixture_schema_and_identity_are_stable() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);
    assert_eq!(value["fixture_id"], "marketplace-discovery-v1");
    assert_eq!(value["initial_intent"], "Build a marketplace.");
    assert_eq!(value["initial_readiness"], "NOT_READY");
}

#[test]
fn initial_vague_intent_contains_material_blockers() {
    let value = fixture();
    let questions = value["material_questions"]
        .as_array()
        .expect("material questions must be an array");
    assert!(questions.len() >= 5);
    assert!(questions
        .iter()
        .all(|question| question["materiality"] == "MATERIAL"));

    let topics: BTreeSet<_> = questions
        .iter()
        .map(|question| question["topic"].as_str().expect("topic"))
        .collect();
    for required in [
        "marketplace_model",
        "payment_scope",
        "admin_backoffice",
        "web_mobile_scope",
        "technical_stack_mode",
    ] {
        assert!(topics.contains(required));
    }
}

#[test]
fn references_preserve_selected_traits_instead_of_becoming_requirements_wholesale() {
    let value = fixture();
    let references = value["references"].as_array().expect("references array");
    assert_eq!(references.len(), 3);
    for reference in references {
        assert!(reference["reference_id"].as_str().is_some());
        assert!(reference["name"].as_str().is_some());
        let traits = reference["selected_traits"]
            .as_array()
            .expect("selected traits array");
        assert!(!traits.is_empty());
        assert!(reference.get("requirement").is_none());
        assert!(reference.get("user_requirement").is_none());
    }
}

#[test]
fn technical_stack_mode_is_explicit_and_non_fixed_override_semantics_are_recorded() {
    let value = fixture();
    let stack = &value["technical_preference"];
    assert_eq!(stack["mode"], "USER_PREFERRED");
    assert!(stack["rationale"]
        .as_str()
        .expect("rationale")
        .contains("override"));
    assert!(stack["source"].as_str().is_some());
}

#[test]
fn resolved_projection_is_full_stack_and_has_explicit_scope() {
    let value = fixture();
    let projection = &value["expected_contract_projection"];

    let actors: BTreeSet<_> = projection["target_actors"]
        .as_array()
        .expect("actors")
        .iter()
        .map(|v| v.as_str().expect("actor"))
        .collect();
    assert_eq!(actors, BTreeSet::from(["admin", "buyer", "seller"]));

    let surfaces = projection["required_surfaces"]
        .as_array()
        .expect("required surfaces");
    let capabilities = projection["required_capabilities"]
        .as_array()
        .expect("required capabilities");
    let constraints = projection["technical_constraints"]
        .as_array()
        .expect("technical constraints");
    assert!(!surfaces.is_empty());
    assert!(!capabilities.is_empty());
    assert!(constraints
        .iter()
        .any(|v| v == "durable backend persistence"));
    assert!(constraints
        .iter()
        .any(|v| v == "server-side authorization for protected actions"));
}

#[test]
fn payment_logistics_and_native_mobile_are_explicitly_out_of_scope() {
    let value = fixture();
    let out_of_scope: BTreeSet<_> = value["expected_contract_projection"]["out_of_scope"]
        .as_array()
        .expect("out of scope")
        .iter()
        .map(|v| v.as_str().expect("scope item"))
        .collect();
    assert!(out_of_scope.contains("in-platform payment processing"));
    assert!(out_of_scope.contains("logistics/fulfillment integration"));
    assert!(out_of_scope.contains("native mobile application"));
}

#[test]
fn minimum_e2e_journeys_and_definition_of_done_are_explicit() {
    let value = fixture();
    let projection = &value["expected_contract_projection"];
    assert!(
        projection["minimum_e2e_journeys"]
            .as_array()
            .expect("journeys")
            .len()
            >= 3
    );
    assert!(
        projection["definition_of_done"]
            .as_array()
            .expect("definition of done")
            .len()
            >= 6
    );
}

#[test]
fn safe_defaults_remain_assumptions() {
    let value = fixture();
    let assumptions = value["assumptions"].as_array().expect("assumptions");
    assert_eq!(assumptions.len(), 1);
    assert!(assumptions[0]["rationale"].as_str().is_some());
    assert!(assumptions[0]["source"].as_str().is_some());
}

#[test]
fn fixture_has_no_readiness_planning_or_acceptance_authority() {
    let value = fixture();
    let authority = &value["fixture_authority"];
    assert_eq!(authority["can_mint_spec_ready"], false);
    assert_eq!(authority["can_mint_plan_ready"], false);
    assert_eq!(authority["can_mint_project_accepted"], false);

    let encoded = serde_json::to_string(&value).expect("serialize fixture");
    for forbidden in ["SPEC_READY", "PLAN_READY", "MVP_ACCEPTED"] {
        assert!(!encoded.contains(forbidden));
    }
}

#[test]
fn question_and_reference_ids_are_unique() {
    let value = fixture();
    let question_ids: Vec<_> = value["material_questions"]
        .as_array()
        .expect("questions")
        .iter()
        .map(|v| v["id"].as_str().expect("question id"))
        .collect();
    let unique_question_ids: BTreeSet<_> = question_ids.iter().copied().collect();
    assert_eq!(question_ids.len(), unique_question_ids.len());

    let reference_ids: Vec<_> = value["references"]
        .as_array()
        .expect("references")
        .iter()
        .map(|v| v["reference_id"].as_str().expect("reference id"))
        .collect();
    let unique_reference_ids: BTreeSet<_> = reference_ids.iter().copied().collect();
    assert_eq!(reference_ids.len(), unique_reference_ids.len());
}
