use metao_contracts::external_effect::{
    evaluate_effect_retry, EffectHistoryEntry, EffectIntent, EffectRetryDisposition,
    ExternalEffectError, ExternalEffectOutcome, IdempotencyAssurance,
};

fn intent_with_assurance(
    idempotency_key: Option<&str>,
    assurance: IdempotencyAssurance,
    evidence_ref: Option<&str>,
) -> EffectIntent {
    EffectIntent {
        effect_id: "effect-send-order-confirmation".to_string(),
        mission_id: "mission-42".to_string(),
        logical_operation: "send order confirmation email".to_string(),
        idempotency_key: idempotency_key.map(str::to_string),
        idempotency_assurance: assurance,
        idempotency_evidence_ref: evidence_ref.map(str::to_string),
        expected_postcondition: "provider records one accepted message".to_string(),
    }
}

fn intent(idempotency_key: Option<&str>) -> EffectIntent {
    match idempotency_key {
        Some(key) => intent_with_assurance(Some(key), IdempotencyAssurance::KeyDeclared, None),
        None => intent_with_assurance(None, IdempotencyAssurance::None, None),
    }
}

fn verified_intent(key: &str) -> EffectIntent {
    intent_with_assurance(
        Some(key),
        IdempotencyAssurance::EnforcementVerified,
        Some("provider-contract:idempotency-v1"),
    )
}

fn entry(
    sequence: u64,
    execution_id: &str,
    outcome: ExternalEffectOutcome,
    idempotency_key: Option<&str>,
) -> EffectHistoryEntry {
    EffectHistoryEntry {
        record_id: format!("record-{sequence}"),
        sequence,
        effect_id: "effect-send-order-confirmation".to_string(),
        idempotency_key: idempotency_key.map(str::to_string),
        execution_id: execution_id.to_string(),
        outcome,
        external_postcondition_verified: false,
    }
}

#[test]
fn applied_effect_blocks_duplicate_retry() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Applied, Some("idem-1"))];
    let result = evaluate_effect_retry(&intent(Some("idem-1")), &history).expect("decision");
    assert_eq!(result.disposition, EffectRetryDisposition::AlreadyApplied);
}

#[test]
fn declared_key_alone_does_not_make_ambiguous_retry_safe() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, Some("idem-1"))];
    let result = evaluate_effect_retry(&intent(Some("idem-1")), &history).expect("decision");
    assert_eq!(
        result.disposition,
        EffectRetryDisposition::RequireHumanOrPolicy
    );
}

#[test]
fn independently_verified_idempotency_enforcement_allows_same_effect_retry() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, Some("idem-1"))];
    let result = evaluate_effect_retry(&verified_intent("idem-1"), &history).expect("decision");
    assert_eq!(result.disposition, EffectRetryDisposition::SafeToRetry);
    assert_eq!(result.effect_id, "effect-send-order-confirmation");
}

#[test]
fn ambiguous_outcome_without_idempotency_requires_explicit_disposition() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, None)];
    let result = evaluate_effect_retry(&intent(None), &history).expect("decision");
    assert_eq!(
        result.disposition,
        EffectRetryDisposition::RequireHumanOrPolicy
    );
}

#[test]
fn failed_attempt_without_verified_idempotency_does_not_prove_effect_absent() {
    for candidate in [intent(None), intent(Some("idem-1"))] {
        let history = vec![entry(
            1,
            "exec-a",
            ExternalEffectOutcome::Failed,
            candidate.idempotency_key.as_deref(),
        )];
        let result = evaluate_effect_retry(&candidate, &history).expect("decision");
        assert_eq!(result.disposition, EffectRetryDisposition::BlockedAmbiguous);
    }
}

#[test]
fn failed_attempt_with_verified_idempotency_can_retry_same_effect() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Failed, Some("idem-1"))];
    let result = evaluate_effect_retry(&verified_intent("idem-1"), &history).expect("decision");
    assert_eq!(result.disposition, EffectRetryDisposition::SafeToRetry);
}

#[test]
fn authoritative_not_applied_outcome_allows_retry() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::NotApplied, None)];
    let result = evaluate_effect_retry(&intent(None), &history).expect("decision");
    assert_eq!(result.disposition, EffectRetryDisposition::SafeToRetry);
}

#[test]
fn failover_changes_execution_but_preserves_logical_effect_identity() {
    let history = vec![
        entry(1, "exec-runtime-a", ExternalEffectOutcome::NotApplied, Some("idem-1")),
        entry(2, "exec-runtime-b", ExternalEffectOutcome::Ambiguous, Some("idem-1")),
    ];
    let result = evaluate_effect_retry(&verified_intent("idem-1"), &history).expect("decision");
    assert_eq!(result.effect_id, "effect-send-order-confirmation");
    assert_eq!(result.authoritative_history_len, 2);
    assert_eq!(result.disposition, EffectRetryDisposition::SafeToRetry);
}

#[test]
fn independent_postcondition_proof_blocks_retry_even_when_ack_was_ambiguous() {
    let mut applied = entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, None);
    applied.external_postcondition_verified = true;
    let result = evaluate_effect_retry(&intent(None), &[applied]).expect("decision");
    assert_eq!(result.disposition, EffectRetryDisposition::AlreadyApplied);
}

#[test]
fn invalid_idempotency_assurance_combinations_fail_closed() {
    let cases = [
        intent_with_assurance(Some("idem-1"), IdempotencyAssurance::None, None),
        intent_with_assurance(None, IdempotencyAssurance::KeyDeclared, None),
        intent_with_assurance(Some("idem-1"), IdempotencyAssurance::KeyDeclared, Some("unexpected")),
        intent_with_assurance(Some("idem-1"), IdempotencyAssurance::EnforcementVerified, None),
        intent_with_assurance(None, IdempotencyAssurance::EnforcementVerified, Some("proof")),
    ];

    for candidate in cases {
        assert_eq!(
            candidate.validate(),
            Err(ExternalEffectError::InvalidIdempotencyAssurance)
        );
    }
}

#[test]
fn omission_of_authoritative_history_fails_closed() {
    assert_eq!(
        evaluate_effect_retry(&verified_intent("idem-1"), &[]),
        Err(ExternalEffectError::MissingAuthoritativeHistory)
    );
}

#[test]
fn history_sequence_gap_fails_closed() {
    let history = vec![entry(2, "exec-a", ExternalEffectOutcome::NotApplied, Some("idem-1"))];
    assert_eq!(
        evaluate_effect_retry(&verified_intent("idem-1"), &history),
        Err(ExternalEffectError::HistorySequenceGap {
            expected: 1,
            actual: 2,
        })
    );
}

#[test]
fn idempotency_key_mutation_is_rejected() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, Some("different"))];
    assert_eq!(
        evaluate_effect_retry(&verified_intent("idem-1"), &history),
        Err(ExternalEffectError::IdempotencyKeyMismatch)
    );
}

#[test]
fn logical_effect_identity_mutation_is_rejected() {
    let mut history = vec![entry(1, "exec-a", ExternalEffectOutcome::NotApplied, None)];
    history[0].effect_id = "different-effect".to_string();
    assert_eq!(
        evaluate_effect_retry(&intent(None), &history),
        Err(ExternalEffectError::EffectBindingMismatch)
    );
}

#[test]
fn serialization_contains_no_exactly_once_or_acceptance_authority() {
    let history = vec![entry(1, "exec-a", ExternalEffectOutcome::Ambiguous, Some("idem-1"))];
    let result = evaluate_effect_retry(&verified_intent("idem-1"), &history).expect("decision");
    let encoded = serde_json::to_string(&result).expect("serialize");
    let decoded: metao_contracts::external_effect::EffectRetryDecision =
        serde_json::from_str(&encoded).expect("deserialize");
    assert_eq!(decoded, result);
    for forbidden in [
        "EXACTLY_ONCE",
        "AcceptanceDecision",
        "PolicyEffect",
        "dispatch",
        "provider_sdk",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
