use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus,
    MissionId, Orchestrator, PolicyEffect, RuntimeId,
};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_registry::{Registry, RegistryError};

fn request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: ExecutionId("exec-1".into()),
        mission_id: MissionId("mission-1".into()),
    }
}

fn success(runtime: &str) -> ExecutionResult {
    ExecutionResult {
        execution_id: ExecutionId("exec-1".into()),
        runtime_id: RuntimeId(runtime.into()),
        status: ExecutionStatus::Succeeded,
    }
}

fn evidence(runtime: &str) -> Evidence {
    Evidence {
        mission_id: MissionId("mission-1".into()),
        execution_id: ExecutionId("exec-1".into()),
        runtime_id: RuntimeId(runtime.into()),
        policy_version: "policy-v1".into(),
        verified: true,
    }
}

struct Alpha;
struct Beta;
struct PanicRuntime;

impl Orchestrator for Alpha {
    fn id(&self) -> RuntimeId {
        RuntimeId("alpha".into())
    }

    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: request.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}

impl Orchestrator for Beta {
    fn id(&self) -> RuntimeId {
        RuntimeId("beta".into())
    }

    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: request.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}

impl Orchestrator for PanicRuntime {
    fn id(&self) -> RuntimeId {
        RuntimeId("panic".into())
    }

    fn execute(&self, _request: &ExecutionRequest) -> ExecutionResult {
        panic!("simulated adapter failure")
    }
}

#[test]
fn whole_orchestrator_replacement_changes_no_kernel_contract() {
    let mut registry = Registry::default();
    registry.register(Box::new(Alpha)).unwrap();
    let first = registry
        .execute_contained(&RuntimeId("alpha".into()), &request())
        .unwrap();
    assert_eq!(first.runtime_id, RuntimeId("alpha".into()));

    assert!(registry.unregister(&RuntimeId("alpha".into())));
    registry.register(Box::new(Beta)).unwrap();
    let second = registry
        .execute_contained(&RuntimeId("beta".into()), &request())
        .unwrap();
    assert_eq!(second.runtime_id, RuntimeId("beta".into()));
}

#[test]
fn duplicate_runtime_identity_fails_deterministically() {
    let mut registry = Registry::default();
    registry.register(Box::new(Alpha)).unwrap();
    assert_eq!(
        registry.register(Box::new(Alpha)),
        Err(RegistryError::Duplicate(RuntimeId("alpha".into())))
    );
}

#[test]
fn succeeded_never_implies_accepted_without_evidence() {
    assert_eq!(
        evaluate_acceptance(&request(), &success("alpha"), None, PolicyEffect::Allow),
        AcceptanceDecision::NotDone
    );
}

#[test]
fn hard_deny_cannot_be_overridden_by_runtime_success() {
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Deny,
        ),
        AcceptanceDecision::Block
    );
}

#[test]
fn bound_verified_evidence_can_accept() {
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
        ),
        AcceptanceDecision::Accept
    );
}

#[test]
fn mismatched_runtime_evidence_blocks() {
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("beta")),
            PolicyEffect::Allow,
        ),
        AcceptanceDecision::Block
    );
}

#[test]
fn adversarial_evidence_binding_matrix_only_accepts_exact_verified_binding() {
    for verified in [false, true] {
        for mission_matches in [false, true] {
            for execution_matches in [false, true] {
                for runtime_matches in [false, true] {
                    let mut item = evidence(if runtime_matches { "alpha" } else { "beta" });
                    item.verified = verified;
                    if !mission_matches {
                        item.mission_id = MissionId("wrong-mission".into());
                    }
                    if !execution_matches {
                        item.execution_id = ExecutionId("wrong-exec".into());
                    }

                    let decision = evaluate_acceptance(
                        &request(),
                        &success("alpha"),
                        Some(&item),
                        PolicyEffect::Allow,
                    );
                    let should_accept = verified
                        && mission_matches
                        && execution_matches
                        && runtime_matches;
                    assert_eq!(decision == AcceptanceDecision::Accept, should_accept);
                }
            }
        }
    }
}

#[test]
fn failed_execution_never_accepts_even_with_valid_evidence() {
    let failed = ExecutionResult {
        execution_id: ExecutionId("exec-1".into()),
        runtime_id: RuntimeId("alpha".into()),
        status: ExecutionStatus::Failed,
    };
    assert_ne!(
        evaluate_acceptance(
            &request(),
            &failed,
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
        ),
        AcceptanceDecision::Accept
    );
}

#[test]
fn adapter_panic_is_contained() {
    let mut registry = Registry::default();
    registry.register(Box::new(PanicRuntime)).unwrap();
    assert_eq!(
        registry.execute_contained(&RuntimeId("panic".into()), &request()),
        Err(RegistryError::Panicked(RuntimeId("panic".into())))
    );
}

#[test]
fn reconciliation_is_idempotent_after_convergence() {
    let desired = vec![RuntimeId("alpha".into()), RuntimeId("beta".into())];
    let mut observed = vec![RuntimeId("alpha".into())];
    let missing = reconcile_missing(&desired, &observed);
    assert_eq!(missing, vec![RuntimeId("beta".into())]);
    observed.extend(missing);
    assert!(reconcile_missing(&desired, &observed).is_empty());
    assert!(reconcile_missing(&desired, &observed).is_empty());
}

#[test]
fn reconciliation_is_deterministic_and_deduplicates_desired_state() {
    let desired = vec![
        RuntimeId("beta".into()),
        RuntimeId("alpha".into()),
        RuntimeId("beta".into()),
    ];
    let observed = vec![];
    assert_eq!(
        reconcile_missing(&desired, &observed),
        vec![RuntimeId("alpha".into()), RuntimeId("beta".into())]
    );
}

#[test]
fn kernel_manifest_has_no_platform_or_framework_dependencies() {
    let manifest = include_str!("../../metao-kernel/Cargo.toml").to_lowercase();
    for forbidden in [
        "axum", "tokio", "kube", "openai", "langgraph", "crewai", "sqlx", "windows", "libc",
    ] {
        assert!(!manifest.contains(forbidden), "forbidden kernel dependency: {forbidden}");
    }
}

#[test]
fn kernel_owned_source_has_no_unsafe_block_or_platform_cfg() {
    let source = include_str!("../../metao-kernel/src/lib.rs").to_lowercase();
    assert!(!source.contains("unsafe"));
    assert!(!source.contains("cfg(target_os"));
    assert!(!source.contains("cfg(windows"));
    assert!(!source.contains("cfg(unix"));
}
