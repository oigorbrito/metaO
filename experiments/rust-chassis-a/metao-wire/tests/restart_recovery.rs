use std::time::Duration;

use metao_contracts::{
    AcceptanceDecision, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus, MissionId,
    PolicyEffect, RuntimeId,
};
use metao_kernel::evaluate_acceptance;
use metao_wire::{
    execute_with_recovery, RecoveryPolicy, RuntimeExecutionBlocked, RuntimeExecutionFailure,
    RuntimeExecutionOutcome, WireRequest, PROTOCOL_VERSION,
};

fn runtime_binary() -> &'static str {
    env!("CARGO_BIN_EXE_metao-wire-runtime")
}

fn request(objective: &str) -> WireRequest {
    WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "phase4-exec-1".into(),
        mission_id: "phase4-mission-1".into(),
        objective: objective.into(),
    }
}

fn kernel_request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: ExecutionId::new("phase4-exec-1").unwrap(),
        mission_id: MissionId::new("phase4-mission-1").unwrap(),
    }
}

fn kernel_result(runtime_id: &str) -> ExecutionResult {
    ExecutionResult {
        execution_id: ExecutionId::new("phase4-exec-1").unwrap(),
        runtime_id: RuntimeId::new(runtime_id).unwrap(),
        status: ExecutionStatus::Succeeded,
    }
}

#[test]
fn crash_recovery_completes_on_second_attempt() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__crash_then_recover__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            assert_eq!(attempts, 2);
            assert_eq!(response.execution_id, "phase4-exec-1");
            assert_eq!(response.status, "SUCCEEDED");
        }
        other => panic!("unexpected outcome: {other:?}"),
    }
}

#[test]
fn timeout_recovery_completes_on_second_attempt() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__hang_then_recover__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            assert_eq!(attempts, 2);
            assert_eq!(response.execution_id, "phase4-exec-1");
            assert_eq!(response.status, "SUCCEEDED");
        }
        other => panic!("unexpected outcome: {other:?}"),
    }
}

#[test]
fn recovery_exhaustion_is_explicit_failure() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__crash__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    assert_eq!(
        outcome,
        RuntimeExecutionOutcome::Failed {
            reason: RuntimeExecutionFailure::RecoveryExhausted,
            attempts: 2,
        }
    );
}

#[test]
fn malformed_protocol_is_explicitly_blocked() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__malformed_response__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    assert_eq!(
        outcome,
        RuntimeExecutionOutcome::Blocked {
            reason: RuntimeExecutionBlocked::MalformedProtocol,
            attempts: 1,
        }
    );
}

#[test]
fn incompatible_protocol_is_explicitly_blocked() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__bad_version__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    assert_eq!(
        outcome,
        RuntimeExecutionOutcome::Blocked {
            reason: RuntimeExecutionBlocked::IncompatibleProtocol,
            attempts: 1,
        }
    );
}

#[test]
fn recovered_runtime_success_does_not_mint_acceptance() {
    let outcome = execute_with_recovery(
        runtime_binary(),
        &request("__crash_then_recover__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    let response = match outcome {
        RuntimeExecutionOutcome::Completed { response, attempts } => {
            assert_eq!(attempts, 2);
            response
        }
        other => panic!("unexpected outcome: {other:?}"),
    };
    let decision = evaluate_acceptance(
        &kernel_request(),
        &kernel_result(&response.runtime_id),
        None,
        PolicyEffect::Allow,
        15,
    );
    assert_eq!(decision, AcceptanceDecision::NotDone);
}

#[test]
fn parent_is_reusable_after_recovery() {
    let recovered = execute_with_recovery(
        runtime_binary(),
        &request("__crash_then_recover__"),
        RecoveryPolicy::new(1, Duration::from_millis(200)),
    );
    assert!(matches!(
        recovered,
        RuntimeExecutionOutcome::Completed { .. }
    ));

    let normal = execute_with_recovery(
        runtime_binary(),
        &request("normal"),
        RecoveryPolicy::new(0, Duration::from_millis(200)),
    );
    assert!(matches!(normal, RuntimeExecutionOutcome::Completed { .. }));
}
