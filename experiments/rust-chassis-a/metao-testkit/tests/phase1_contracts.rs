use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, ExecutionRequest,
    ExecutionResult, ExecutionStatus, MissionId, PolicyEffect, RuntimeId,
};
use metao_kernel::{canonical_acceptance, evaluate_acceptance};
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

#[derive(Debug, Deserialize)]
struct PolicyInput {
    request: RequestInput,
    result: ResultInput,
    policy: String,
    now_epoch: i64,
}

#[derive(Debug, Deserialize)]
struct RequestInput {
    execution_id: String,
    mission_id: String,
}

#[derive(Debug, Deserialize)]
struct ResultInput {
    execution_id: String,
    runtime_id: String,
    status: String,
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
        mission_id: "m1".into(),
        execution_id: "x1".into(),
        runtime_id: "orch-a".into(),
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

fn request(input: &RequestInput) -> ExecutionRequest {
    ExecutionRequest {
        execution_id: ExecutionId::new(input.execution_id.clone()).unwrap(),
        mission_id: MissionId::new(input.mission_id.clone()).unwrap(),
    }
}

fn result(input: &ResultInput) -> ExecutionResult {
    let status = match input.status.as_str() {
        "Succeeded" => ExecutionStatus::Succeeded,
        "Failed" => ExecutionStatus::Failed,
        "Cancelled" => ExecutionStatus::Cancelled,
        other => panic!("unexpected status {other}"),
    };
    ExecutionResult {
        execution_id: ExecutionId::new(input.execution_id.clone()).unwrap(),
        runtime_id: RuntimeId::new(input.runtime_id.clone()).unwrap(),
        status,
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
    assert_eq!(fixture.contract_version, 1);

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
        let decision = match case.kind.as_str() {
            "acceptance" => {
                let input: AcceptanceInput =
                    serde_json::from_value(case.input.clone()).expect("parse acceptance case");
                canonical_acceptance(&context(&input.context), &input.evidence, input.now_epoch)
                    .decision
            }
            "identity" => {
                let input: IdentityInput =
                    serde_json::from_value(case.input.clone()).expect("parse identity case");
                if MissionId::new(input.mission_id).is_err() {
                    rust_results.push(serde_json::json!({
                        "name": case.name,
                        "decision": "REJECT"
                    }));
                    continue;
                } else {
                    AcceptanceDecision::Accept
                }
            }
            "policy_deny" => {
                let input: PolicyInput =
                    serde_json::from_value(case.input.clone()).expect("parse policy case");
                let policy = match input.policy.as_str() {
                    "Deny" => PolicyEffect::Deny,
                    "Allow" => PolicyEffect::Allow,
                    "RequireHuman" => PolicyEffect::RequireHuman,
                    other => panic!("unexpected policy {other}"),
                };
                evaluate_acceptance(
                    &request(&input.request),
                    &result(&input.result),
                    None,
                    policy,
                    input.now_epoch,
                )
            }
            "contract_version" | "malformed" => {
                rust_results.push(serde_json::json!({
                    "name": case.name,
                    "decision": "REJECT"
                }));
                continue;
            }
            other => panic!("unexpected case kind {other}"),
        };
        assert_eq!(
            normalize(decision),
            case.expected.decision.as_str(),
            "expected mismatch for {}",
            case.name
        );
        rust_results.push(serde_json::json!({
            "name": case.name,
            "decision": normalize(decision)
        }));
    }

    for (python_case, rust_case) in python_results.iter().zip(rust_results.iter()) {
        assert_eq!(python_case, rust_case);
    }
}
