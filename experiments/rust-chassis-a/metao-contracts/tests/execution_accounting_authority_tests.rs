use metao_contracts::execution_governance::{ExecutionAccountingAuthority,ExecutionAccountingError,ExecutionAccountingOperation,ExecutionBudget,ExecutionObservedUsage,ExecutionSettlementDecision,ExecutionUsage,ExecutionUsageEvidenceBasis};
use metao_contracts::{ExecutionId,MissionId};
use std::sync::Arc;
use std::thread;

fn budget()->ExecutionBudget{ExecutionBudget{money_limit:10.0,token_limit:1000,wall_time_limit_s:100.0,attempt_limit:5,money_used:0.0,tokens_used:0,wall_time_used_s:0.0,attempts_used:0}}
fn op(id:&str,money:f64)->ExecutionAccountingOperation{ExecutionAccountingOperation{operation_id:id.into(),mission_id:MissionId::new("m485").unwrap(),execution_id:ExecutionId::new("e485").unwrap(),execution_lineage_id:"lineage-485".into(),observed:ExecutionObservedUsage{usage:ExecutionUsage{money,tokens:100,wall_time_s:10.0,attempts:1},evidence_basis:ExecutionUsageEvidenceBasis::AdapterVerified,evidence_ref:"evidence://usage/485".into()}}}

#[test]
fn identical_replay_is_idempotent(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();assert_eq!(a.settle(1,op("acct-1",1.0)),Ok(ExecutionSettlementDecision::Applied));assert_eq!(a.settle(1,op("acct-1",1.0)),Ok(ExecutionSettlementDecision::Idempotent));let s=a.snapshot();assert_eq!(s.budget.money_used,1.0);assert_eq!(s.budget.attempts_used,1);assert_eq!(s.settlement_count,1);}
#[test]
fn conflicting_duplicate_is_rejected(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.settle(1,op("acct-1",1.0)).unwrap();assert_eq!(a.settle(2,op("acct-1",2.0)),Err(ExecutionAccountingError::Conflict));}
#[test]
fn stale_writer_is_rejected(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();a.settle(1,op("acct-1",1.0)).unwrap();assert_eq!(a.settle(1,op("acct-2",1.0)),Err(ExecutionAccountingError::StaleVersion));}
#[test]
fn concurrent_duplicate_settlement_charges_once(){let a=Arc::new(ExecutionAccountingAuthority::new(budget()).unwrap());let mut hs=vec![];for _ in 0..8{let x=a.clone();hs.push(thread::spawn(move||x.settle(1,op("acct-concurrent",1.0)).unwrap()));}for h in hs{let _=h.join().unwrap();}let s=a.snapshot();assert_eq!(s.budget.money_used,1.0);assert_eq!(s.budget.attempts_used,1);assert_eq!(s.settlement_count,1);}
#[test]
fn factual_overage_is_preserved_and_blocks_future_capacity(){let mut b=budget();b.money_limit=1.0;let a=ExecutionAccountingAuthority::new(b).unwrap();a.settle(1,op("acct-over",2.0)).unwrap();let s=a.snapshot();assert_eq!(s.budget.money_used,2.0);assert!(!s.budget.has_pre_runtime_capacity(&ExecutionUsage{money:0.0,tokens:0,wall_time_s:0.0,attempts:0}));}
#[test]
fn evidence_ref_is_not_accounting_identity(){let a=ExecutionAccountingAuthority::new(budget()).unwrap();let mut one=op("acct-a",1.0);let mut two=op("acct-b",1.0);one.observed.evidence_ref="same-ref".into();two.observed.evidence_ref="same-ref".into();a.settle(1,one).unwrap();a.settle(2,two).unwrap();assert_eq!(a.snapshot().settlement_count,2);}
