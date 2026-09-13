use metao_contracts::execution_governance::{ExecutionAccountingAuthority,ExecutionAccountingError,ExecutionAccountingOperation,ExecutionBudget,ExecutionBudgetReservation,ExecutionObservedUsage,ExecutionSettlementDecision,ExecutionUsage,ExecutionUsageEvidenceBasis,ReservationDecision,ReservationStatus};
use metao_contracts::{ExecutionId,MissionId};
use std::sync::Arc;
use std::thread;

fn budget()->ExecutionBudget{ExecutionBudget{money_limit:2.0,token_limit:200,wall_time_limit_s:20.0,attempt_limit:1,money_used:0.0,tokens_used:0,wall_time_used_s:0.0,attempts_used:0}}
fn reservation(id:&str,execution:&str)->ExecutionBudgetReservation{ExecutionBudgetReservation{reservation_id:id.into(),mission_id:MissionId::new("m486").unwrap(),execution_id:ExecutionId::new(execution).unwrap(),action:"retry_execution".into(),requested:ExecutionUsage{money:1.0,tokens:100,wall_time_s:10.0,attempts:1},status:ReservationStatus::Active}}
fn op(id:&str,execution:&str)->ExecutionAccountingOperation{ExecutionAccountingOperation{operation_id:id.into(),mission_id:MissionId::new("m486").unwrap(),execution_id:ExecutionId::new(execution).unwrap(),execution_lineage_id:"lineage-486".into(),observed:ExecutionObservedUsage{usage:ExecutionUsage{money:1.0,tokens:100,wall_time_s:10.0,attempts:1},evidence_basis:ExecutionUsageEvidenceBasis::AdapterVerified,evidence_ref:"evidence://486".into()}}}

#[test]
fn concurrent_attempt_capacity_allows_at_most_one_reservation(){let a=Arc::new(ExecutionAccountingAuthority::new(budget()).unwrap());let mut hs=vec![];for i in 0..8{let x=a.clone();hs.push(thread::spawn(move||{let s=x.snapshot();x.reserve(s.version,reservation(&format!("r-{i}"),&format!("e-{i}")))}));}let mut ok=0;for h in hs{if matches!(h.join().unwrap(),Ok(ReservationDecision::Reserved)){ok+=1;}}assert_eq!(ok,1);let s=a.snapshot();assert_eq!(s.active_reservation_count,1);assert_eq!(s.reserved.attempts,1);}

#[test]
fn duplicate_same_reservation_is_idempotent(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();let r=reservation("r1","e1");assert_eq!(a.reserve(1,r.clone()),Ok(ReservationDecision::Reserved));assert_eq!(a.reserve(1,r),Ok(ReservationDecision::Idempotent));assert_eq!(a.snapshot().active_reservation_count,1);}

#[test]
fn conflicting_duplicate_reservation_is_rejected(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();let mut other=reservation("r1","e1");other.requested.money=0.5;assert_eq!(a.reserve(2,other),Err(ExecutionAccountingError::Conflict));}

#[test]
fn stale_reservation_version_fails_closed(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();assert_eq!(a.reserve(1,reservation("r2","e2")),Err(ExecutionAccountingError::StaleVersion));}

#[test]
fn release_is_exactly_once_and_restores_capacity(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();assert_eq!(a.release(2,"r1"),Ok(ReservationDecision::Released));assert_eq!(a.release(2,"r1"),Ok(ReservationDecision::AlreadyReleased));let s=a.snapshot();assert_eq!(s.active_reservation_count,0);assert_eq!(s.reserved.attempts,0);assert_eq!(a.reserve(s.version,reservation("r2","e2")),Ok(ReservationDecision::Reserved));}

#[test]
fn reserved_execution_settlement_consumes_reservation_once(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();assert_eq!(a.settle_reserved(2,"r1",op("acct1","e1")),Ok(ExecutionSettlementDecision::Applied));let s=a.snapshot();assert_eq!(s.active_reservation_count,0);assert_eq!(s.budget.attempts_used,1);assert_eq!(s.settlement_count,1);assert_eq!(a.settle_reserved(2,"r1",op("acct1","e1")),Ok(ExecutionSettlementDecision::Idempotent));assert_eq!(a.snapshot().budget.attempts_used,1);}

#[test]
fn reservation_binding_mismatch_cannot_settle_other_execution(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();assert_eq!(a.settle_reserved(2,"r1",op("acct1","e2")),Err(ExecutionAccountingError::ReservationBindingMismatch));assert_eq!(a.snapshot().active_reservation_count,1);}

#[test]
fn active_reservation_blocks_snapshot_oversubscription(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.reserve(1,reservation("r1","e1")).unwrap();let s=a.snapshot();assert_eq!(s.reserved.money,1.0);assert_eq!(s.reserved.tokens,100);assert_eq!(s.reserved.attempts,1);assert_eq!(a.reserve(s.version,reservation("r2","e2")),Err(ExecutionAccountingError::CapacityExceeded));}
