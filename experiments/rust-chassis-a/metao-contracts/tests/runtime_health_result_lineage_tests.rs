use metao_contracts::execution_lease::{
    bind_execution_runtime_identity, bind_runtime_health_observation_lineage, BoundExecutionRuntimeIdentity,
    ExecutionLease, ExecutionResultLineageProducer, ExecutionRuntimeBindingBasis,
    ExecutionRuntimeBindingClaim, ExecutionRuntimeBindingProducer, LeaseAssurance, LeaseEvidenceBasis,
    LeaseState, RuntimeHealthLineageError,
};
use metao_contracts::runtime_health::{RuntimeHealthEvidenceBasis, RuntimeHealthObservation};

fn lease(execution: &str, generation: u64, fence: u64) -> ExecutionLease {
    ExecutionLease { mission_id:"mission-481".into(),logical_execution_key:"logical-481".into(),execution_id:execution.into(),holder_identity:"worker".into(),generation,fencing_token:fence,acquired_at_epoch:100,renewed_at_epoch:110,expires_at_epoch:200,state:LeaseState::Active,assurance:LeaseAssurance::AuthoritativeStore,evidence_basis:LeaseEvidenceBasis::AuthoritativeStoreRead,evidence_ref:Some("lease://481".into()) }
}
fn identity(execution:&str,generation:u64,fence:u64)->BoundExecutionRuntimeIdentity{
    let producer=ExecutionRuntimeBindingProducer{producer_id:"dispatch-481".into(),mission_id:"mission-481".into(),logical_execution_key:"logical-481".into(),execution_id:execution.into(),runtime_id:"runtime-a".into(),runtime_version:"1.0".into(),config_id:"cfg-a".into(),lease_generation:generation,fencing_token:fence,basis:ExecutionRuntimeBindingBasis::CanonicalDispatch,evidence_ref:"dispatch://481".into()};
    let claim=ExecutionRuntimeBindingClaim{mission_id:"mission-481".into(),logical_execution_key:"logical-481".into(),execution_id:execution.into(),runtime_id:"runtime-a".into(),runtime_version:"1.0".into(),config_id:"cfg-a".into(),lease_generation:generation,fencing_token:fence};
    bind_execution_runtime_identity(&claim,&producer,&lease(execution,generation,fence)).unwrap()
}
fn observation(ref_id:&str)->RuntimeHealthObservation{RuntimeHealthObservation{runtime_id:"runtime-a".into(),runtime_version:"1.0".into(),config_id:"cfg-a".into(),evidence_basis:RuntimeHealthEvidenceBasis::AdapterVerified,evidence_ref:ref_id.into(),window_start_sequence:1,window_end_sequence:1,attempts:1,successes:0,failures:1,consecutive_failures:1,timeouts:0,transport_failures:0,active_retries:0,fresh_successes_since_unhealthy:0,prior_state:None,self_reported_healthy:None}}
fn result(execution:&str,result_id:&str,obs_ref:&str,generation:u64,fence:u64)->ExecutionResultLineageProducer{ExecutionResultLineageProducer{result_id:result_id.into(),execution_id:execution.into(),runtime_id:"runtime-a".into(),runtime_version:"1.0".into(),config_id:"cfg-a".into(),lease_generation:generation,fencing_token:fence,health_observation_evidence_ref:obs_ref.into(),result_evidence_ref:format!("result://{result_id}")}}

#[test]
fn exact_execution_result_lineage_binds_health_observation(){let id=identity("execution-b",7,11);let bound=bind_runtime_health_observation_lineage(&id,&result("execution-b","result-b","health://result-b",7,11),&observation("health://result-b")).unwrap();assert_eq!(bound.execution_id,"execution-b");assert_eq!(bound.result_id,"result-b");}
#[test]
fn observation_from_execution_a_cannot_be_admitted_under_execution_b(){let id=identity("execution-b",7,11);assert_eq!(bind_runtime_health_observation_lineage(&id,&result("execution-a","result-a","health://result-a",7,11),&observation("health://result-a")),Err(RuntimeHealthLineageError::RuntimeBindingMismatch));}
#[test]
fn copied_runtime_tuple_and_wrong_observation_evidence_ref_do_not_prove_causality(){let id=identity("execution-b",7,11);assert_eq!(bind_runtime_health_observation_lineage(&id,&result("execution-b","result-b","health://canonical-b",7,11),&observation("health://copied")),Err(RuntimeHealthLineageError::ObservationLineageMismatch));}
#[test]
fn replay_after_takeover_is_rejected_independently_of_runtime_tuple(){let id=identity("execution-b",8,12);assert_eq!(bind_runtime_health_observation_lineage(&id,&result("execution-b","old-result","health://old",7,11),&observation("health://old")),Err(RuntimeHealthLineageError::RuntimeBindingMismatch));}
#[test]
fn zero_attempt_bootstrap_cannot_be_execution_bound_fact(){let id=identity("execution-b",7,11);let mut obs=observation("health://result-b");obs.attempts=0;obs.failures=0;obs.consecutive_failures=0;obs.evidence_basis=RuntimeHealthEvidenceBasis::Unknown;assert_eq!(bind_runtime_health_observation_lineage(&id,&result("execution-b","result-b","health://result-b",7,11),&obs),Err(RuntimeHealthLineageError::ObservationLineageMismatch));}
