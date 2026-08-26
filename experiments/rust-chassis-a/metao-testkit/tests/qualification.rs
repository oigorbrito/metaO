use metao_contracts::{AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus, MissionId, Orchestrator, PolicyEffect, RuntimeId};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_registry::{Registry, RegistryError};

const NOW: i64 = 15;
fn request() -> ExecutionRequest { ExecutionRequest { execution_id: ExecutionId("exec-1".into()), mission_id: MissionId("mission-1".into()) } }
fn success(runtime: &str) -> ExecutionResult { ExecutionResult { execution_id: ExecutionId("exec-1".into()), runtime_id: RuntimeId(runtime.into()), status: ExecutionStatus::Succeeded } }
fn evidence(runtime: &str) -> Evidence { Evidence { mission_id: MissionId("mission-1".into()), execution_id: ExecutionId("exec-1".into()), runtime_id: RuntimeId(runtime.into()), policy_version: "policy-v1".into(), verified: true, created_at_epoch: 10, expires_at_epoch: 20 } }

struct Alpha; struct AlphaV2; struct Beta; struct PanicRuntime;
impl Orchestrator for Alpha { fn id(&self)->RuntimeId{RuntimeId("alpha".into())} fn version(&self)->String{"1".into()} fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}} }
impl Orchestrator for AlphaV2 { fn id(&self)->RuntimeId{RuntimeId("alpha".into())} fn version(&self)->String{"2".into()} fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}} }
impl Orchestrator for Beta { fn id(&self)->RuntimeId{RuntimeId("beta".into())} fn version(&self)->String{"1".into()} fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}} }
impl Orchestrator for PanicRuntime { fn id(&self)->RuntimeId{RuntimeId("panic".into())} fn version(&self)->String{"1".into()} fn execute(&self,_:&ExecutionRequest)->ExecutionResult{panic!("simulated adapter failure")} }

#[test]
fn whole_orchestrator_replacement_changes_no_kernel_contract() {
    let mut registry=Registry::default(); registry.register(Box::new(Alpha)).unwrap();
    assert_eq!(registry.execute_contained(&RuntimeId("alpha".into()),&request()).unwrap().runtime_id,RuntimeId("alpha".into()));
    assert!(registry.unregister(&RuntimeId("alpha".into()))); registry.register(Box::new(Beta)).unwrap();
    assert_eq!(registry.execute_contained(&RuntimeId("beta".into()),&request()).unwrap().runtime_id,RuntimeId("beta".into()));
}

#[test]
fn duplicate_and_version_conflict_fail_deterministically() {
    let mut duplicate=Registry::default(); duplicate.register(Box::new(Alpha)).unwrap();
    assert_eq!(duplicate.register(Box::new(Alpha)),Err(RegistryError::Duplicate(RuntimeId("alpha".into()))));
    let mut conflict=Registry::default(); conflict.register(Box::new(Alpha)).unwrap();
    assert_eq!(conflict.register(Box::new(AlphaV2)),Err(RegistryError::VersionConflict{id:RuntimeId("alpha".into()),existing:"1".into(),incoming:"2".into()}));
}

#[test]
fn acceptance_hard_gates_match_python_baseline() {
    assert_eq!(evaluate_acceptance(&request(),&success("alpha"),None,PolicyEffect::Allow,NOW),AcceptanceDecision::NotDone);
    assert_eq!(evaluate_acceptance(&request(),&success("alpha"),Some(&evidence("alpha")),PolicyEffect::Deny,NOW),AcceptanceDecision::Block);
    assert_eq!(evaluate_acceptance(&request(),&success("alpha"),Some(&evidence("alpha")),PolicyEffect::Allow,NOW),AcceptanceDecision::Accept);
    assert_eq!(evaluate_acceptance(&request(),&success("alpha"),Some(&evidence("alpha")),PolicyEffect::Allow,21),AcceptanceDecision::Stale);
    assert_eq!(evaluate_acceptance(&request(),&success("alpha"),Some(&evidence("beta")),PolicyEffect::Allow,NOW),AcceptanceDecision::Block);
}

#[test]
fn adversarial_evidence_binding_matrix_only_accepts_exact_verified_binding() {
    for verified in [false,true] { for mission_matches in [false,true] { for execution_matches in [false,true] { for runtime_matches in [false,true] {
        let mut item=evidence(if runtime_matches{"alpha"}else{"beta"}); item.verified=verified;
        if !mission_matches { item.mission_id=MissionId("wrong-mission".into()); }
        if !execution_matches { item.execution_id=ExecutionId("wrong-exec".into()); }
        let decision=evaluate_acceptance(&request(),&success("alpha"),Some(&item),PolicyEffect::Allow,NOW);
        assert_eq!(decision==AcceptanceDecision::Accept,verified&&mission_matches&&execution_matches&&runtime_matches);
    }}}}
}

#[test]
fn failed_execution_never_accepts_and_panic_is_contained() {
    let failed=ExecutionResult{execution_id:ExecutionId("exec-1".into()),runtime_id:RuntimeId("alpha".into()),status:ExecutionStatus::Failed};
    assert_ne!(evaluate_acceptance(&request(),&failed,Some(&evidence("alpha")),PolicyEffect::Allow,NOW),AcceptanceDecision::Accept);
    let mut registry=Registry::default(); registry.register(Box::new(PanicRuntime)).unwrap();
    assert_eq!(registry.execute_contained(&RuntimeId("panic".into()),&request()),Err(RegistryError::Panicked(RuntimeId("panic".into()))));
}

#[test]
fn reconciliation_is_idempotent_and_deterministic() {
    let desired=vec![RuntimeId("alpha".into()),RuntimeId("beta".into())]; let mut observed=vec![RuntimeId("alpha".into())];
    let missing=reconcile_missing(&desired,&observed); assert_eq!(missing,vec![RuntimeId("beta".into())]); observed.extend(missing);
    assert!(reconcile_missing(&desired,&observed).is_empty()); assert!(reconcile_missing(&desired,&observed).is_empty());
    let duplicated=vec![RuntimeId("beta".into()),RuntimeId("alpha".into()),RuntimeId("beta".into())];
    assert_eq!(reconcile_missing(&duplicated,&[]),vec![RuntimeId("alpha".into()),RuntimeId("beta".into())]);
}

#[test]
fn kernel_is_platform_framework_and_unsafe_free() {
    let manifest=include_str!("../../metao-kernel/Cargo.toml").to_lowercase();
    for forbidden in ["axum","tokio","kube","openai","langgraph","crewai","sqlx","windows","libc"] { assert!(!manifest.contains(forbidden),"forbidden kernel dependency: {forbidden}"); }
    let source=include_str!("../../metao-kernel/src/lib.rs").to_lowercase();
    for forbidden in ["unsafe","cfg(target_os","cfg(windows","cfg(unix"] { assert!(!source.contains(forbidden),"kernel leak: {forbidden}"); }
}
