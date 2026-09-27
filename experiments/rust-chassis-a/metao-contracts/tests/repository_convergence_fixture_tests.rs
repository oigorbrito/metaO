use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

const FIXTURE: &str = include_str!("fixtures/repository_convergence_cases.v1.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("repository convergence fixture must be valid JSON")
}

fn cases_by_id(value: &Value) -> BTreeMap<&str, &Value> {
    value["cases"]
        .as_array()
        .expect("cases must be array")
        .iter()
        .map(|case| (case["id"].as_str().expect("case id"), case))
        .collect()
}

fn obligations(case: &Value) -> BTreeSet<&str> {
    case["obligations"]
        .as_array()
        .expect("obligations")
        .iter()
        .map(|value| value.as_str().expect("obligation string"))
        .collect()
}

#[test]
fn fixture_identity_and_safety_metrics_are_explicit() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);
    assert_eq!(
        value["fixture_family"],
        "repository-convergence-ground-truth"
    );
    assert_eq!(value["expected_metrics"]["false_close"], 0);
    assert_eq!(value["expected_metrics"]["protected_experiment_loss"], 0);
    assert_eq!(value["expected_metrics"]["dependency_break"], 0);
    assert_eq!(value["expected_metrics"]["result_reproducible"], true);
    assert_eq!(value["authority_boundary"]["fixture_mutates_github"], false);
    assert_eq!(
        value["authority_boundary"]["similarity_is_close_authority"],
        false
    );
    assert_eq!(
        value["authority_boundary"]["inactivity_is_obsolescence"],
        false
    );
}

#[test]
fn all_case_ids_are_unique_and_required_classes_exist() {
    let value = fixture();
    let cases = value["cases"].as_array().expect("cases");
    let ids: BTreeSet<&str> = cases
        .iter()
        .map(|case| case["id"].as_str().expect("case id"))
        .collect();
    assert_eq!(ids.len(), cases.len());

    for required in [
        "active-canonical-discovery",
        "blocked-hosted-runner",
        "stack-parent-runtime-contract",
        "stack-child-runtime-adapter",
        "docs-only-composition-record",
        "duplicate-reference-intake-old",
        "superseded-runtime-health-slice-old",
        "partial-integration-with-unique-obligation",
        "protected-chassis-spike-a",
        "protected-chassis-spike-b",
        "protected-chassis-spike-c",
    ] {
        assert!(
            ids.contains(required),
            "missing required fixture class: {required}"
        );
    }
}

#[test]
fn safe_supersession_requires_obligation_containment() {
    let value = fixture();
    let cases = cases_by_id(&value);

    for case in cases.values() {
        if case["safe_to_close"] == true && case["expected_disposition"] == "ABSORBED" {
            let successor_id = case["superseded_by"]
                .as_str()
                .expect("absorbed item must identify canonical successor");
            let successor = cases
                .get(successor_id)
                .expect("canonical successor must exist in fixture");
            let old = obligations(case);
            let new = obligations(successor);
            assert!(
                old.is_subset(&new),
                "successor must contain every old obligation"
            );
            assert!(!case["protected"].as_bool().expect("protected flag"));
            assert!(case["blocked_by"].is_null());
        }
    }
}

#[test]
fn partial_integration_with_unique_obligation_cannot_be_superseded() {
    let value = fixture();
    let cases = cases_by_id(&value);
    let partial = cases["partial-integration-with-unique-obligation"];
    let proposed_successor = cases["superseding-runtime-health-slice-new"];

    let remaining: BTreeSet<_> = obligations(partial)
        .difference(&obligations(proposed_successor))
        .copied()
        .collect();
    assert_eq!(remaining, BTreeSet::from(["strategy-health-consumption"]));
    assert_eq!(partial["safe_to_close"], false);
    assert_eq!(partial["expected_disposition"], "ACTIVE_CANONICAL");
}

#[test]
fn protected_evidence_is_never_safe_to_close() {
    let value = fixture();
    for case in value["cases"].as_array().expect("cases") {
        if case["protected"] == true {
            assert_eq!(case["expected_disposition"], "PROTECTED_EVIDENCE");
            assert_eq!(case["safe_to_close"], false);
        }
    }
}

#[test]
fn blocked_work_remains_explicit_and_open() {
    let value = fixture();
    for case in value["cases"].as_array().expect("cases") {
        if !case["blocked_by"].is_null() {
            assert_eq!(case["expected_disposition"], "BLOCKED_EXTERNAL");
            assert_eq!(case["safe_to_close"], false);
            assert!(case["blocked_by"]
                .as_str()
                .is_some_and(|value| !value.trim().is_empty()));
        }
    }
}

#[test]
fn stack_dependency_is_preserved() {
    let value = fixture();
    let cases = cases_by_id(&value);
    let parent = cases["stack-parent-runtime-contract"];
    let child = cases["stack-child-runtime-adapter"];

    assert_eq!(parent["safe_to_close"], false);
    assert!(child["dependencies"]
        .as_array()
        .expect("dependencies")
        .iter()
        .any(|dependency| dependency == "stack-parent-runtime-contract"));
}

#[test]
fn known_duplicate_and_superseded_cases_are_not_left_active_in_ground_truth() {
    let value = fixture();
    let cases = cases_by_id(&value);

    for id in [
        "duplicate-reference-intake-old",
        "superseded-runtime-health-slice-old",
    ] {
        let case = cases[id];
        assert_eq!(case["expected_disposition"], "ABSORBED");
        assert_eq!(case["safe_to_close"], true);
    }

    assert_eq!(value["expected_metrics"]["known_duplicate_left_active"], 0);
    assert_eq!(value["expected_metrics"]["known_superseded_left_active"], 0);
}
