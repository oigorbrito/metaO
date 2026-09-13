use metao_contracts::runtime_health::{ActiveRetryAuthorityBasis,ActiveRetryExecutionRecord,ActiveRetryExecutionState,ActiveRetrySetPersistedState,ActiveRetrySetProducer,ActiveRetrySetState,RuntimeHealthError};
use metao_contracts::MissionId;

fn record(id:&str,state:ActiveRetryExecutionState)->ActiveRetryExecutionRecord{ActiveRetryExecutionRecord{retry_execution_id:id.into(),mission_id:MissionId::new("m504").unwrap(),runtime_id:"runtime-a".into(),runtime_version:"1".into(),config_id:"cfg-a".into(),retry_lineage_id:"lineage-504".into(),authority_generation:7,fencing_token:11,current_authority_generation:7,current_fencing_token:11,state,evidence_ref:format!("retry://{id}")}}
fn producer(records:Vec<ActiveRetryExecutionRecord>)->ActiveRetrySetProducer{ActiveRetrySetProducer{producer_id:"registry-504".into(),state_version:9,basis:ActiveRetryAuthorityBasis::CanonicalExecutionRegistry,evidence_ref:"registry://504/v9".into(),records}}

#[test]
fn json_round_trip_preserves_pressure(){let state=ActiveRetrySetState::from_producer(producer(vec![record("r1",ActiveRetryExecutionState::Active),record("r2",ActiveRetryExecutionState::Settled)])).unwrap();let before=state.bind_pressure("runtime-a","1","cfg-a").unwrap();let encoded=serde_json::to_string(&state.export_state()).unwrap();let persisted:ActiveRetrySetPersistedState=serde_json::from_str(&encoded).unwrap();let reopened=ActiveRetrySetState::reopen(persisted).unwrap();let after=reopened.bind_pressure("runtime-a","1","cfg-a").unwrap();assert_eq!(before.active_retries(),after.active_retries());assert_eq!(after.active_retries(),1);assert_eq!(after.state_version(),9);}

#[test]
fn terminal_records_remain_non_active_after_restart(){let state=ActiveRetrySetState::from_producer(producer(vec![record("r1",ActiveRetryExecutionState::Settled),record("r2",ActiveRetryExecutionState::Cancelled),record("r3",ActiveRetryExecutionState::Expired)])).unwrap();let reopened=ActiveRetrySetState::reopen(state.export_state()).unwrap();assert_eq!(reopened.bind_pressure("runtime-a","1","cfg-a").unwrap().active_retries(),0);}

#[test]
fn stale_active_record_fails_closed_on_reopen(){let mut stale=record("r1",ActiveRetryExecutionState::Active);stale.current_fencing_token=12;assert_eq!(ActiveRetrySetState::reopen(ActiveRetrySetPersistedState{producer:producer(vec![stale])}).err(),Some(RuntimeHealthError::RetryPressureStaleExecution));}

#[test]
fn conflicting_duplicate_identity_fails_closed(){let one=record("r1",ActiveRetryExecutionState::Active);let mut conflict=one.clone();conflict.retry_lineage_id="other".into();assert_eq!(ActiveRetrySetState::reopen(ActiveRetrySetPersistedState{producer:producer(vec![one,conflict])}).err(),Some(RuntimeHealthError::RetryPressureDuplicateConflict));}

#[test]
fn identical_duplicate_is_not_canonical_persisted_state(){let one=record("r1",ActiveRetryExecutionState::Active);assert_eq!(ActiveRetrySetState::reopen(ActiveRetrySetPersistedState{producer:producer(vec![one.clone(),one])}).err(),Some(RuntimeHealthError::RetryPressureDuplicateConflict));}

#[test]
fn exported_snapshot_is_canonical_and_sorted_by_identity(){let state=ActiveRetrySetState::from_producer(producer(vec![record("r2",ActiveRetryExecutionState::Active),record("r1",ActiveRetryExecutionState::Active)])).unwrap();let exported=state.export_state();assert_eq!(exported.producer.records.iter().map(|r|r.retry_execution_id.as_str()).collect::<Vec<_>>(),vec!["r1","r2"]);assert_eq!(state.bind_pressure("runtime-a","1","cfg-a").unwrap().active_retries(),2);}
