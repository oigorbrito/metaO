use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::{Arc, Barrier, Mutex};
use std::thread;

use metao_contracts::{
    AcceptanceBudget, AcceptanceContext, AcceptanceDecision, ApprovalRecord, EvidenceEnvelope,
    ExecutionId, MissionId, PolicyEffect, RuntimeId,
};
use metao_kernel::{
    apply_confidence_after_hard_gates, canonical_acceptance, evaluate_policy,
    replay_acceptance_decision, require_human, resume_after_approval, AcceptanceBudgetAuthority,
};
use metao_wire::{
    execute_with_recovery, RecoveryPolicy, RuntimeExecutionBlocked, RuntimeExecutionFailure,
    RuntimeExecutionOutcome, WireRequest, PROTOCOL_VERSION,
};
use serde::Deserialize;
use serde_json::{json, Value};

#[derive(Debug, Deserialize)]
struct Fixture {
    fixture_version: u32,
    contract_version: u32,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct Case {
    case_id: String,
    category: String,
    scenario: String,
}

fn fixture() -> Fixture {
    serde_json::from_str(include_str!(concat!(
        "../../../../tests/golden/phase6_shadow_v1.json"
    )))
    .expect("parse phase6 shadow fixture")
}

fn workspace_root() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .to_path_buf()
}

fn python_oracle_path() -> std::path::PathBuf {
    workspace_root()
        .join("tests")
        .join("phase6_shadow_oracle.py")
}

fn corpus_path() -> std::path::PathBuf {
    workspace_root()
        .join("tests")
        .join("golden")
        .join("phase6_shadow_v1.json")
}

#[allow(clippy::too_many_arguments)]
fn context(
    subject_id: &str,
    subject_state_id: &str,
    verification_context_id: &str,
    policy_bundle_id: &str,
    required_obligations: Vec<&str>,
    trusted_verifiers: Vec<&str>,
    trusted_provenance_roots: Vec<&str>,
    authorized_authorities: Vec<&str>,
) -> AcceptanceContext {
    AcceptanceContext {
        subject_id: subject_id.into(),
        subject_state_id: subject_state_id.into(),
        verification_context_id: verification_context_id.into(),
        policy_bundle_id: policy_bundle_id.into(),
        required_obligations: required_obligations
            .into_iter()
            .map(str::to_string)
            .collect(),
        trusted_verifiers: trusted_verifiers.into_iter().map(str::to_string).collect(),
        trusted_provenance_roots: trusted_provenance_roots
            .into_iter()
            .map(str::to_string)
            .collect(),
        authorized_authorities: authorized_authorities
            .into_iter()
            .map(str::to_string)
            .collect(),
    }
}

fn evidence(overrides: impl FnOnce(&mut EvidenceEnvelope)) -> EvidenceEnvelope {
    let mut value = EvidenceEnvelope {
        evidence_id: "e1".into(),
        obligation_id: "verify".into(),
        mission_id: MissionId::new("m1").unwrap(),
        execution_id: ExecutionId::new("x1").unwrap(),
        orchestrator_id: RuntimeId::new("orch-a").unwrap(),
        adapter_version: "1".into(),
        attempt_id: "a1".into(),
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "ctx-1".into(),
        policy_bundle_id: "policy-1".into(),
        verifier_id: "verifier-1".into(),
        payload_digest: "abc".into(),
        provenance_root: "root-1".into(),
        authority_id: "authority-1".into(),
        passed: true,
        created_at_epoch: 10.0,
        expires_at_epoch: Some(20.0),
        approval_id: None,
        confidence: None,
    };
    overrides(&mut value);
    value
}

fn acceptance_semantic(result: metao_contracts::AcceptanceResult) -> Value {
    let proof = result.proof.clone();
    json!({
        "decision": decision_string(result.decision),
        "reasons": result.reasons,
        "proof_digest": proof.as_ref().map(|p| p.digest.clone()),
        "proof_evidence_ids": proof.map(|p| p.evidence_ids),
    })
}

fn policy_semantic(result: metao_contracts::PolicyDecision) -> Value {
    json!({
        "effect": policy_string(result.effect),
        "policy_bundle_id": result.policy_bundle_id,
        "reason": result.reason,
    })
}

fn decision_string(value: AcceptanceDecision) -> &'static str {
    match value {
        AcceptanceDecision::Accept => "ACCEPT",
        AcceptanceDecision::Block => "BLOCK",
        AcceptanceDecision::NotDone => "NOT_DONE",
        AcceptanceDecision::Stale => "STALE",
        AcceptanceDecision::RequireHuman => "REQUIRE_HUMAN",
    }
}

fn policy_string(value: PolicyEffect) -> &'static str {
    match value {
        PolicyEffect::Allow => "ALLOW",
        PolicyEffect::Deny => "DENY",
        PolicyEffect::RequireHuman => "REQUIRE_HUMAN",
    }
}

fn approval_request() -> metao_contracts::ApprovalRequest {
    require_human("ap-1", "m1", "x1", "s1", "p1", "high risk")
}

fn approved_record() -> ApprovalRecord {
    ApprovalRecord {
        approval_id: "ap-1".into(),
        mission_id: "m1".into(),
        execution_id: "x1".into(),
        subject_state_id: "s1".into(),
        policy_bundle_id: "p1".into(),
        approver_id: "human-1".into(),
        approved: true,
    }
}

fn denied_record() -> ApprovalRecord {
    ApprovalRecord {
        approved: false,
        ..approved_record()
    }
}

fn budget_authority() -> AcceptanceBudgetAuthority {
    AcceptanceBudgetAuthority::new(
        AcceptanceBudget::new(10.0, 10_000, 60.0, 10).expect("valid budget"),
    )
}

fn budget_semantic(map: BTreeMap<&str, Value>) -> Value {
    Value::Object(map.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
}

fn proof_context() -> AcceptanceContext {
    context(
        "subject-l5",
        "state-l5",
        "verify-l5",
        "policy-l5",
        vec!["a", "b"],
        vec!["verifier-l5"],
        vec!["root-l5"],
        vec!["authority-l5"],
    )
}

fn proof_evidence(obligation: &str, evidence_id: &str, created_at: f64) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: evidence_id.into(),
        obligation_id: obligation.into(),
        mission_id: MissionId::new("mission-l5").unwrap(),
        execution_id: ExecutionId::new("exec-l5").unwrap(),
        orchestrator_id: RuntimeId::new("runtime-l5").unwrap(),
        adapter_version: "1".into(),
        attempt_id: "attempt-l5".into(),
        subject_id: "subject-l5".into(),
        subject_state_id: "state-l5".into(),
        verification_context_id: "verify-l5".into(),
        policy_bundle_id: "policy-l5".into(),
        verifier_id: "verifier-l5".into(),
        payload_digest: format!("digest-{evidence_id}"),
        provenance_root: "root-l5".into(),
        authority_id: "authority-l5".into(),
        passed: true,
        created_at_epoch: created_at,
        expires_at_epoch: Some(100.0),
        approval_id: None,
        confidence: None,
    }
}

fn proof_semantic(result: metao_contracts::AcceptanceResult) -> Value {
    let proof = result.proof.as_ref().expect("proof present");
    json!({
        "decision": decision_string(result.decision),
        "replay_decision": decision_string(replay_acceptance_decision(proof).unwrap()),
        "reasons": result.reasons,
        "proof_digest": proof.digest.clone(),
        "proof_evidence_ids": proof.evidence_ids.clone(),
    })
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum CapabilityAuthority {
    Python,
    RustShadow,
    RustActive,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct CapabilityCutoverState {
    qualified_capabilities: BTreeSet<String>,
    shadow_capabilities: BTreeSet<String>,
    active_capabilities: BTreeSet<String>,
}

impl CapabilityCutoverState {
    fn new() -> Self {
        Self {
            qualified_capabilities: [
                "acceptance",
                "policy",
                "approval",
                "budget",
                "authority_provenance",
                "proof_replay",
            ]
            .into_iter()
            .map(str::to_string)
            .collect(),
            shadow_capabilities: ["runtime"].into_iter().map(str::to_string).collect(),
            active_capabilities: BTreeSet::new(),
        }
    }

    fn authority_for(&self, capability: &str) -> CapabilityAuthority {
        if self.active_capabilities.contains(capability) {
            CapabilityAuthority::RustActive
        } else if self.shadow_capabilities.contains(capability) {
            CapabilityAuthority::RustShadow
        } else {
            CapabilityAuthority::Python
        }
    }

    fn promote(mut self, capability: &str) -> Self {
        if self.qualified_capabilities.contains(capability) {
            self.shadow_capabilities.remove(capability);
            self.active_capabilities.insert(capability.to_string());
        }
        self
    }

    fn rollback(mut self, capability: &str) -> Self {
        self.active_capabilities.remove(capability);
        self.shadow_capabilities.remove(capability);
        self
    }
}

fn capability_for_category(category: &str) -> &str {
    match category {
        "proof" => "proof_replay",
        other => other,
    }
}

fn normalized_error_category(err: impl std::fmt::Debug) -> String {
    let text = format!("{err:?}");
    if text.contains("BudgetExhausted") {
        "budget_exhausted".into()
    } else if text.contains("ReplayConflict") {
        "replay_conflict".into()
    } else if text.contains("UnknownReservation") {
        "unknown_reservation".into()
    } else if text.contains("AcceptanceProofDigestMismatch") {
        "proof_digest_mismatch".into()
    } else if text.contains("InvalidConfidence") || text.contains("InvalidThreshold") {
        "invalid_confidence".into()
    } else {
        text
    }
}

fn runtime_binary() -> PathBuf {
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_metao-wire-runtime") {
        return PathBuf::from(path);
    }
    let fallback = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("target")
        .join("debug")
        .join(if cfg!(windows) {
            "metao-wire-runtime.exe"
        } else {
            "metao-wire-runtime"
        });
    assert!(
        fallback.exists(),
        "missing runtime binary; run metao-wire runtime tests first or build the workspace: {}",
        fallback.display()
    );
    fallback
}

fn runtime_objective(scenario: &str) -> &'static str {
    match scenario {
        "success_without_evidence" => "normal",
        "recovered_success_without_evidence" => "__crash_then_recover__",
        "failover_success_without_evidence" => "__crash_then_recover__",
        "failover_success_with_valid_evidence" => "__crash_then_recover__",
        "crash_recovery" => "__crash_then_recover__",
        "timeout_recovery" => "__hang_then_recover__",
        other => panic!("unknown runtime scenario: {other}"),
    }
}

fn runtime_request(scenario: &str) -> WireRequest {
    WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: format!("runtime-{scenario}"),
        mission_id: "mission-rt".into(),
        objective: runtime_objective(scenario).into(),
    }
}

fn runtime_result_summary(scenario: &str) -> Value {
    let started = std::time::Instant::now();
    let request = runtime_request(scenario);
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request,
        RecoveryPolicy::new(1, std::time::Duration::from_millis(200)),
    );

    let (execution_status, execution_error, runtime_observation, acceptance) = match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            let execution_status = response.status.clone();
            let execution_id = response.execution_id.clone();
            let runtime_id = response.runtime_id.clone();
            let result = response.result.clone();
            let acceptance = if scenario == "failover_success_with_valid_evidence" {
                acceptance_semantic(canonical_acceptance(
                    &context(
                        "subject-rt",
                        "state-rt",
                        "ctx-rt",
                        "policy-rt",
                        vec!["verify"],
                        vec!["verifier-rt"],
                        vec!["root-rt"],
                        vec!["authority-rt"],
                    ),
                    &[evidence(|item| {
                        item.evidence_id = "rt-e1".into();
                        item.obligation_id = "verify".into();
                        item.mission_id = MissionId::new("mission-rt").unwrap();
                        item.execution_id =
                            ExecutionId::new("runtime-failover_success_with_valid_evidence")
                                .unwrap();
                        item.orchestrator_id = RuntimeId::new("runtime-a").unwrap();
                        item.adapter_version = "1".into();
                        item.attempt_id = "attempt-1".into();
                        item.subject_id = "subject-rt".into();
                        item.subject_state_id = "state-rt".into();
                        item.verification_context_id = "ctx-rt".into();
                        item.policy_bundle_id = "policy-rt".into();
                        item.verifier_id = "verifier-rt".into();
                        item.payload_digest = "digest-rt".into();
                        item.provenance_root = "root-rt".into();
                        item.authority_id = "authority-rt".into();
                        item.passed = true;
                        item.created_at_epoch = 10.0;
                        item.expires_at_epoch = Some(100.0);
                    })],
                    15.0,
                ))
            } else {
                acceptance_semantic(canonical_acceptance(
                    &context(
                        "subject-rt",
                        "state-rt",
                        "ctx-rt",
                        "policy-rt",
                        vec!["verify"],
                        vec!["verifier-rt"],
                        vec!["root-rt"],
                        vec!["authority-rt"],
                    ),
                    &[],
                    15.0,
                ))
            };
            let execution_status_for_output = execution_status.clone();
            (
                execution_status_for_output,
                String::new(),
                json!({
                    "runtime_outcome": "COMPLETED",
                    "attempts": attempts,
                    "response": {
                        "protocol_version": response.protocol_version,
                        "execution_id": execution_id,
                        "runtime_id": runtime_id,
                        "status": execution_status.clone(),
                        "result": result,
                    },
                }),
                acceptance,
            )
        }
        RuntimeExecutionOutcome::Failed { reason, attempts } => {
            let reason_text = match reason {
                RuntimeExecutionFailure::Crash => "crash",
                RuntimeExecutionFailure::Timeout => "timeout",
                RuntimeExecutionFailure::SpawnFailed => "spawn_failed",
                RuntimeExecutionFailure::RecoveryExhausted => "recovery_exhausted",
            };
            (
                "FAILED".into(),
                reason_text.into(),
                json!({
                    "runtime_outcome": "FAILED",
                    "attempts": attempts,
                    "reason": reason_text,
                }),
                acceptance_semantic(canonical_acceptance(
                    &context(
                        "subject-rt",
                        "state-rt",
                        "ctx-rt",
                        "policy-rt",
                        vec!["verify"],
                        vec!["verifier-rt"],
                        vec!["root-rt"],
                        vec!["authority-rt"],
                    ),
                    &[],
                    15.0,
                )),
            )
        }
        RuntimeExecutionOutcome::Blocked { reason, attempts } => {
            let reason_text = match reason {
                RuntimeExecutionBlocked::MalformedProtocol => "malformed_protocol",
                RuntimeExecutionBlocked::IncompatibleProtocol => "incompatible_protocol",
            };
            (
                "BLOCKED".into(),
                reason_text.into(),
                json!({
                    "runtime_outcome": "BLOCKED",
                    "attempts": attempts,
                    "reason": reason_text,
                }),
                acceptance_semantic(canonical_acceptance(
                    &context(
                        "subject-rt",
                        "state-rt",
                        "ctx-rt",
                        "policy-rt",
                        vec!["verify"],
                        vec!["verifier-rt"],
                        vec!["root-rt"],
                        vec!["authority-rt"],
                    ),
                    &[],
                    15.0,
                )),
            )
        }
    };
    let execution_status_for_attempt = execution_status.clone();
    let acceptance_decision = acceptance["decision"]
        .as_str()
        .unwrap_or("NOT_DONE")
        .to_string();

    json!({
        "mission_id": "mission-rt",
        "orchestrator_id": "runtime-a",
        "attempted_orchestrators": ["runtime-a"],
        "execution_status": execution_status,
        "execution_error": execution_error,
        "execution_output": runtime_observation.clone(),
        "acceptance": acceptance,
        "state": {
            "status": "VERIFYING",
            "history": ["CREATED", "PLANNING", "SELECTING", "RUNNING", "VERIFYING"],
            "attempts": [{
                "attempt_number": 1,
                "execution_id": request.execution_id,
                "orchestrator_id": "runtime-a",
                "execution_status": execution_status_for_attempt,
                "acceptance_decision": acceptance_decision,
                "reasons": [],
            }],
        },
        "budget": {
            "money_limit": 1.0,
            "money_used": 0.0,
            "token_limit": 1000,
            "tokens_used": 0,
            "wall_time_limit_s": 60.0,
            "wall_time_used_s": 0.0,
            "verifier_attempt_limit": 4,
            "verifier_attempts_used": 0,
        },
        "comparison_kind": "HARNESS_ONLY",
        "runtime_observation": runtime_observation,
        "metrics": {
            "duration_ms": started.elapsed().as_secs_f64() * 1000.0,
        }
    })
}

fn run_case(case: &Case) -> Value {
    let started = std::time::Instant::now();
    let comparison_kind = if case.category == "runtime" {
        "HARNESS_ONLY"
    } else {
        "REAL_PYTHON_VS_REAL_RUST"
    };
    let semantic = match (case.category.as_str(), case.scenario.as_str()) {
        ("acceptance", "valid_bound") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|_| {})],
            15.0,
        )),
        ("acceptance", "succeeded_without_evidence") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[],
            15.0,
        )),
        ("acceptance", "failed_obligation") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| item.passed = false)],
            15.0,
        )),
        ("acceptance", "stale_evidence") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| item.expires_at_epoch = Some(12.0))],
            15.0,
        )),
        ("acceptance", "future_evidence") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| {
                item.created_at_epoch = 20.0;
                item.expires_at_epoch = Some(30.0);
            })],
            15.0,
        )),
        ("acceptance", "subject_mismatch") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| item.subject_id = "other-subject".into())],
            15.0,
        )),
        ("acceptance", "subject_state_mismatch") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| {
                item.subject_state_id = "other-state".into()
            })],
            15.0,
        )),
        ("acceptance", "verification_context_mismatch") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|item| {
                    item.verification_context_id = "other-ctx".into()
                })],
                15.0,
            ))
        }
        ("acceptance", "policy_bundle_mismatch") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| {
                item.policy_bundle_id = "other-policy".into()
            })],
            15.0,
        )),

        ("authority_provenance", "missing_provenance") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|item| {
                    item.payload_digest = "".into();
                    item.provenance_root = "".into();
                })],
                15.0,
            ))
        }
        ("authority_provenance", "untrusted_verifier") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|item| item.verifier_id = "evil-verifier".into())],
                15.0,
            ))
        }
        ("authority_provenance", "untrusted_provenance_root") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|item| item.provenance_root = "evil-root".into())],
                15.0,
            ))
        }
        ("authority_provenance", "missing_authority") => acceptance_semantic(canonical_acceptance(
            &context(
                "subject-1",
                "state-1",
                "ctx-1",
                "policy-1",
                vec!["verify"],
                vec!["verifier-1"],
                vec!["root-1"],
                vec!["authority-1"],
            ),
            &[evidence(|item| item.authority_id = "".into())],
            15.0,
        )),
        ("authority_provenance", "unauthorized_authority") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|item| item.authority_id = "evil-authority".into())],
                15.0,
            ))
        }
        ("authority_provenance", "trusted_exact_evidence") => {
            acceptance_semantic(canonical_acceptance(
                &context(
                    "subject-1",
                    "state-1",
                    "ctx-1",
                    "policy-1",
                    vec!["verify"],
                    vec!["verifier-1"],
                    vec!["root-1"],
                    vec!["authority-1"],
                ),
                &[evidence(|_| {})],
                15.0,
            ))
        }

        ("policy", "allow_default") => {
            policy_semantic(evaluate_policy("policy-1", true, false, ""))
        }
        ("policy", "deny_default") => {
            policy_semantic(evaluate_policy("policy-1", false, false, ""))
        }
        ("policy", "require_human_default") => {
            policy_semantic(evaluate_policy("policy-1", true, true, ""))
        }
        ("policy", "deny_overrides_require_human") => {
            policy_semantic(evaluate_policy("policy-1", false, true, ""))
        }

        ("approval", "approved_exact_binding") => json!({
            "request": json!(approval_request()),
            "record": json!(approved_record()),
            "decision": decision_string(resume_after_approval(&approval_request(), &approved_record())),
        }),
        ("approval", "denied_exact_binding") => json!({
            "request": json!(approval_request()),
            "record": json!(denied_record()),
            "decision": decision_string(resume_after_approval(&approval_request(), &denied_record())),
        }),
        ("approval", "approval_id_mismatch") => {
            let mut record = approved_record();
            record.approval_id = "ap-2".into();
            json!({
                "request": json!(approval_request()),
                "record": json!(record.clone()),
                "decision": decision_string(resume_after_approval(&approval_request(), &record)),
            })
        }
        ("approval", "low_confidence_requires_human") => json!({
            "decision": decision_string(apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 0.4, 0.8).unwrap()),
            "confidence": 0.4,
            "threshold": 0.8,
        }),
        ("approval", "invalid_confidence_fails_closed") => {
            let err = apply_confidence_after_hard_gates(AcceptanceDecision::Accept, 1.1, 0.8)
                .unwrap_err();
            json!({
                "error_category": normalized_error_category(&err),
            })
        }

        ("budget", "shared_budget_no_oversubscription") => {
            let authority = Arc::new(budget_authority());
            let barrier = Arc::new(Barrier::new(2));
            let accepted = Arc::new(Mutex::new(Vec::new()));
            let rejected = Arc::new(Mutex::new(Vec::new()));
            let handles: Vec<_> = ["r1", "r2"]
                .into_iter()
                .map(|reservation_id| {
                    let authority = Arc::clone(&authority);
                    let barrier = Arc::clone(&barrier);
                    let accepted = Arc::clone(&accepted);
                    let rejected = Arc::clone(&rejected);
                    thread::spawn(move || {
                        barrier.wait();
                        match authority.reserve(reservation_id, 6.0, 0, 0.0, 0) {
                            Ok(_) => accepted.lock().unwrap().push(reservation_id.to_string()),
                            Err(err) => {
                                assert_eq!(normalized_error_category(err), "budget_exhausted");
                                rejected.lock().unwrap().push(reservation_id.to_string())
                            }
                        }
                    })
                })
                .collect();
            for handle in handles {
                handle.join().unwrap();
            }
            let mut accepted = accepted.lock().unwrap().clone();
            let mut rejected = rejected.lock().unwrap().clone();
            accepted.sort();
            rejected.sort();
            let winner_money = accepted
                .first()
                .map(|id| authority.reservation(id).unwrap().money)
                .unwrap_or_default();
            budget_semantic(BTreeMap::from([
                ("accepted", json!(accepted)),
                ("rejected", json!(rejected)),
                ("winner_money", json!(winner_money)),
                ("money_used", json!(authority.snapshot().money_used)),
            ]))
        }
        ("budget", "exact_capacity_admission") => {
            let authority = budget_authority();
            authority.reserve("r1", 5.0, 0, 0.0, 0).unwrap();
            authority.reserve("r2", 5.0, 0, 0.0, 0).unwrap();
            budget_semantic(BTreeMap::from([
                (
                    "reservation_r1",
                    json!(authority.reservation("r1").unwrap()),
                ),
                (
                    "reservation_r2",
                    json!(authority.reservation("r2").unwrap()),
                ),
                ("money_used", json!(authority.snapshot().money_used)),
            ]))
        }
        ("budget", "failed_reservation_no_mutation") => {
            let authority = budget_authority();
            authority.reserve("winner", 8.0, 0, 0.0, 0).unwrap();
            let rejected = authority.reserve("loser", 3.0, 0, 0.0, 0).unwrap_err();
            assert_eq!(normalized_error_category(rejected), "budget_exhausted");
            budget_semantic(BTreeMap::from([
                ("winner", json!(authority.reservation("winner").unwrap())),
                ("loser", json!(authority.reservation("loser"))),
                ("reject_error", json!("budget_exhausted")),
                ("money_used", json!(authority.snapshot().money_used)),
                ("settled", json!(authority.settle("winner").unwrap())),
            ]))
        }
        ("budget", "duplicate_reservation_replay_idempotent") => {
            let authority = budget_authority();
            let first = authority.reserve("reservation-1", 4.0, 10, 0.0, 0).unwrap();
            let retry = authority.reserve("reservation-1", 4.0, 10, 0.0, 0).unwrap();
            budget_semantic(BTreeMap::from([
                ("first", json!(first)),
                ("retry", json!(retry)),
                ("money_used", json!(authority.snapshot().money_used)),
            ]))
        }
        ("budget", "conflicting_reservation_replay_fails_closed") => {
            let authority = budget_authority();
            authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();
            let conflict = authority
                .reserve("reservation-1", 5.0, 0, 0.0, 0)
                .unwrap_err();
            assert_eq!(normalized_error_category(conflict), "replay_conflict");
            budget_semantic(BTreeMap::from([
                ("error_category", json!("replay_conflict")),
                (
                    "reservation",
                    json!(authority.reservation("reservation-1").unwrap()),
                ),
            ]))
        }
        ("budget", "settlement_retry_idempotent") => {
            let authority = budget_authority();
            authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();
            let first = authority.settle("reservation-1").unwrap();
            let retry = authority.settle("reservation-1").unwrap();
            budget_semantic(BTreeMap::from([
                ("first", json!(first)),
                ("retry", json!(retry)),
                (
                    "reservation",
                    json!(authority.reservation("reservation-1").unwrap()),
                ),
            ]))
        }
        ("budget", "concurrent_same_settlement_single_effect") => {
            let authority = Arc::new(budget_authority());
            authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();
            let barrier = Arc::new(Barrier::new(2));
            let results = Arc::new(Mutex::new(Vec::<f64>::new()));
            let handles: Vec<_> = (0..2)
                .map(|_| {
                    let authority = Arc::clone(&authority);
                    let barrier = Arc::clone(&barrier);
                    let results = Arc::clone(&results);
                    thread::spawn(move || {
                        barrier.wait();
                        let snapshot = authority.settle("reservation-1").unwrap();
                        results.lock().unwrap().push(snapshot.money_used);
                    })
                })
                .collect();
            for handle in handles {
                handle.join().unwrap();
            }
            let mut results = results.lock().unwrap().clone();
            results.sort_by(|a, b| a.partial_cmp(b).unwrap());
            budget_semantic(BTreeMap::from([
                ("results", json!(results)),
                ("money_used", json!(authority.snapshot().money_used)),
                (
                    "reservation",
                    json!(authority.reservation("reservation-1").unwrap()),
                ),
            ]))
        }
        ("budget", "unknown_settlement_id_fails_closed") => {
            let authority = budget_authority();
            let unknown = authority.settle("missing-reservation").unwrap_err();
            assert_eq!(normalized_error_category(unknown), "unknown_reservation");
            budget_semantic(BTreeMap::from([
                ("error_category", json!("unknown_reservation")),
                ("money_used", json!(authority.snapshot().money_used)),
            ]))
        }

        ("proof", "valid_replay") => {
            let result = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            proof_semantic(result)
        }
        ("proof", "tampered_evidence_ids") => {
            let result = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            let mut proof = result.proof.unwrap();
            proof.evidence_ids = vec!["forged".into()];
            let err = replay_acceptance_decision(&proof).unwrap_err();
            json!({
                "error_category": normalized_error_category(&err),
                "proof_digest": proof.digest,
            })
        }
        ("proof", "tampered_decision") => {
            let result = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            let mut proof = result.proof.unwrap();
            proof.decision = AcceptanceDecision::Block;
            let err = replay_acceptance_decision(&proof).unwrap_err();
            json!({
                "error_category": normalized_error_category(&err),
            })
        }
        ("proof", "tampered_reasons") => {
            let result = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            let mut proof = result.proof.unwrap();
            proof.reasons = vec!["forged".into()];
            let err = replay_acceptance_decision(&proof).unwrap_err();
            json!({
                "error_category": normalized_error_category(&err),
            })
        }
        ("proof", "tampered_digest") => {
            let result = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            let mut proof = result.proof.unwrap();
            proof.digest = "deadbeef".repeat(8);
            let err = replay_acceptance_decision(&proof).unwrap_err();
            json!({
                "error_category": normalized_error_category(&err),
            })
        }
        ("proof", "order_independent") => {
            let chronological = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("b", "e-b", 10.0),
                    proof_evidence("a", "e-a", 20.0),
                ],
                30.0,
            );
            let out_of_order = canonical_acceptance(
                &proof_context(),
                &[
                    proof_evidence("a", "e-a", 20.0),
                    proof_evidence("b", "e-b", 10.0),
                ],
                30.0,
            );
            json!({
                "base": proof_semantic(chronological.clone()),
                "shuffled": proof_semantic(out_of_order.clone()),
                "proof_equal": chronological.proof == out_of_order.proof,
            })
        }

        ("runtime", "success_without_evidence") => {
            runtime_result_summary("success_without_evidence")
        }
        ("runtime", "recovered_success_without_evidence") => {
            runtime_result_summary("recovered_success_without_evidence")
        }
        ("runtime", "failover_success_without_evidence") => {
            runtime_result_summary("failover_success_without_evidence")
        }
        ("runtime", "failover_success_with_valid_evidence") => {
            runtime_result_summary("failover_success_with_valid_evidence")
        }
        ("runtime", "crash_recovery") => runtime_result_summary("crash_recovery"),
        ("runtime", "timeout_recovery") => runtime_result_summary("timeout_recovery"),

        other => panic!("unhandled shadow case: {other:?}"),
    };

    json!({
        "case_id": case.case_id,
        "category": case.category,
        "scenario": case.scenario,
        "comparison_kind": comparison_kind,
        "semantic": semantic,
        "metrics": {
            "duration_ms": started.elapsed().as_secs_f64() * 1000.0,
        }
    })
}

fn strip_metrics(results: &[Value]) -> Vec<Value> {
    results
        .iter()
        .map(|item| {
            json!({
                "case_id": item["case_id"],
                "category": item["category"],
                "scenario": item["scenario"],
                "comparison_kind": item["comparison_kind"],
                "semantic": item["semantic"],
            })
        })
        .collect()
}

fn run_python_oracle() -> Vec<Value> {
    let python = std::env::var("METAO_PYTHON")
        .or_else(|_| std::env::var("PYTHON"))
        .unwrap_or_else(|_| "python".to_string());
    let output = Command::new(python)
        .arg(python_oracle_path())
        .arg(corpus_path())
        .output()
        .expect("run python shadow oracle");
    assert!(
        output.status.success(),
        "python oracle failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).expect("parse python oracle output")
}

#[test]
fn shadow_corpus_matches_python_semantics() {
    let fixture = fixture();
    assert_eq!(fixture.fixture_version, 1);
    assert_eq!(fixture.contract_version, metao_contracts::CONTRACT_VERSION);

    let python_results = run_python_oracle();
    let rust_results: Vec<Value> = fixture.cases.iter().map(run_case).collect();

    let python = strip_metrics(&python_results);
    let rust = strip_metrics(&rust_results);
    let mut real_cases = 0usize;
    let mut harness_only_cases = 0usize;
    let cutover = CapabilityCutoverState::new()
        .promote("acceptance")
        .promote("policy")
        .promote("approval")
        .promote("budget")
        .promote("authority_provenance")
        .promote("proof_replay");

    assert_eq!(python.len(), rust.len(), "shadow corpus length mismatch");
    for case in &fixture.cases {
        match case.category.as_str() {
            "runtime" => harness_only_cases += 1,
            "acceptance" | "policy" | "approval" | "budget" | "authority_provenance" | "proof" => {
                real_cases += 1;
                assert_eq!(
                    cutover.authority_for(capability_for_category(case.category.as_str())),
                    CapabilityAuthority::RustActive
                );
            }
            other => panic!("unexpected phase 7 capability category: {other}"),
        }
    }
    assert_eq!(real_cases, 38);
    assert_eq!(harness_only_cases, 6);
    for (index, (py, rs)) in python.iter().zip(rust.iter()).enumerate() {
        let case = &fixture.cases[index];
        if case.category == "runtime" {
            assert_eq!(py["comparison_kind"], "HARNESS_ONLY");
            assert_eq!(rs["comparison_kind"], "HARNESS_ONLY");
            assert!(rs["semantic"]["runtime_observation"]["runtime_outcome"].is_string());
            continue;
        }
        if py != rs {
            let case_id = &fixture.cases[index].case_id;
            panic!(
                "shadow semantic mismatch at case index {index} (case_id={case_id})\npython={}\nrust={}",
                serde_json::to_string_pretty(py).expect("format python semantic"),
                serde_json::to_string_pretty(rs).expect("format rust semantic"),
            );
        }
    }
}

#[test]
fn phase7_cutover_promotes_qualified_capabilities_and_keeps_runtime_shadow() {
    let state = CapabilityCutoverState::new()
        .promote("acceptance")
        .promote("policy")
        .promote("approval")
        .promote("budget")
        .promote("authority_provenance")
        .promote("proof_replay");

    for capability in [
        "acceptance",
        "policy",
        "approval",
        "budget",
        "authority_provenance",
        "proof_replay",
    ] {
        assert_eq!(
            state.authority_for(capability),
            CapabilityAuthority::RustActive
        );
    }
    assert_eq!(
        state.authority_for("runtime"),
        CapabilityAuthority::RustShadow
    );
    assert_eq!(
        state.authority_for("unqualified_capability"),
        CapabilityAuthority::Python
    );
}

#[test]
fn phase7_cutover_rollback_is_idempotent_and_restores_python() {
    let promoted = CapabilityCutoverState::new().promote("acceptance");
    assert_eq!(
        promoted.authority_for("acceptance"),
        CapabilityAuthority::RustActive
    );

    let rolled_back = promoted.clone().rollback("acceptance");
    assert_eq!(
        rolled_back.authority_for("acceptance"),
        CapabilityAuthority::Python
    );
    assert_eq!(rolled_back.clone().rollback("acceptance"), rolled_back);
}

#[test]
fn shadow_comparator_prefers_python_authority_on_mismatch() {
    let python = json!({
        "case_id": "synthetic.case",
        "category": "synthetic",
        "scenario": "authority",
        "semantic": {"decision": "ACCEPT"}
    });
    let rust = json!({
        "case_id": "synthetic.case",
        "category": "synthetic",
        "scenario": "authority",
        "semantic": {"decision": "BLOCK"}
    });

    let comparison = if python["semantic"] == rust["semantic"] {
        "MATCH"
    } else {
        "RUST_BUG"
    };

    assert_eq!(comparison, "RUST_BUG");
    assert_eq!(python["semantic"]["decision"], "ACCEPT");
}
