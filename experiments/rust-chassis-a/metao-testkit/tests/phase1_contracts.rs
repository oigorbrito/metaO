use metao_contracts::{AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, MissionId};
use metao_kernel::canonical_acceptance;
use serde::Deserialize;
use std::process::Command;

#[derive(Debug, Deserialize)]
struct Fixture {
    fixture_version: u32,
    contract_version: u32,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct Case {
    name: String,
    kind: String,
    input: serde_json::Value,
    expected: Expected,
}

#[derive(Debug, Deserialize)]
struct Expected {
    decision: String,
}

#[derive(Debug, Deserialize)]
struct ContextInput {
    subject_id: String,
    subject_state_id: String,
    verification_context_id: String,
    policy_bundle_id: String,
    required_obligations: Vec<String>,
    trusted_verifiers: Vec<String>,
    trusted_provenance_roots: Vec<String>,
    authorized_authorities: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct AcceptanceInput {
    context: ContextInput,
    evidence: Vec<EvidenceEnvelope>,
    now_epoch: f64,
}

#[derive(Debug, Deserialize)]
struct IdentityInput {
    mission_id: String,
}

fn load_fixture() -> Fixture {
    serde_json::from_str(include_str!(concat!(
        "../../../../tests/golden/phase1_contracts_v1.json"
    )))
    .expect("parse phase1 fixture")
}

fn workspace_root() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .to_path_buf()
}

fn context(input: &ContextInput) -> AcceptanceContext {
    AcceptanceContext {
        subject_id: input.subject_id.clone(),
        subject_state_id: input.subject_state_id.clone(),
        verification_context_id: input.verification_context_id.clone(),
        policy_bundle_id: input.policy_bundle_id.clone(),
        required_obligations: input.required_obligations.clone(),
        trusted_verifiers: input.trusted_verifiers.clone(),
        trusted_provenance_roots: input.trusted_provenance_roots.clone(),
        authorized_authorities: input.authorized_authorities.clone(),
    }
}

fn normalize(decision: AcceptanceDecision) -> &'static str {
    match decision {
        AcceptanceDecision::Accept => "ACCEPT",
        AcceptanceDecision::Block => "BLOCK",
        AcceptanceDecision::NotDone => "NOT_DONE",
        AcceptanceDecision::Stale => "STALE",
        AcceptanceDecision::RequireHuman => "REQUIRE_HUMAN",
    }
}

#[test]
fn cross_language_contract_replay_matches_python_oracle() {
    let fixture = load_fixture();
    assert_eq!(fixture.fixture_version, 1);
    assert_eq!(fixture.contract_version, metao_contracts::CONTRACT_VERSION);

    let root = workspace_root();
    let python = Command::new("python")
        .arg(root.join("tests").join("phase1_oracle.py"))
        .arg(
            root.join("tests")
                .join("golden")
                .join("phase1_contracts_v1.json"),
        )
        .output()
        .expect("run python oracle");
    assert!(
        python.status.success(),
        "python oracle failed: {}",
        String::from_utf8_lossy(&python.stderr)
    );
    let python_results: Vec<serde_json::Value> =
        serde_json::from_slice(&python.stdout).expect("parse python oracle results");

    let mut rust_results = Vec::new();
    for case in &fixture.cases {
        let rust_case = match case.kind.as_str() {
            "acceptance" => {
                let input: AcceptanceInput =
                    serde_json::from_value(case.input.clone()).expect("parse acceptance case");
                let result = canonical_acceptance(
                    &context(&input.context),
                    &input.evidence,
                    input.now_epoch,
                );
                assert_eq!(
                    normalize(result.decision),
                    case.expected.decision.as_str(),
                    "expected mismatch for {}",
                    case.name
                );
                let proof = result
                    .proof
                    .expect("acceptance result must carry parity proof");
                serde_json::json!({
                    "name": case.name,
                    "decision": normalize(result.decision),
                    "reasons": result.reasons,
                    "proof_digest": proof.digest,
                })
            }
            "identity" => {
                let input: IdentityInput =
                    serde_json::from_value(case.input.clone()).expect("parse identity case");
                let decision = if MissionId::new(input.mission_id).is_err() {
                    "REJECT"
                } else {
                    "ACCEPT"
                };
                assert_eq!(
                    decision,
                    case.expected.decision.as_str(),
                    "expected mismatch for {}",
                    case.name
                );
                serde_json::json!({
                    "name": case.name,
                    "decision": decision,
                })
            }
            other => panic!("unexpected differential case kind {other}"),
        };
        rust_results.push(rust_case);
    }

    assert_eq!(
        python_results.len(),
        rust_results.len(),
        "oracle result cardinality mismatch"
    );
    for (python_case, rust_case) in python_results.iter().zip(rust_results.iter()) {
        assert_eq!(python_case, rust_case);
    }
}
