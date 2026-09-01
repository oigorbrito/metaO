use metao_contracts::failure_causality::{
    evaluate_retry_eligibility, FactualExecutionOutcome, FailureCausalityFacts, FailureClass,
    FailureClassificationBasis, RecoveryStatus, RetryEligibility,
};
use proptest::prelude::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Event {
    Timeout,
    RecoveryComplete,
    Retry,
    Failover,
    OldRuntimeDone,
    FreshEvidence,
    Accept,
    OmitHistoryAttack,
}

#[derive(Clone, Debug)]
struct LifecycleModel {
    generation: u64,
    attempt: u64,
    max_attempts: u64,
    recovery_complete: bool,
    evidence_generation: Option<u64>,
    accepted: bool,
    retry_history_len: u64,
}

impl LifecycleModel {
    fn new() -> Self {
        Self {
            generation: 1,
            attempt: 1,
            max_attempts: 4,
            recovery_complete: false,
            evidence_generation: None,
            accepted: false,
            retry_history_len: 0,
        }
    }

    fn apply(&mut self, event: Event) {
        if self.accepted {
            // Terminal acceptance is not reopened by later runtime observations.
            return;
        }

        match event {
            Event::Timeout => {
                self.recovery_complete = false;
                self.evidence_generation = None;
            }
            Event::RecoveryComplete => {
                self.recovery_complete = true;
            }
            Event::Retry => {
                let facts = FailureCausalityFacts {
                    original_outcome: FactualExecutionOutcome::Timeout,
                    failure_class: FailureClass::Transient,
                    failure_class_basis: FailureClassificationBasis::AuthoritativeObservation,
                    failure_class_evidence_ref: Some("stateful-timeout".to_string()),
                    recovery_required: true,
                    recovery_status: if self.recovery_complete {
                        RecoveryStatus::Complete
                    } else {
                        RecoveryStatus::Incomplete
                    },
                    current_attempt: self.attempt,
                    max_attempts: self.max_attempts,
                    policy_blocked: false,
                    risk_blocked: false,
                    budget_blocked: false,
                };
                let projection = evaluate_retry_eligibility(&facts);
                if projection.eligibility == RetryEligibility::Eligible {
                    self.attempt = projection.next_attempt.expect("eligible retry has next attempt");
                    self.retry_history_len += 1;
                    self.recovery_complete = false;
                    self.evidence_generation = None;
                }
            }
            Event::Failover => {
                self.generation += 1;
                self.attempt = 1;
                self.recovery_complete = false;
                self.evidence_generation = None;
            }
            Event::OldRuntimeDone => {
                // Runtime completion is a factual observation, never acceptance authority.
            }
            Event::FreshEvidence => {
                self.evidence_generation = Some(self.generation);
            }
            Event::Accept => {
                self.accepted = self.evidence_generation == Some(self.generation);
            }
            Event::OmitHistoryAttack => {
                // Caller omission cannot shrink authoritative retry history.
            }
        }
    }
}

fn event_from_byte(value: u8) -> Event {
    match value % 8 {
        0 => Event::Timeout,
        1 => Event::RecoveryComplete,
        2 => Event::Retry,
        3 => Event::Failover,
        4 => Event::OldRuntimeDone,
        5 => Event::FreshEvidence,
        6 => Event::Accept,
        _ => Event::OmitHistoryAttack,
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(256))]

    #[test]
    fn generated_lifecycle_sequences_preserve_authority_invariants(
        raw_events in prop::collection::vec(any::<u8>(), 1..96)
    ) {
        let mut model = LifecycleModel::new();
        let mut previous_generation = model.generation;
        let mut previous_retry_history = model.retry_history_len;

        for raw in raw_events {
            let event = event_from_byte(raw);
            let was_accepted = model.accepted;
            let evidence_before = model.evidence_generation;
            let generation_before = model.generation;
            let attempt_before = model.attempt;
            let recovery_before = model.recovery_complete;

            model.apply(event);

            prop_assert!(model.generation >= previous_generation);
            prop_assert!(model.retry_history_len >= previous_retry_history);

            if was_accepted {
                prop_assert!(model.accepted);
                prop_assert_eq!(model.generation, generation_before);
                prop_assert_eq!(model.evidence_generation, evidence_before);
            }

            if event == Event::OldRuntimeDone && !was_accepted {
                prop_assert!(!model.accepted);
            }

            if event == Event::Retry && !recovery_before {
                prop_assert_eq!(model.attempt, attempt_before);
            }

            if model.accepted {
                prop_assert_eq!(model.evidence_generation, Some(model.generation));
            }

            previous_generation = model.generation;
            previous_retry_history = model.retry_history_len;
        }
    }
}

#[test]
fn regression_incomplete_recovery_late_done_and_omission_cannot_accept() {
    let mut model = LifecycleModel::new();

    model.apply(Event::Timeout);
    let attempt_before = model.attempt;
    model.apply(Event::Retry);
    assert_eq!(model.attempt, attempt_before, "incomplete recovery must block retry");

    model.apply(Event::OldRuntimeDone);
    assert!(!model.accepted, "runtime DONE must not mint acceptance");

    let history_before = model.retry_history_len;
    model.apply(Event::OmitHistoryAttack);
    assert_eq!(model.retry_history_len, history_before, "omission must not erase retry history");

    model.apply(Event::RecoveryComplete);
    model.apply(Event::Retry);
    assert_eq!(model.retry_history_len, history_before + 1);

    model.apply(Event::Failover);
    let current_generation = model.generation;
    model.apply(Event::Accept);
    assert!(!model.accepted, "failover without current-generation evidence cannot accept");

    model.apply(Event::FreshEvidence);
    model.apply(Event::Accept);
    assert!(model.accepted);
    assert_eq!(model.evidence_generation, Some(current_generation));
}
