use metao_contracts::{
    AcceptanceBudget, AcceptanceContext, AcceptanceDecision, ContractError, ExecutionId,
    ExecutionStatus, MissionId, RetryHistoryKind, RetryHistoryPort, RetryHistoryRecord,
    VerificationAttemptId, VerificationAttemptStarted, VerificationRequestId, VerificationUsage,
    VerifierId,
};
use metao_kernel::{
    canonical_acceptance, validate_retry_history_projection, VerificationAccountingAuthority,
};

fn budget(verifier_attempt_limit: u64) -> AcceptanceBudget {
    AcceptanceBudget::new(10.0, 1_000, 60.0, verifier_attempt_limit).expect("valid budget")
}

fn authority(verifier_attempt_limit: u64) -> VerificationAccountingAuthority {
    VerificationAccountingAuthority::new(budget(verifier_attempt_limit))
}

fn mission() -> MissionId {
    MissionId::new("mission-1").expect("valid mission")
}

fn execution() -> ExecutionId {
    ExecutionId::new("execution-1").expect("valid execution")
}

fn request_id() -> VerificationRequestId {
    VerificationRequestId::new("request-1").expect("valid request")
}

fn attempt_id(value: &str) -> VerificationAttemptId {
    VerificationAttemptId::new(value).expect("valid attempt")
}

fn verifier_id() -> VerifierId {
    VerifierId::new("verifier-1").expect("valid verifier")
}

fn started(
    attempt_id: &VerificationAttemptId,
    started_at_epoch: f64,
) -> VerificationAttemptStarted {
    VerificationAttemptStarted {
        request_id: request_id(),
        attempt_id: attempt_id.clone(),
        mission_id: mission(),
        execution_id: execution(),
        verifier_id: verifier_id(),
        verifier_version: "1.0".into(),
        started_at_epoch,
    }
}

fn usage(attempt_id: &VerificationAttemptId, money: f64, tokens: u64) -> VerificationUsage {
    VerificationUsage {
        attempt_id: attempt_id.clone(),
        money: Some(money),
        tokens: Some(tokens),
        wall_time_s: Some(1.0),
        verifier_attempts: Some(1),
    }
}

fn recovery_record(
    record_id: &str,
    attempt_id: &VerificationAttemptId,
    from_attempt_id: &VerificationAttemptId,
    sequence: u64,
) -> RetryHistoryRecord {
    RetryHistoryRecord {
        record_id: record_id.into(),
        mission_id: mission(),
        execution_id: execution(),
        attempt_id: attempt_id.clone(),
        sequence,
        kind: RetryHistoryKind::RecoveryObserved,
        attempt_started: None,
        recovery_from_attempt_id: Some(from_attempt_id.clone()),
        recovery_outcome: Some(ExecutionStatus::Failed),
        usage: None,
    }
}

fn authoritative_history() -> (VerificationAccountingAuthority, Vec<RetryHistoryRecord>) {
    let authority = authority(10);
    let attempt1 = attempt_id("attempt-1");
    let attempt2 = attempt_id("attempt-2");
    let usage1 = usage(&attempt1, 2.0, 3);
    let usage2 = usage(&attempt2, 4.0, 5);

    authority.start_attempt(started(&attempt1, 10.0)).unwrap();
    authority.record_usage(usage1.clone()).unwrap();
    authority.apply_usage(&usage1).unwrap();
    RetryHistoryPort::append(
        &authority,
        recovery_record("recovery-1", &attempt2, &attempt1, 2),
    )
    .unwrap();
    authority.start_attempt(started(&attempt2, 20.0)).unwrap();
    authority.record_usage(usage2.clone()).unwrap();
    authority.apply_usage(&usage2).unwrap();

    let history = authority
        .retry_history(&mission(), &execution())
        .expect("authoritative history");
    (authority, history)
}

#[test]
fn full_authoritative_history_consumed() {
    let (authority, history) = authoritative_history();
    assert!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &history).is_ok()
    );
}

#[test]
fn caller_shorter_history_cannot_reopen_acceptance() {
    let (authority, history) = authoritative_history();
    let caller_history = history[..history.len() - 1].to_vec();

    assert_eq!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &caller_history),
        Err(ContractError::RetryHistoryProjectionMismatch)
    );
}

#[test]
fn caller_omitted_prior_attempt_cannot_override_ledger() {
    let (authority, history) = authoritative_history();
    let caller_history = history[2..].to_vec();

    assert_eq!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &caller_history),
        Err(ContractError::RetryHistoryProjectionMismatch)
    );
}

#[test]
fn caller_reset_counters_cannot_override_ledger() {
    let (authority, history) = authoritative_history();
    let mut caller_history = history.clone();
    for (index, record) in caller_history.iter_mut().enumerate() {
        if index >= 2 {
            record.sequence = (index - 2) as u64;
        }
    }

    assert_eq!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &caller_history),
        Err(ContractError::RetryHistorySequenceGap {
            expected: 2,
            actual: 0,
        })
    );
}

#[test]
fn cumulative_attempts_preserved_across_reload_reconstruction() {
    let (source_authority, history) = authoritative_history();
    let rebuilt = authority(10);

    rebuilt.replay_history(&history).unwrap();

    assert_eq!(
        rebuilt.retry_history(&mission(), &execution()).unwrap(),
        history
    );
    assert_eq!(
        rebuilt
            .attempt_started(&attempt_id("attempt-1"))
            .unwrap()
            .started_at_epoch,
        10.0
    );
    assert_eq!(
        rebuilt
            .attempt_started(&attempt_id("attempt-2"))
            .unwrap()
            .started_at_epoch,
        20.0
    );
    assert_eq!(
        rebuilt.budget().money_used,
        source_authority.budget().money_used
    );
    assert_eq!(
        rebuilt.budget().verifier_attempts_used,
        source_authority.budget().verifier_attempts_used
    );
}

#[test]
fn cumulative_factual_cost_usage_preserved_where_supported() {
    let (_source_authority, history) = authoritative_history();
    let rebuilt = authority(10);

    rebuilt.replay_history(&history).unwrap();

    assert_eq!(
        rebuilt.usage(&attempt_id("attempt-1")).unwrap().money,
        Some(2.0)
    );
    assert_eq!(
        rebuilt.usage(&attempt_id("attempt-2")).unwrap().money,
        Some(4.0)
    );
    assert_eq!(rebuilt.budget().money_used, 6.0);
    assert_eq!(rebuilt.budget().tokens_used, 8);
}

#[test]
fn over_limit_attempt_remains_recorded() {
    let authority = authority(1);
    let attempt1 = attempt_id("attempt-1");
    let attempt2 = attempt_id("attempt-2");
    let usage1 = usage(&attempt1, 1.0, 1);
    let usage2 = usage(&attempt2, 1.0, 1);

    authority.start_attempt(started(&attempt1, 10.0)).unwrap();
    authority.record_usage(usage1.clone()).unwrap();
    authority.apply_usage(&usage1).unwrap();
    authority.start_attempt(started(&attempt2, 20.0)).unwrap();
    authority.record_usage(usage2.clone()).unwrap();
    assert_eq!(
        authority.apply_usage(&usage2),
        Err(ContractError::BudgetExhausted)
    );
    let history = authority.retry_history(&mission(), &execution()).unwrap();
    assert_eq!(history.len(), 4);
    assert_eq!(authority.usage(&attempt2).unwrap().money, Some(1.0));
}

#[test]
fn over_limit_factual_history_blocks_continuation_as_required() {
    let source_authority = authority(1);
    let attempt1 = attempt_id("attempt-1");
    let attempt2 = attempt_id("attempt-2");
    let usage1 = usage(&attempt1, 1.0, 1);
    let usage2 = usage(&attempt2, 1.0, 1);

    source_authority
        .start_attempt(started(&attempt1, 10.0))
        .unwrap();
    source_authority.record_usage(usage1.clone()).unwrap();
    source_authority.apply_usage(&usage1).unwrap();
    source_authority
        .start_attempt(started(&attempt2, 20.0))
        .unwrap();
    source_authority.record_usage(usage2.clone()).unwrap();
    let original_error = source_authority.apply_usage(&usage2);
    assert_eq!(original_error, Err(ContractError::BudgetExhausted));

    let history = source_authority
        .retry_history(&mission(), &execution())
        .unwrap();
    let rebuilt = authority(1);
    assert_eq!(
        rebuilt.replay_history(&history),
        Err(ContractError::BudgetExhausted)
    );
    assert_eq!(
        rebuilt.retry_history(&mission(), &execution()).unwrap(),
        history
    );
}

#[test]
fn duplicate_record_id_fails_closed() {
    let authority = authority(10);
    let attempt1 = attempt_id("attempt-1");
    let record = recovery_record("recovery-1", &attempt1, &attempt1, 0);
    let mut duplicate = record.clone();
    duplicate.sequence = 1;

    RetryHistoryPort::append(&authority, record.clone()).unwrap();
    assert_eq!(
        RetryHistoryPort::append(&authority, duplicate),
        Err(ContractError::RetryHistoryDuplicateRecord(
            "recovery-1".into()
        ))
    );
}

#[test]
fn duplicate_attempt_identity_fails_closed() {
    let authority = authority(10);
    let attempt1 = attempt_id("attempt-1");

    authority.start_attempt(started(&attempt1, 10.0)).unwrap();
    assert_eq!(
        authority.start_attempt(started(&attempt1, 11.0)),
        Err(ContractError::DuplicateVerificationAttempt(
            "attempt-1".into()
        ))
    );
}

#[test]
fn sequence_gap_fails_closed() {
    let authority = authority(10);
    let attempt1 = attempt_id("attempt-1");
    let record = RetryHistoryRecord {
        record_id: "recovery-1".into(),
        mission_id: mission(),
        execution_id: execution(),
        attempt_id: attempt1.clone(),
        sequence: 1,
        kind: RetryHistoryKind::RecoveryObserved,
        attempt_started: None,
        recovery_from_attempt_id: Some(attempt1.clone()),
        recovery_outcome: Some(ExecutionStatus::Failed),
        usage: None,
    };

    assert_eq!(
        RetryHistoryPort::append(&authority, record),
        Err(ContractError::RetryHistorySequenceGap {
            expected: 0,
            actual: 1,
        })
    );
}

#[test]
fn mission_binding_mismatch_fails_closed() {
    let (authority, history) = authoritative_history();
    let mut caller_history = history.clone();
    caller_history[0].mission_id = MissionId::new("mission-2").expect("valid mission");

    assert_eq!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &caller_history),
        Err(ContractError::RetryHistoryBindingMismatch)
    );
}

#[test]
fn execution_binding_mismatch_fails_closed() {
    let (authority, history) = authoritative_history();
    let mut caller_history = history.clone();
    caller_history[0].execution_id = ExecutionId::new("execution-2").expect("valid execution");

    assert_eq!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &caller_history),
        Err(ContractError::RetryHistoryBindingMismatch)
    );
}

#[test]
fn missing_authoritative_history_source_fails_closed() {
    struct MissingHistoryPort;

    impl RetryHistoryPort for MissingHistoryPort {
        fn append(&self, _record: RetryHistoryRecord) -> Result<(), ContractError> {
            Ok(())
        }

        fn history(
            &self,
            _mission_id: &MissionId,
            _execution_id: &ExecutionId,
        ) -> Option<Vec<RetryHistoryRecord>> {
            None
        }
    }

    let caller_history = vec![];
    assert_eq!(
        validate_retry_history_projection(
            &MissingHistoryPort,
            &mission(),
            &execution(),
            &caller_history,
        ),
        Err(ContractError::MissingRetryHistorySource)
    );
}

#[test]
fn retry_history_cannot_mint_metao_accepted() {
    let (authority, history) = authoritative_history();
    assert!(
        validate_retry_history_projection(&authority, &mission(), &execution(), &history).is_ok()
    );

    let context = AcceptanceContext {
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "vc-1".into(),
        policy_bundle_id: "policy-1".into(),
        required_obligations: vec!["obligation-1".into()],
        trusted_verifiers: vec![],
        trusted_provenance_roots: vec![],
        authorized_authorities: vec![],
    };
    let acceptance = canonical_acceptance(&context, &[], 0.0);
    assert_eq!(acceptance.decision, AcceptanceDecision::NotDone);
}
