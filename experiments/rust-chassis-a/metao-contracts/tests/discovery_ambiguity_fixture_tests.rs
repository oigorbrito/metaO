use serde_json::Value;
use std::collections::BTreeSet;

const FIXTURE: &str = include_str!("fixtures/discovery_ambiguity_cases.v1.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("discovery ambiguity fixture must be valid JSON")
}

#[test]
fn fixture_schema_and_source_pins_are_explicit() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);

    let sources = value["sources"]
        .as_array()
        .expect("sources must be an array");
    assert!(sources.iter().any(|source| {
        source["reference"] == "fangz-cs/ClarifyCodeBench"
            && source["pinned_revision"] == "5e2d5b5ce6259daa034cebb69f65e5e4c6dec3e9"
    }));
    assert!(sources
        .iter()
        .any(|source| source["reference"] == "arXiv:2608.09072v1"));
}

#[test]
fn fixture_ids_are_unique_and_order_is_stable() {
    let value = fixture();
    let scenarios = value["scenarios"]
        .as_array()
        .expect("scenarios must be an array");

    let ids: Vec<&str> = scenarios
        .iter()
        .map(|scenario| {
            scenario["fixture_id"]
                .as_str()
                .expect("fixture_id must be a string")
        })
        .collect();
    let unique: BTreeSet<&str> = ids.iter().copied().collect();

    assert_eq!(ids.len(), unique.len());
    assert_eq!(
        ids,
        vec![
            "behavior-payment-scope-material",
            "ordering-atomicity-checkout-security",
            "output-format-admin-date-display",
            "terminology-local-variable-naming",
            "behavior-web-vs-mobile-scope",
            "behavior-user-fixed-technology-conflict",
            "multi-ambiguity-marketplace-intake",
        ]
    );
}

#[test]
fn fixture_actions_are_clarification_only() {
    let value = fixture();
    let scenarios = value["scenarios"]
        .as_array()
        .expect("scenarios must be an array");
    let allowed = BTreeSet::from([
        "ASK_HUMAN",
        "RECORD_SAFE_ASSUMPTION",
        "ASK_HUMAN_WITH_SAFE_ASSUMPTION_FOR_NON_BLOCKER",
    ]);

    for scenario in scenarios {
        let action = scenario["expected_action"]
            .as_str()
            .expect("expected_action must be a string");
        assert!(allowed.contains(action), "unexpected action: {action}");

        if let Some(items) = scenario.get("items").and_then(Value::as_array) {
            for item in items {
                let item_action = item["expected_action"]
                    .as_str()
                    .expect("item expected_action must be a string");
                assert!(
                    matches!(item_action, "ASK_HUMAN" | "RECORD_SAFE_ASSUMPTION"),
                    "unexpected item action: {item_action}"
                );
            }
        }
    }
}

#[test]
fn safe_defaults_exist_only_on_non_material_reversible_items() {
    let value = fixture();
    let scenarios = value["scenarios"]
        .as_array()
        .expect("scenarios must be an array");

    for scenario in scenarios {
        if scenario["safe_default"].is_object() {
            assert_eq!(scenario["materiality"], "NON_MATERIAL");
            assert_eq!(scenario["reversibility"], "REVERSIBLE");
            assert_eq!(scenario["expected_action"], "RECORD_SAFE_ASSUMPTION");
        }

        if let Some(items) = scenario.get("items").and_then(Value::as_array) {
            for item in items {
                if item["safe_default"].is_object() {
                    assert_eq!(item["materiality"], "NON_MATERIAL");
                    assert_eq!(item["reversibility"], "REVERSIBLE");
                    assert_eq!(item["expected_action"], "RECORD_SAFE_ASSUMPTION");
                }
            }
        }
    }
}

#[test]
fn benchmark_labels_are_metadata_not_materiality() {
    let value = fixture();
    let scenarios = value["scenarios"]
        .as_array()
        .expect("scenarios must be an array");

    let output_format = scenarios
        .iter()
        .find(|scenario| scenario["fixture_id"] == "output-format-admin-date-display")
        .expect("output format fixture must exist");
    let payment = scenarios
        .iter()
        .find(|scenario| scenario["fixture_id"] == "behavior-payment-scope-material")
        .expect("payment fixture must exist");
    let web_mobile = scenarios
        .iter()
        .find(|scenario| scenario["fixture_id"] == "behavior-web-vs-mobile-scope")
        .expect("web/mobile fixture must exist");

    assert_eq!(output_format["benchmark_inspired_label"], "Output Format");
    assert_eq!(output_format["materiality"], "NON_MATERIAL");
    assert_eq!(payment["benchmark_inspired_label"], "Behavior");
    assert_eq!(payment["materiality"], "MATERIAL");
    assert_eq!(web_mobile["benchmark_inspired_label"], "Behavior");
    assert_eq!(web_mobile["materiality"], "MATERIAL");
}

#[test]
fn corpus_does_not_mint_readiness_or_acceptance_authority() {
    let value = fixture();
    let forbidden = value["forbidden_authority_outputs"]
        .as_array()
        .expect("forbidden authority outputs must be an array");

    for scenario in value["scenarios"]
        .as_array()
        .expect("scenarios must be an array")
    {
        let action = scenario["expected_action"]
            .as_str()
            .expect("expected_action must be a string");
        assert!(!forbidden.iter().any(|entry| entry == action));
    }

    let serialized_scenarios = serde_json::to_string(&value["scenarios"])
        .expect("fixture scenarios must serialize deterministically");
    for authority in ["SPEC_READY", "PLAN_READY", "PROJECT_ACCEPTED", "ACCEPTED"] {
        assert!(!serialized_scenarios.contains(authority));
    }
}
