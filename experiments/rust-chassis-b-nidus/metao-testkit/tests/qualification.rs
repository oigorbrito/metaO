use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus,
    MissionId, Orchestrator, PolicyEffect, RuntimeId,
};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_nidus_host::{ambiguous_provider_graph, circular_host_graph, valid_host_graph};
use metao_registry::{Registry, RegistryError};
use nidus_core::NidusError;

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
    assert_eq!(
        registry
            .execute_contained(&RuntimeId("alpha".into()), &request())
            .unwrap()
            .runtime_id,
        RuntimeId("alpha".into())
    );
    assert!(registry.unregister(&RuntimeId("alpha".into())));
    registry.register(Box::new(Beta)).unwrap();
    assert_eq!(
        registry
            .execute_contained(&RuntimeId("beta".into()), &request())
            .unwrap()
            .runtime_id,
        RuntimeId("beta".into())
    );
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
fn runtime_success_without_evidence_is_not_acceptance() {
    assert_eq!(
        evaluate_acceptance(&request(), &success("alpha"), None, PolicyEffect::Allow),
        AcceptanceDecision::NotDone
    );
}

#[test]
fn hard_deny_wins_even_with_success_and_evidence() {
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
fn evidence_binding_and_panic_containment_match_spike_a() {
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
        ),
        AcceptanceDecision::Accept
    );
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("beta")),
            PolicyEffect::Allow,
        ),
        AcceptanceDecision::Block
    );

    let mut registry = Registry::default();
    registry.register(Box::new(PanicRuntime)).unwrap();
    assert_eq!(
        registry.execute_contained(&RuntimeId("panic".into()), &request()),
        Err(RegistryError::Panicked(RuntimeId("panic".into())))
    );
}

#[test]
fn reconciliation_matches_spike_a_semantics() {
    let desired = vec![RuntimeId("alpha".into()), RuntimeId("beta".into())];
    let mut observed = vec![RuntimeId("alpha".into())];
    let missing = reconcile_missing(&desired, &observed);
    assert_eq!(missing, vec![RuntimeId("beta".into())]);
    observed.extend(missing);
    assert!(reconcile_missing(&desired, &observed).is_empty());
    assert!(reconcile_missing(&desired, &observed).is_empty());
}

#[test]
fn kernel_has_no_nidus_or_web_dependency() {
    let manifest = include_str!("../../metao-kernel/Cargo.toml").to_lowercase();
    for forbidden in ["nidus", "axum", "tokio", "tower", "sqlx", "kube", "windows", "libc"] {
        assert!(!manifest.contains(forbidden), "framework leaked into kernel: {forbidden}");
    }
}

#[test]
fn nidus_host_graph_accepts_explicit_valid_boundaries() {
    let graph = valid_host_graph().unwrap();
    let names = graph.modules().map(|m| m.name()).collect::<Vec<_>>();
    assert_eq!(names, ["MetaOKernelModule", "RuntimeAdaptersModule"]);
}

#[test]
fn nidus_rejects_circular_module_dependency() {
    let error = circular_host_graph().unwrap_err();
    assert!(matches!(error, NidusError::CircularModuleImport { .. }));
}

#[test]
fn nidus_rejects_ambiguous_runtime_provider_visibility() {
    let error = ambiguous_provider_graph().unwrap_err();
    assert!(matches!(error, NidusError::AmbiguousProvider { .. }));
}

#[test]
fn kernel_owned_source_contains_no_nidus_or_platform_symbol() {
    let source = include_str!("../../metao-kernel/src/lib.rs").to_lowercase();
    assert!(!source.contains("nidus"));
    assert!(!source.contains("unsafe"));
    assert!(!source.contains("cfg(target_os"));
    assert!(!source.contains("cfg(windows"));
    assert!(!source.contains("cfg(unix"));
}
