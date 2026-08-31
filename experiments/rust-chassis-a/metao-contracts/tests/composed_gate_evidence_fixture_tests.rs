use serde_json::Value;
use std::collections::BTreeSet;

const FIXTURE: &str = include_str!("fixtures/composed_gate_evidence_records.v1.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("composed gate evidence fixture must be valid JSON")
}

#[test]
fn schema_and_vocabularies_are_explicit() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);
    assert_eq!(value["record_family"], "composed-validation-gate-evidence");
    let results: BTreeSet<&str> = value["allowed_results"].as_array().expect("allowed results").iter().map(|entry| entry.as_str().expect("result string")).collect();
    assert_eq!(results, BTreeSet::from(["BLOCKED", "FAIL", "NOT_REQUESTED", "PASS", "SKIPPED"]));
}

#[test]
fn record_ids_are_unique_and_exact_commit_is_required() {
    let value = fixture();
    let records = value["records"].as_array().expect("records");
    let mut ids = BTreeSet::new();
    for record in records {
        let id = record["record_id"].as_str().expect("record id");
        assert!(ids.insert(id));
        assert_eq!(record["repository"], "tihotm/metaO");
        let commit = record["commit"].as_str().expect("commit");
        assert_eq!(commit.len(), 40);
        assert!(commit.chars().all(|ch| ch.is_ascii_hexdigit()));
        assert!(record["claim_boundary"].as_str().is_some_and(|text| !text.trim().is_empty()));
    }
}

#[test]
fn blocked_fail_and_skipped_require_reason_and_classification() {
    let value = fixture();
    for record in value["records"].as_array().expect("records") {
        let result = record["result"].as_str().expect("result");
        if matches!(result, "BLOCKED" | "FAIL" | "SKIPPED") {
            assert!(record["reason"].as_str().is_some_and(|text| !text.trim().is_empty()));
            assert!(record["classification"].as_str().is_some_and(|text| !text.trim().is_empty()));
        }
        if matches!(result, "PASS" | "NOT_REQUESTED") { assert!(record["classification"].is_null()); }
    }
}

#[test]
fn pass_and_fail_require_actual_executed_repository_steps_and_evidence() {
    let value = fixture();
    for record in value["records"].as_array().expect("records") {
        let result = record["result"].as_str().expect("result");
        if matches!(result, "PASS" | "FAIL") {
            assert_eq!(record["repository_steps_executed"], true);
            assert!(record["commands"].as_array().is_some_and(|commands| !commands.is_empty()));
            assert!(record["evidence_ids"].as_array().is_some_and(|evidence| !evidence.is_empty()));
        }
    }
}

#[test]
fn pre_step_blocker_is_not_misreported_as_executed_gate() {
    let value = fixture();
    let blocked = value["records"].as_array().expect("records").iter().find(|record| record["result"] == "BLOCKED").expect("blocked fixture");
    assert_eq!(blocked["repository_steps_executed"], false);
    assert!(blocked["commands"].as_array().is_some_and(Vec::is_empty));
    assert_eq!(blocked["classification"], "BLOCKED_EXTERNAL_PRE_STEP");
    assert!(blocked["evidence_ids"].as_array().is_some_and(|evidence| !evidence.is_empty()));
}

#[test]
fn skipped_and_not_requested_are_distinct_and_not_executed() {
    let value = fixture();
    let records = value["records"].as_array().expect("records");
    let skipped = records.iter().find(|record| record["result"] == "SKIPPED").expect("skipped");
    let not_requested = records.iter().find(|record| record["result"] == "NOT_REQUESTED").expect("not requested");
    assert_ne!(skipped["record_id"], not_requested["record_id"]);
    assert!(skipped["reason"].is_string());
    assert!(not_requested["reason"].is_null());
    assert_eq!(skipped["repository_steps_executed"], false);
    assert_eq!(not_requested["repository_steps_executed"], false);
}

#[test]
fn substrate_and_real_external_flag_are_consistent() {
    let value = fixture();
    for record in value["records"].as_array().expect("records") {
        let substrate = record["substrate"].as_str().expect("substrate");
        let external_real = record["external_systems_real"].as_bool().expect("external_systems_real");
        let expected_real = matches!(substrate, "REAL_EXTERNAL_RUNTIME" | "REAL_EXTERNAL_SERVICE");
        assert_eq!(external_real, expected_real);
    }
}

#[test]
fn gate_level_and_timing_fields_are_machine_readable() {
    let value = fixture();
    let allowed: BTreeSet<&str> = value["allowed_gate_levels"].as_array().expect("levels").iter().map(|entry| entry.as_str().expect("level")).collect();
    for record in value["records"].as_array().expect("records") {
        let level = record["gate_level"].as_str().expect("gate level");
        assert!(allowed.contains(level));
        assert!(record["started_at"].as_str().is_some());
        assert!(record["ended_at"].as_str().is_some());
        assert!(record["duration_ms"].as_u64().is_some());
        assert!(record["commands"].as_array().is_some());
        assert!(record["repository_steps_executed"].as_bool().is_some());
        assert!(record["environment"].is_object());
        assert!(record["evidence_ids"].as_array().is_some());
    }
}

#[test]
fn evidence_record_has_no_acceptance_or_claim_promotion_authority() {
    let value = fixture();
    let boundary = &value["authority_boundary"];
    assert_eq!(boundary["record_is_product_acceptance"], false);
    assert_eq!(boundary["record_is_mission_acceptance"], false);
    assert_eq!(boundary["record_promotes_claim_automatically"], false);
    let serialized = serde_json::to_string(&value).expect("serialize fixture");
    for forbidden in ["AcceptanceDecision", "ProjectCompletionDecision", "dispatch_authority", "provider_sdk"] { assert!(!serialized.contains(forbidden)); }
}
