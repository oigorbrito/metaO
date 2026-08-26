use metao_contracts::{AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus, MissionId, Orchestrator, PolicyEffect, RuntimeId};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_nidus_host::{ambiguous_provider_graph, circular_host_graph, valid_host_graph};
use metao_registry::{Registry, RegistryError};
use nidus_core::NidusError;

const NOW:i64=15;
fn request()->ExecutionRequest{ExecutionRequest{execution_id:ExecutionId("exec-1".into()),mission_id:MissionId("mission-1".into())}}
fn success(runtime:&str)->ExecutionResult{ExecutionResult{execution_id:ExecutionId("exec-1".into()),runtime_id:RuntimeId(runtime.into()),status:ExecutionStatus::Succeeded}}
fn evidence(runtime:&str)->Evidence{Evidence{mission_id:MissionId("mission-1".into()),execution_id:ExecutionId("exec-1".into()),runtime_id:RuntimeId(runtime.into()),policy_version:"policy-v1".into(),verified:true,created_at_epoch:10,expires_at_epoch:20}}

struct Alpha; struct AlphaV2; struct Beta; struct PanicRuntime;
impl Orchestrator for Alpha{fn id(&self)->RuntimeId{RuntimeId("alpha".into())}fn version(&self)->String{"1".into()}fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}}}
impl Orchestrator for AlphaV2{fn id(&self)->RuntimeId{RuntimeId("alpha".into())}fn version(&self)->String{"2".into()}fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}}}
impl Orchestrator for Beta{fn id(&self)->RuntimeId{RuntimeId("beta".into())}fn version(&self)->String{"1".into()}fn execute(&self,r:&ExecutionRequest)->ExecutionResult{ExecutionResult{execution_id:r.execution_id.clone(),runtime_id:self.id(),status:ExecutionStatus::Succeeded}}}
impl Orchestrator for PanicRuntime{fn id(&self)->RuntimeId{RuntimeId("panic".into())}fn version(&self)->String{"1".into()}fn execute(&self,_:&ExecutionRequest)->ExecutionResult{panic!("simulated adapter failure")}}

#[test]
fn same_semantic_slice_as_spike_a(){
 let mut registry=Registry::default();registry.register(Box::new(Alpha)).unwrap();assert_eq!(registry.execute_contained(&RuntimeId("alpha".into()),&request()).unwrap().runtime_id,RuntimeId("alpha".into()));
 assert!(registry.unregister(&RuntimeId("alpha".into())));registry.register(Box::new(Beta)).unwrap();assert_eq!(registry.execute_contained(&RuntimeId("beta".into()),&request()).unwrap().runtime_id,RuntimeId("beta".into()));
 assert_eq!(evaluate_acceptance(&request(),&success("beta"),None,PolicyEffect::Allow,NOW),AcceptanceDecision::NotDone);
 assert_eq!(evaluate_acceptance(&request(),&success("beta"),Some(&evidence("beta")),PolicyEffect::Allow,NOW),AcceptanceDecision::Accept);
 assert_eq!(evaluate_acceptance(&request(),&success("beta"),Some(&evidence("beta")),PolicyEffect::Deny,NOW),AcceptanceDecision::Block);
 assert_eq!(evaluate_acceptance(&request(),&success("beta"),Some(&evidence("beta")),PolicyEffect::Allow,21),AcceptanceDecision::Stale);
}

#[test]
fn duplicate_version_conflict_and_panic_are_deterministic(){
 let mut duplicate=Registry::default();duplicate.register(Box::new(Alpha)).unwrap();assert_eq!(duplicate.register(Box::new(Alpha)),Err(RegistryError::Duplicate(RuntimeId("alpha".into()))));
 let mut conflict=Registry::default();conflict.register(Box::new(Alpha)).unwrap();assert_eq!(conflict.register(Box::new(AlphaV2)),Err(RegistryError::VersionConflict{id:RuntimeId("alpha".into()),existing:"1".into(),incoming:"2".into()}));
 let mut panics=Registry::default();panics.register(Box::new(PanicRuntime)).unwrap();assert_eq!(panics.execute_contained(&RuntimeId("panic".into()),&request()),Err(RegistryError::Panicked(RuntimeId("panic".into()))));
}

#[test]
fn reconciliation_matches_spike_a_semantics(){let desired=vec![RuntimeId("alpha".into()),RuntimeId("beta".into())];let mut observed=vec![RuntimeId("alpha".into())];let missing=reconcile_missing(&desired,&observed);assert_eq!(missing,vec![RuntimeId("beta".into())]);observed.extend(missing);assert!(reconcile_missing(&desired,&observed).is_empty());assert!(reconcile_missing(&desired,&observed).is_empty());}

#[test]
fn exhaustive_small_reconcile_state_space_satisfies_laws(){
 let universe=[RuntimeId("alpha".into()),RuntimeId("beta".into()),RuntimeId("gamma".into())];
 for desired_mask in 0u8..8{for observed_mask in 0u8..8{
  let desired:Vec<_>=universe.iter().enumerate().filter(|(i,_)|desired_mask&(1<<i)!=0).map(|(_,r)|r.clone()).collect();
  let observed:Vec<_>=universe.iter().enumerate().filter(|(i,_)|observed_mask&(1<<i)!=0).map(|(_,r)|r.clone()).collect();
  let first=reconcile_missing(&desired,&observed);let second=reconcile_missing(&desired,&observed);assert_eq!(first,second,"reconcile must be deterministic");
  assert!(first.windows(2).all(|w|w[0]<w[1]),"missing must be sorted and deduplicated");
  assert!(first.iter().all(|r|desired.contains(r)&&!observed.contains(r)));
  let mut converged=observed.clone();converged.extend(first);assert!(reconcile_missing(&desired,&converged).is_empty(),"one application must converge for this model");
 }}
}

#[test]
fn kernel_has_no_nidus_or_platform_dependency(){let manifest=include_str!("../../metao-kernel/Cargo.toml").to_lowercase();for forbidden in["nidus","axum","tokio","tower","sqlx","kube","windows","libc"]{assert!(!manifest.contains(forbidden),"framework leaked into kernel: {forbidden}");}let source=include_str!("../../metao-kernel/src/lib.rs").to_lowercase();for forbidden in["nidus","unsafe","cfg(target_os","cfg(windows","cfg(unix"]{assert!(!source.contains(forbidden),"kernel leak: {forbidden}");}}

#[test]
fn nidus_graph_adds_only_host_level_guards(){let graph=valid_host_graph().unwrap();let names=graph.modules().map(|m|m.name()).collect::<Vec<_>>();assert_eq!(names,["MetaOKernelModule","RuntimeAdaptersModule"]);assert!(matches!(circular_host_graph().unwrap_err(),NidusError::CircularModuleImport{..}));assert!(matches!(ambiguous_provider_graph().unwrap_err(),NidusError::AmbiguousProvider{..}));}
