use serde_json::Value;
use std::collections::BTreeSet;
use std::path::Path;

const TRACEABILITY: &str = include_str!("fixtures/formal_invariant_traceability.v1.json");

fn fixture() -> Value {
    serde_json::from_str(TRACEABILITY).expect("formal invariant traceability fixture must be valid JSON")
}

fn repository_root() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
}

#[test]
fn model_identity_and_claim_boundary_are_explicit() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);
    assert_eq!(value["source_model"]["model"], "AcceptanceRetryAuthority");
    assert_eq!(value["source_model"]["model_evidence_state"], "MODEL_NOT_CHECKED");

    let boundary = &value["authority_boundary"];
    assert_eq!(boundary["traceability_is_execution"], false);
    assert_eq!(boundary["model_invariant_is_implementation_proof"], false);
    assert_eq!(boundary["test_path_present_is_test_pass"], false);
    assert_eq!(boundary["python_oracle_is_rust_authority"], false);
}

#[test]
fn every_named_formal_invariant_has_one_unique_mapping() {
    let value = fixture();
    let mappings = value["mappings"].as_array().expect("mappings must be array");
    let expected = BTreeSet::from([
        "AcceptedGenerationMatchesCurrent",
        "AcceptedRequiresIndependentFreshPass",
        "IncompleteRecoveryCannotEnableRetry",
        "OldGenerationDoneCannotAcceptCurrent",
        "OrchestratorDoneIsNotAcceptance",
        "StaleEvidenceCannotAcceptCurrentGeneration",
        "UnknownNeverAccepts",
    ]);
    let actual: BTreeSet<&str> = mappings
        .iter()
        .map(|mapping| mapping["invariant_id"].as_str().expect("invariant id"))
        .collect();

    assert_eq!(actual, expected);
    assert_eq!(actual.len(), mappings.len());
}

#[test]
fn implementation_targets_are_traceable_but_never_reported_as_executed() {
    let value = fixture();
    let root = repository_root();

    for mapping in value["mappings"].as_array().expect("mappings") {
        assert_eq!(mapping["execution_state"], "EXECUTION_NOT_RUN");
        match mapping["implementation_state"].as_str().expect("implementation state") {
            "TEST_PATH_PRESENT" => {
                let targets = mapping["rust_targets"].as_array().expect("rust targets");
                assert!(!targets.is_empty());
                for target in targets {
                    let relative = target.as_str().expect("target path");
                    assert!(root.join(relative).is_file(), "missing mapped test target: {relative}");
                }
            }
            "PENDING_BRANCH_TARGET" => {
                assert!(mapping["rust_targets"].as_array().is_some_and(Vec::is_empty));
                assert!(mapping["pending_owner"]["issue"].as_u64().is_some());
                assert!(mapping["pending_owner"]["pull_request"].as_u64().is_some());
                assert!(mapping["pending_branch"]
                    .as_str()
                    .is_some_and(|value| !value.trim().is_empty()));
                let pending_targets = mapping["pending_rust_targets"]
                    .as_array()
                    .expect("pending rust targets");
                assert!(!pending_targets.is_empty());
            }
            state => panic!("unexpected implementation state: {state}"),
        }
    }
}

#[test]
fn pending_branch_target_is_not_misreported_as_current_main_coverage() {
    let value = fixture();
    let recovery = value["mappings"]
        .as_array()
        .expect("mappings")
        .iter()
        .find(|mapping| mapping["invariant_id"] == "IncompleteRecoveryCannotEnableRetry")
        .expect("recovery invariant mapping");

    assert_eq!(recovery["implementation_state"], "PENDING_BRANCH_TARGET");
    assert_eq!(recovery["execution_state"], "EXECUTION_NOT_RUN");
    assert_eq!(recovery["pending_owner"]["issue"], 315);
    assert_eq!(recovery["pending_owner"]["pull_request"], 318);
    assert_eq!(recovery["pending_branch"], "post-v0.1/failure-retry-causality-v1");
}

#[test]
fn python_oracle_targets_are_present_but_never_rust_authority() {
    let value = fixture();
    let root = repository_root();

    for mapping in value["mappings"].as_array().expect("mappings") {
        for target in mapping["python_oracle_targets"]
            .as_array()
            .expect("python oracle targets")
        {
            let relative = target.as_str().expect("python target path");
            assert!(root.join(relative).is_file(), "missing oracle target: {relative}");
        }
    }

    let serialized = serde_json::to_string(&value).expect("serialize traceability");
    for forbidden in ["EXECUTED_PASS", "AcceptanceDecisionAuthority", "provider_sdk"] {
        assert!(!serialized.contains(forbidden));
    }
}
