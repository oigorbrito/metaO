use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

use metao_contracts::execution_governance::{
    evaluate_pre_runtime_gate, ExecutionBudget, ExecutionGateDecision, ExecutionObservedUsage,
    ExecutionPolicyEffect, ExecutionRiskDecision, ExecutionUsage, ExecutionUsageEvidenceBasis,
};
use metao_contracts::execution_stage_evidence::{
    project_execution_stages, ExecutionStageEvidence, ExecutionStageEvidenceBasis,
    ExecutionStageStatus,
};
use metao_contracts::failure_causality::{
    evaluate_retry_eligibility, FactualExecutionOutcome, FailureCausalityFacts, FailureClass,
    FailureClassificationBasis, RecoveryStatus, RetryEligibility,
};
use metao_contracts::runtime_health::{
    derive_runtime_health, RuntimeHealthEvidenceBasis, RuntimeHealthObservation,
    RuntimeHealthPolicy, RuntimeHealthState,
};
use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, EvidenceEnvelope, ExecutionId, MissionId, RuntimeId,
};
use metao_kernel::canonical_acceptance;
use serde::Serialize;
use serde_json::{json, Value};

fn unique_name(prefix: &str) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock should be monotonic enough")
        .as_nanos();
    format!("{prefix}-{nanos}")
}

fn service_exe() -> PathBuf {
    PathBuf::from(
        env::var("CARGO_BIN_EXE_metao-testkit-service")
            .expect("service binary must be built by cargo test"),
    )
}

fn spawn_service(mode: &str, state_path: &PathBuf) -> (Child, ChildStdin, BufReader<ChildStdout>) {
    let mut child = Command::new(service_exe())
        .arg(mode)
        .arg(state_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to start testkit service");
    let stdin = child.stdin.take().expect("service stdin");
    let stdout = child.stdout.take().expect("service stdout");
    (child, stdin, BufReader::new(stdout))
}

fn send_json(stdin: &mut ChildStdin, reader: &mut BufReader<ChildStdout>, value: Value) -> Value {
    writeln!(stdin, "{value}").expect("service write");
    stdin.flush().expect("service flush");
    let mut line = String::new();
    reader.read_line(&mut line).expect("service read");
    serde_json::from_str(line.trim()).expect("service response")
}

fn send_json_expect_lost_ack(
    mut child: Child,
    mut stdin: ChildStdin,
    mut reader: BufReader<ChildStdout>,
    value: Value,
) {
    writeln!(stdin, "{value}").expect("service write");
    stdin.flush().expect("service flush");
    drop(stdin);
    let mut line = String::new();
    let read = reader.read_line(&mut line).expect("service read");
    assert_eq!(read, 0, "lost-ack service must close without response");
    assert!(child.wait().expect("wait lost-ack service").success());
}

fn budget() -> ExecutionBudget {
    ExecutionBudget {
        money_limit: 10.0,
        token_limit: 1_000,
        wall_time_limit_s: 100.0,
        attempt_limit: 3,
        money_used: 0.0,
        tokens_used: 0,
        wall_time_used_s: 0.0,
        attempts_used: 0,
    }
}

fn usage(attempts: u64) -> ExecutionUsage {
    ExecutionUsage {
        money: 1.0,
        tokens: 10,
        wall_time_s: 1.0,
        attempts,
    }
}

fn mission_id() -> MissionId {
    MissionId::new("closure-marketplace-mission").unwrap()
}

fn execution_id(value: &str) -> ExecutionId {
    ExecutionId::new(value).unwrap()
}

fn runtime_id(value: &str) -> RuntimeId {
    RuntimeId::new(value).unwrap()
}

fn acceptance_context(_runtime_id: &RuntimeId, provenance_root: &str) -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "marketplace-project".into(),
        subject_state_id: "state-generation-2".into(),
        verification_context_id: "closure-verification".into(),
        policy_bundle_id: "policy-allow-budget-v1".into(),
        required_obligations: vec!["system_lineage".into()],
        trusted_verifiers: vec!["independent-closure-verifier".into()],
        trusted_provenance_roots: vec![provenance_root.into()],
        authorized_authorities: vec!["metao-closure-authority".into()],
    }
}

fn evidence(
    runtime_id: RuntimeId,
    execution_id: ExecutionId,
    provenance_root: &str,
) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: format!("{}:system-lineage", execution_id.as_str()),
        obligation_id: "system_lineage".into(),
        mission_id: mission_id(),
        execution_id,
        orchestrator_id: runtime_id,
        adapter_version: "local-test-adapter-1".into(),
        attempt_id: "attempt-2".into(),
        subject_id: "marketplace-project".into(),
        subject_state_id: "state-generation-2".into(),
        verification_context_id: "closure-verification".into(),
        policy_bundle_id: "policy-allow-budget-v1".into(),
        verifier_id: "independent-closure-verifier".into(),
        payload_digest: "sha256:closure-system-proof".into(),
        provenance_root: provenance_root.into(),
        authority_id: "metao-closure-authority".into(),
        passed: true,
        created_at_epoch: 20.0,
        expires_at_epoch: Some(40.0),
        approval_id: None,
        confidence: Some(1.0),
    }
}

#[derive(Serialize)]
struct GateEvidenceRecord {
    schema_version: &'static str,
    record_id: &'static str,
    repository: &'static str,
    gate_id: &'static str,
    gate_level: &'static str,
    runtime_identities: Vec<&'static str>,
    mission_id: String,
    execution_lineage: Vec<&'static str>,
    result: &'static str,
    substrate: Vec<&'static str>,
    external_systems_real: bool,
    claim_boundary: &'static str,
}

#[test]
fn composed_system_proof_reconciles_failover_fencing_effects_and_acceptance() {
    let root = env::temp_dir().join(unique_name("metao-composed-system"));
    fs::create_dir_all(&root).unwrap();
    let effect_state = root.join("effect-state.json");
    let fence_state = root.join("fence-state.json");

    let deny = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Deny,
        ExecutionRiskDecision::Allow,
        &budget(),
        &usage(1),
        true,
    );
    assert_eq!(deny.decision, ExecutionGateDecision::Block);

    let risk_stop = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Stop,
        &budget(),
        &usage(1),
        true,
    );
    assert_eq!(risk_stop.decision, ExecutionGateDecision::Block);

    let exhausted = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &ExecutionBudget {
            attempt_limit: 0,
            ..budget()
        },
        &usage(1),
        true,
    );
    assert_eq!(exhausted.decision, ExecutionGateDecision::Block);

    let eligible = evaluate_pre_runtime_gate(
        ExecutionPolicyEffect::Allow,
        ExecutionRiskDecision::Allow,
        &budget(),
        &usage(1),
        true,
    );
    assert_eq!(eligible.decision, ExecutionGateDecision::Proceed);

    let (mut fence_a, mut fence_stdin_a, mut fence_reader_a) = spawn_service("fence", &fence_state);
    let (mut fence_b, mut fence_stdin_b, mut fence_reader_b) = spawn_service("fence", &fence_state);
    let acquired_a = send_json(
        &mut fence_stdin_a,
        &mut fence_reader_a,
        json!({"cmd": "ACQUIRE", "execution_id": "exec-a", "holder": "runtime-a"}),
    );
    assert_eq!(acquired_a["status"], "ACQUIRED");
    assert_eq!(acquired_a["generation"], 1);
    assert_eq!(acquired_a["fence"], 1);

    let (effect_child, effect_stdin, effect_reader) = spawn_service("effect", &effect_state);
    send_json_expect_lost_ack(
        effect_child,
        effect_stdin,
        effect_reader,
        json!({
            "effect_id": "create-marketplace-ticket",
            "idempotency_key": "marketplace-effect-key",
            "execution_id": "exec-a",
            "attempt": 1,
            "payload": "create-ticket",
            "drop_ack": true
        }),
    );

    let health = derive_runtime_health(
        &RuntimeHealthObservation {
            runtime_id: "runtime-a".into(),
            runtime_version: "1.0".into(),
            config_id: "config-a".into(),
            evidence_basis: RuntimeHealthEvidenceBasis::IndependentObservation,
            evidence_ref: "health-after-lost-ack".into(),
            window_start_sequence: 1,
            window_end_sequence: 2,
            attempts: 2,
            successes: 1,
            failures: 1,
            consecutive_failures: 1,
            timeouts: 0,
            transport_failures: 1,
            active_retries: 1,
            fresh_successes_since_unhealthy: 0,
            prior_state: Some(RuntimeHealthState::Healthy),
            self_reported_healthy: Some(true),
        },
        &RuntimeHealthPolicy {
            quarantine_consecutive_failures: 3,
            unhealthy_failure_percent: 75,
            recovery_successes_required: 2,
            retry_pressure_limit: 2,
        },
    )
    .expect("health projection");
    assert_eq!(health.state, RuntimeHealthState::Degraded);
    assert!(health
        .reasons
        .iter()
        .any(|reason| reason.contains("self-report healthy=true did not override")));

    let acquired_b = send_json(
        &mut fence_stdin_b,
        &mut fence_reader_b,
        json!({"cmd": "ACQUIRE", "execution_id": "exec-a", "holder": "runtime-b"}),
    );
    assert_eq!(acquired_b["status"], "ACQUIRED");
    assert_eq!(acquired_b["generation"], 2);
    assert_eq!(acquired_b["fence"], 2);

    let late_a = send_json(
        &mut fence_stdin_a,
        &mut fence_reader_a,
        json!({
            "cmd": "MUTATE",
            "execution_id": "exec-a",
            "holder": "runtime-a",
            "generation": 1,
            "fence": 1
        }),
    );
    assert_eq!(late_a["status"], "REJECTED_STALE_OWNER");
    assert_eq!(late_a["current_holder"], "runtime-b");

    let current_b = send_json(
        &mut fence_stdin_b,
        &mut fence_reader_b,
        json!({
            "cmd": "MUTATE",
            "execution_id": "exec-a",
            "holder": "runtime-b",
            "generation": 2,
            "fence": 2
        }),
    );
    assert_eq!(current_b["status"], "MUTATED");
    assert_eq!(current_b["current_holder"], "runtime-b");

    drop(fence_stdin_a);
    drop(fence_stdin_b);
    let _ = fence_a.wait();
    let _ = fence_b.wait();

    let (mut restarted_effect, mut effect_stdin, mut effect_reader) =
        spawn_service("effect", &effect_state);
    let reconciled_effect = send_json(
        &mut effect_stdin,
        &mut effect_reader,
        json!({
            "effect_id": "create-marketplace-ticket",
            "idempotency_key": "marketplace-effect-key",
            "execution_id": "exec-b",
            "attempt": 2,
            "payload": "create-ticket"
        }),
    );
    assert_eq!(reconciled_effect["status"], "ALREADY_APPLIED");
    assert_eq!(reconciled_effect["application_count"], 2);
    drop(effect_stdin);
    let _ = restarted_effect.wait();

    let observed = budget()
        .observe_usage(&ExecutionObservedUsage {
            usage: usage(1),
            evidence_basis: ExecutionUsageEvidenceBasis::IndependentObservation,
            evidence_ref: "usage-after-failover".into(),
        })
        .expect("observed usage");
    assert!(!observed.over_limit);
    assert_eq!(observed.attempts_observed, 1);

    let retry = evaluate_retry_eligibility(&FailureCausalityFacts {
        original_outcome: FactualExecutionOutcome::Failed,
        failure_class: FailureClass::Transient,
        failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
        failure_class_evidence_ref: Some("transport-lost-ack".into()),
        recovery_required: true,
        recovery_status: RecoveryStatus::Complete,
        current_attempt: 1,
        max_attempts: 3,
        policy_blocked: false,
        risk_blocked: false,
        budget_blocked: false,
    });
    assert_eq!(retry.eligibility, RetryEligibility::Eligible);
    assert_eq!(retry.next_attempt, Some(2));

    let stages = project_execution_stages(&[
        ExecutionStageEvidence {
            stage_id: "dispatch-a".into(),
            sequence: 1,
            requested: true,
            executed: true,
            status: ExecutionStageStatus::Failed,
            reason: "runtime-a lost acknowledgement after external effect".into(),
            evidence_basis: ExecutionStageEvidenceBasis::IndependentObservation,
            evidence_ref: Some("transport-lost-ack".into()),
        },
        ExecutionStageEvidence {
            stage_id: "late-a-done".into(),
            sequence: 2,
            requested: true,
            executed: false,
            status: ExecutionStageStatus::Blocked,
            reason: "stale owner generation rejected".into(),
            evidence_basis: ExecutionStageEvidenceBasis::IndependentObservation,
            evidence_ref: Some("stale-owner-rejected".into()),
        },
        ExecutionStageEvidence {
            stage_id: "telemetry-only".into(),
            sequence: 3,
            requested: false,
            executed: false,
            status: ExecutionStageStatus::NotRequested,
            reason: "telemetry does not carry authority".into(),
            evidence_basis: ExecutionStageEvidenceBasis::Unknown,
            evidence_ref: None,
        },
        ExecutionStageEvidence {
            stage_id: "redundant-cleanup".into(),
            sequence: 4,
            requested: true,
            executed: false,
            status: ExecutionStageStatus::Skipped,
            reason: "external postcondition already proved effect".into(),
            evidence_basis: ExecutionStageEvidenceBasis::Unknown,
            evidence_ref: None,
        },
    ])
    .expect("stage projection");
    assert_eq!(stages.failed, 1);
    assert_eq!(stages.blocked, 1);
    assert_eq!(stages.not_requested, 1);
    assert_eq!(stages.skipped, 1);

    let stale_root = "runtime-a:config-a:generation-1";
    let current_root = "runtime-b:config-b:generation-2";
    let stale_evidence = evidence(runtime_id("runtime-a"), execution_id("exec-a"), stale_root);
    let current_evidence = evidence(
        runtime_id("runtime-b"),
        execution_id("exec-b"),
        current_root,
    );
    let context = acceptance_context(&runtime_id("runtime-b"), current_root);

    assert_eq!(
        canonical_acceptance(&context, &[], 30.0).decision,
        AcceptanceDecision::NotDone
    );
    assert_eq!(
        canonical_acceptance(&context, &[stale_evidence], 30.0).decision,
        AcceptanceDecision::Block
    );
    let accepted = canonical_acceptance(&context, &[current_evidence], 30.0);
    assert_eq!(accepted.decision, AcceptanceDecision::Accept);
    assert!(accepted.proof.is_some());

    let record = GateEvidenceRecord {
        schema_version: "metao.gate-evidence.v1",
        record_id: "gate-composed-system-final-closure-v1",
        repository: "tihotm/metaO",
        gate_id: "COMPOSED_SYSTEM_PROOF",
        gate_level: "L4_MULTIPROCESS_RESTART_WITH_REAL_LOCAL_EXTERNAL_SERVICE",
        runtime_identities: vec!["runtime-a", "runtime-b"],
        mission_id: mission_id().as_str().into(),
        execution_lineage: vec!["exec-a:generation-1", "exec-b:generation-2"],
        result: "PASS",
        substrate: vec![
            "SIMULATED_RUNTIME",
            "LOCAL_REAL_PROCESS",
            "MULTIPROCESS",
            "DURABLE_FILE_STORE",
            "REAL_LOCAL_EXTERNAL_SERVICE",
            "FAULT_INJECTION",
        ],
        external_systems_real: true,
        claim_boundary:
            "local composed proof only; no real external orchestrator/provider execution claimed",
    };
    let serialized = serde_json::to_value(&record).expect("machine-readable evidence");
    assert_eq!(serialized["result"], "PASS");
    assert_eq!(serialized["external_systems_real"], true);
    assert!(serialized["claim_boundary"]
        .as_str()
        .unwrap()
        .contains("no real external orchestrator"));

    fs::remove_file(&effect_state).ok();
    fs::remove_file(&fence_state).ok();
    fs::remove_dir_all(&root).ok();
}
