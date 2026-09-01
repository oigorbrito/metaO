#[path = "../src/executor_capacity.rs"]
mod executor_capacity;

use executor_capacity::*;
use std::collections::BTreeSet;

fn caps(items: &[&str]) -> BTreeSet<String> {
    items.iter().map(|item| (*item).to_string()).collect()
}

fn executor(
    id: &str,
    provider: &str,
    region: Option<&str>,
    qualification: QualificationState,
    capacity: CapacityState,
    paid: bool,
    cost: u64,
    reliability: u16,
) -> ExecutorRecord {
    ExecutorRecord {
        executor_id: id.to_string(),
        provider: provider.to_string(),
        country_or_region: region.map(str::to_string),
        capabilities: caps(&["code", "git", "tests"]),
        qualification,
        capacity,
        recovery: None,
        paid,
        estimated_cost_microunits: cost,
        reliability_score_basis_points: reliability,
    }
}

fn policy() -> ExecutionPolicy {
    ExecutionPolicy {
        required_capabilities: caps(&["code", "git"]),
        paid_fallback_allowed: false,
        max_paid_cost_microunits: 0,
        prefer_free: true,
        max_wait_for_free_s: 300,
    }
}

#[test]
fn transient_rate_limit_uses_evidenced_retry_window() {
    let mut record = executor(
        "free-a",
        "provider-a",
        None,
        QualificationState::Qualified,
        CapacityState::TemporarilyRateLimited,
        false,
        0,
        9000,
    );
    record.recovery = Some(RecoveryObservation {
        recoverable: true,
        available_at_epoch_s: Some(1_060),
        evidence_basis: RecoveryEvidenceBasis::ProviderApi,
        evidence_ref: "retry-after:60".to_string(),
    });

    assert_eq!(
        supervision_decision(&record, 1_000).unwrap(),
        SupervisionDecision::RetryAfter { delay_s: 60 }
    );
}

#[test]
fn quota_exhaustion_does_not_fail_task_when_free_alternative_exists() {
    let exhausted = executor(
        "free-a",
        "provider-a",
        None,
        QualificationState::Qualified,
        CapacityState::DailyQuotaExhausted,
        false,
        0,
        9500,
    );
    let available = executor(
        "free-b",
        "provider-b",
        None,
        QualificationState::Qualified,
        CapacityState::Available,
        false,
        0,
        8500,
    );

    let selected = select_executor(&[exhausted, available], &policy())
        .unwrap()
        .unwrap();
    assert_eq!(selected.executor_id, "free-b");
}

#[test]
fn paid_fallback_requires_explicit_budget_authority() {
    let paid = executor(
        "paid-a",
        "provider-a",
        None,
        QualificationState::Qualified,
        CapacityState::Available,
        true,
        500_000,
        9900,
    );

    assert!(select_executor(std::slice::from_ref(&paid), &policy())
        .unwrap()
        .is_none());

    let mut allowed = policy();
    allowed.paid_fallback_allowed = true;
    allowed.max_paid_cost_microunits = 600_000;
    assert_eq!(
        select_executor(std::slice::from_ref(&paid), &allowed)
            .unwrap()
            .unwrap()
            .executor_id,
        "paid-a"
    );
}

#[test]
fn unknown_capacity_fails_closed() {
    let record = executor(
        "unknown-a",
        "provider-a",
        None,
        QualificationState::Qualified,
        CapacityState::Unknown,
        false,
        0,
        9000,
    );
    assert_eq!(
        supervision_decision(&record, 1_000).unwrap(),
        SupervisionDecision::Block
    );
    assert!(select_executor(&[record], &policy()).unwrap().is_none());
}

#[test]
fn discovered_or_unqualified_executor_cannot_receive_project_data() {
    for qualification in [
        QualificationState::Discovered,
        QualificationState::Unqualified,
        QualificationState::Blocked,
    ] {
        let record = executor(
            "candidate",
            "provider-x",
            Some("region-x"),
            qualification,
            CapacityState::Available,
            false,
            0,
            9000,
        );
        assert!(!record.can_receive_project_data());
        assert!(select_executor(&[record], &policy()).unwrap().is_none());
    }
}

#[test]
fn checkpoint_handoff_rejects_head_mismatch() {
    let mismatch = VerifiedCheckpoint {
        task_id: "TASK-1".to_string(),
        branch: "metao/task-1".to_string(),
        expected_head: "abc".to_string(),
        observed_head: "def".to_string(),
        evidence_ref: "git-observation-1".to_string(),
    };
    assert_eq!(
        authorize_handoff(&mismatch),
        Err(ExecutorCapacityError::InvalidCheckpoint)
    );
}

#[test]
fn executor_completion_never_implies_acceptance() {
    assert!(!executor_completion_implies_acceptance(true));
    assert!(!executor_completion_implies_acceptance(false));
}

#[test]
fn provider_or_country_identity_does_not_change_selection_authority() {
    let a = executor(
        "executor-a",
        "provider-cn",
        Some("CN"),
        QualificationState::Qualified,
        CapacityState::Available,
        false,
        0,
        9000,
    );
    let b = executor(
        "executor-b",
        "provider-us",
        Some("US"),
        QualificationState::Qualified,
        CapacityState::Available,
        false,
        0,
        9000,
    );

    let selected = select_executor(&[b, a], &policy()).unwrap().unwrap();
    assert_eq!(selected.executor_id, "executor-a");
}

#[test]
fn higher_reliability_wins_after_hard_filters() {
    let lower = executor(
        "lower",
        "provider-a",
        None,
        QualificationState::Qualified,
        CapacityState::Available,
        false,
        0,
        8100,
    );
    let higher = executor(
        "higher",
        "provider-b",
        None,
        QualificationState::Qualified,
        CapacityState::Available,
        false,
        0,
        9300,
    );

    assert_eq!(
        select_executor(&[lower, higher], &policy())
            .unwrap()
            .unwrap()
            .executor_id,
        "higher"
    );
}
