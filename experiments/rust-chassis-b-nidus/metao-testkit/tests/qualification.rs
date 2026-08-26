use metao_kernel::{acceptance, AcceptanceDecision, ExecutionStatus, PolicyEffect};
use metao_nidus_host::{ambiguous_provider_graph, circular_host_graph, valid_host_graph};
use nidus_core::NidusError;

#[test]
fn kernel_has_no_nidus_or_web_dependency() {
    let manifest = include_str!("../../metao-kernel/Cargo.toml").to_lowercase();
    for forbidden in ["nidus", "axum", "tokio", "tower", "sqlx", "kube"] {
        assert!(!manifest.contains(forbidden), "framework leaked into kernel: {forbidden}");
    }
}

#[test]
fn runtime_success_without_evidence_is_not_acceptance() {
    assert_eq!(
        acceptance(ExecutionStatus::Succeeded, false, PolicyEffect::Allow),
        AcceptanceDecision::NotDone
    );
}

#[test]
fn hard_deny_wins_even_with_success_and_evidence() {
    assert_eq!(
        acceptance(ExecutionStatus::Succeeded, true, PolicyEffect::Deny),
        AcceptanceDecision::Block
    );
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
fn kernel_owned_source_contains_no_nidus_symbol() {
    let source = include_str!("../../metao-kernel/src/lib.rs").to_lowercase();
    assert!(!source.contains("nidus"));
}
