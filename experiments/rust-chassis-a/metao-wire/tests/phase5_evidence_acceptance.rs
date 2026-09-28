use std::time::Duration;

use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, ExecutionRequest,
    ExecutionResult, ExecutionStatus, MissionId, Orchestrator, RuntimeId,
};
use metao_kernel::canonical_acceptance;
use metao_registry::{Registry, RegistryError};
use metao_wire::{execute_with_recovery, RecoveryPolicy, RuntimeExecutionOutcome, WireRequest};
use serde::Serialize;
use serde_json::json;
use sha2::{Digest, Sha256};

fn runtime_binary() -> &'static str {
    env!("CARGO_BIN_EXE_metao-wire-runtime")
}

fn mission_id() -> MissionId {
    MissionId::new("phase5-mission-1").unwrap()
}

fn execution_id() -> ExecutionId {
    ExecutionId::new("phase5-exec-1").unwrap()
}

fn request(objective: &str) -> WireRequest {
    WireRequest {
        protocol_version: metao_wire::PROTOCOL_VERSION,
        execution_id: execution_id().as_str().to_string(),
        mission_id: mission_id().as_str().to_string(),
        objective: objective.into(),
    }
}

fn acceptance_context(runtime_id: &RuntimeId) -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "subject-5".into(),
        subject_state_id: "state-5".into(),
        verification_context_id: "verify-5".into(),
        policy_bundle_id: "policy-5".into(),
        required_obligations: vec!["execution_result".into()],
        trusted_verifiers: vec!["verifier-5".into()],
        trusted_provenance_roots: vec![format!(
            "evidence:{}:{}",
            runtime_id.as_str(),
            execution_id().as_str()
        )],
        authorized_authorities: vec!["authority-5".into()],
    }
}

fn digest_payload<T: Serialize>(payload: &T) -> String {
    let bytes = serde_json::to_vec(payload).expect("stable evidence payload serialization");
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn normalize_evidence<T: Serialize>(
    payload: &T,
    runtime_id: &RuntimeId,
    attempt_id: &str,
    created_at_epoch: f64,
    expires_at_epoch: Option<f64>,
) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: format!("{}:result", execution_id().as_str()),
        obligation_id: "execution_result".into(),
        mission_id: mission_id(),
        execution_id: execution_id(),
        orchestrator_id: runtime_id.clone(),
        adapter_version: "wire-1".into(),
        attempt_id: attempt_id.into(),
        subject_id: "subject-5".into(),
        subject_state_id: "state-5".into(),
        verification_context_id: "verify-5".into(),
        policy_bundle_id: "policy-5".into(),
        verifier_id: "verifier-5".into(),
        payload_digest: digest_payload(&json!({ "payload": payload })),
        provenance_root: format!(
            "evidence:{}:{}",
            runtime_id.as_str(),
            execution_id().as_str()
        ),
        authority_id: "authority-5".into(),
        passed: true,
        created_at_epoch,
        expires_at_epoch,
        approval_id: None,
        confidence: None,
    }
}

fn wire_success(objective: &str) -> metao_wire::WireResponse {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request(objective),
        RecoveryPolicy::new(0, Duration::from_millis(200)),
    );
    match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            assert_eq!(attempts, 1);
            response
        }
        other => panic!("unexpected runtime outcome: {other:?}"),
    }
}

fn wire_recovered_success(objective: &str) -> metao_wire::WireResponse {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request(objective),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            assert_eq!(attempts, 2);
            response
        }
        other => panic!("unexpected recovered runtime outcome: {other:?}"),
    }
}

#[test]
fn success_without_evidence_is_not_done() {
    let response = wire_success("normal");
    assert_eq!(response.status, "SUCCEEDED");

    let result = canonical_acceptance(
        &acceptance_context(&RuntimeId::new(response.runtime_id).unwrap()),
        &[],
        30.0,
    );
    assert_eq!(result.decision, AcceptanceDecision::NotDone);
}

#[test]
fn success_with_valid_evidence_accepts() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    let context = acceptance_context(&runtime_id);

    let result = canonical_acceptance(&context, &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
    assert!(result.proof.is_some());
}

#[test]
fn recovered_success_without_evidence_is_not_done() {
    let response = wire_recovered_success("__crash_then_recover__");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[], 30.0);
    assert_eq!(response.status, "SUCCEEDED");
    assert_eq!(result.decision, AcceptanceDecision::NotDone);
}

#[test]
fn recovered_success_with_valid_evidence_accepts() {
    let response = wire_recovered_success("__crash_then_recover__");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-2",
        20.0,
        Some(40.0),
    );
    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Accept);
}

#[test]
fn stale_evidence_after_success_is_stale() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(25.0),
    );

    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Stale);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "evidence_expired"));
}

#[test]
fn subject_misbound_evidence_never_accepts() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let mut evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    evidence.subject_id = "other-subject".into();

    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "subject_mismatch"));
}

#[test]
fn subject_state_misbound_is_stale() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let mut evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    evidence.subject_state_id = "other-state".into();

    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Stale);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "subject_state_mismatch"));
}

#[test]
fn verification_context_mismatch_blocks() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let mut evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    evidence.verification_context_id = "other-ctx".into();

    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "verification_context_mismatch"));
}

#[test]
fn policy_bundle_mismatch_blocks() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let mut evidence = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    evidence.policy_bundle_id = "other-policy".into();

    let result = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "policy_bundle_mismatch"));
}

#[test]
fn provenance_mismatch_blocks() {
    let response = wire_success("normal");
    let runtime_id = RuntimeId::new(response.runtime_id.clone()).unwrap();
    let base = normalize_evidence(
        &json!({"result": response.result}),
        &runtime_id,
        "attempt-1",
        20.0,
        Some(40.0),
    );
    let context = acceptance_context(&runtime_id);

    let mut verifier = base.clone();
    verifier.verifier_id = "evil-verifier".into();
    let result = canonical_acceptance(&context, &[verifier], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "untrusted_verifier"));

    let mut root = base.clone();
    root.provenance_root = "evil-root".into();
    let result = canonical_acceptance(&context, &[root], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "untrusted_provenance_root"));

    let mut authority = base;
    authority.authority_id = "evil-authority".into();
    let result = canonical_acceptance(&context, &[authority], 30.0);
    assert_eq!(result.decision, AcceptanceDecision::Block);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "unauthorized_authority"));
}

struct CrashRuntime;
struct BackupRuntime;

fn runtime_id(value: &str) -> RuntimeId {
    RuntimeId::new(value).unwrap()
}

impl Orchestrator for CrashRuntime {
    fn id(&self) -> RuntimeId {
        runtime_id("orch-a")
    }

    fn version(&self) -> String {
        "1".into()
    }

    fn execute(&self, _: &ExecutionRequest) -> ExecutionResult {
        panic!("simulated failover crash")
    }
}

impl Orchestrator for BackupRuntime {
    fn id(&self) -> RuntimeId {
        runtime_id("orch-b")
    }

    fn version(&self) -> String {
        "1".into()
    }

    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: request.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}

fn contract_request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: execution_id(),
        mission_id: mission_id(),
    }
}

#[test]
fn failover_success_without_evidence_is_not_done() {
    let mut registry = Registry::default();
    registry.register(Box::new(CrashRuntime)).unwrap();
    registry.register(Box::new(BackupRuntime)).unwrap();

    assert_eq!(
        registry.execute_contained(&runtime_id("orch-a"), &contract_request()),
        Err(RegistryError::Panicked(runtime_id("orch-a")))
    );

    let result = registry
        .execute_contained(&runtime_id("orch-b"), &contract_request())
        .expect("backup runtime should execute");
    assert_eq!(result.status, ExecutionStatus::Succeeded);

    let context = acceptance_context(&result.runtime_id);
    let decision = canonical_acceptance(&context, &[], 30.0);
    assert_eq!(decision.decision, AcceptanceDecision::NotDone);
}

#[test]
fn failover_success_with_valid_evidence_accepts() {
    let mut registry = Registry::default();
    registry.register(Box::new(CrashRuntime)).unwrap();
    registry.register(Box::new(BackupRuntime)).unwrap();

    let result = registry
        .execute_contained(&runtime_id("orch-b"), &contract_request())
        .expect("backup runtime should execute");
    let runtime_id = result.runtime_id.clone();
    let evidence = normalize_evidence(
        &json!({
            "runtime_id": runtime_id.as_str(),
            "status": "SUCCEEDED"
        }),
        &runtime_id,
        "attempt-2",
        20.0,
        Some(40.0),
    );

    let decision = canonical_acceptance(&acceptance_context(&runtime_id), &[evidence], 30.0);
    assert_eq!(decision.decision, AcceptanceDecision::Accept);
    assert!(decision.proof.is_some());
}
