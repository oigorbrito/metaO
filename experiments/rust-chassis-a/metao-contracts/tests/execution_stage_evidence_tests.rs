use metao_contracts::execution_stage_evidence::{
    project_execution_stages, ExecutionStageEvidence, ExecutionStageEvidenceBasis,
    ExecutionStageEvidenceError, ExecutionStageStatus,
};

fn stage(
    id: &str,
    sequence: u64,
    requested: bool,
    executed: bool,
    status: ExecutionStageStatus,
) -> ExecutionStageEvidence {
    let conclusive = matches!(
        status,
        ExecutionStageStatus::Pass | ExecutionStageStatus::Failed
    );
    ExecutionStageEvidence {
        stage_id: id.to_string(),
        sequence,
        requested,
        executed,
        status,
        reason: format!("factual stage result for {id}"),
        evidence_basis: if conclusive {
            ExecutionStageEvidenceBasis::AdapterVerified
        } else {
            ExecutionStageEvidenceBasis::Unknown
        },
        evidence_ref: conclusive.then(|| format!("stage-evidence:{id}:{sequence}")),
    }
}

#[test]
fn skipped_and_not_requested_are_distinct_facts() {
    let report = project_execution_stages(&[
        stage("policy", 1, true, true, ExecutionStageStatus::Pass),
        stage("runtime", 2, true, false, ExecutionStageStatus::Skipped),
        stage(
            "optional-export",
            3,
            false,
            false,
            ExecutionStageStatus::NotRequested,
        ),
    ])
    .expect("report");
    assert_eq!(report.skipped, 1);
    assert_eq!(report.not_requested, 1);
    assert_ne!(report.stages[1].status, report.stages[2].status);
}

#[test]
fn unexecuted_stage_cannot_claim_pass() {
    let invalid = stage("runtime", 1, true, false, ExecutionStageStatus::Pass);
    assert_eq!(
        project_execution_stages(&[invalid]),
        Err(ExecutionStageEvidenceError::InvalidExecutionClaim)
    );
}

#[test]
fn executed_conclusive_stage_requires_verified_origin_and_evidence() {
    for basis in [
        ExecutionStageEvidenceBasis::SelfReported,
        ExecutionStageEvidenceBasis::Unknown,
    ] {
        let mut invalid = stage("runtime", 1, true, true, ExecutionStageStatus::Pass);
        invalid.evidence_basis = basis;
        assert_eq!(
            project_execution_stages(&[invalid]),
            Err(ExecutionStageEvidenceError::InvalidEvidenceBasis)
        );
    }

    for evidence_ref in [None, Some(String::new()), Some("   ".to_string())] {
        let mut invalid = stage("runtime", 1, true, true, ExecutionStageStatus::Failed);
        invalid.evidence_ref = evidence_ref;
        assert_eq!(
            project_execution_stages(&[invalid]),
            Err(ExecutionStageEvidenceError::BlankEvidenceRef)
        );
    }
}

#[test]
fn independent_observation_can_support_conclusive_stage() {
    let mut value = stage("runtime", 1, true, true, ExecutionStageStatus::Pass);
    value.evidence_basis = ExecutionStageEvidenceBasis::IndependentObservation;
    assert_eq!(
        project_execution_stages(&[value]).expect("report").passed,
        1
    );
}

#[test]
fn not_requested_stage_cannot_claim_execution() {
    let invalid = stage("export", 1, false, true, ExecutionStageStatus::NotRequested);
    assert_eq!(
        project_execution_stages(&[invalid]),
        Err(ExecutionStageEvidenceError::InvalidExecutionClaim)
    );
}

#[test]
fn duplicate_stage_id_fails_closed() {
    let result = project_execution_stages(&[
        stage("runtime", 1, true, true, ExecutionStageStatus::Pass),
        stage("runtime", 2, true, true, ExecutionStageStatus::Failed),
    ]);
    assert_eq!(
        result,
        Err(ExecutionStageEvidenceError::DuplicateStage(
            "runtime".to_string()
        ))
    );
}

#[test]
fn sequence_gap_fails_closed() {
    let result = project_execution_stages(&[
        stage("policy", 1, true, true, ExecutionStageStatus::Pass),
        stage("runtime", 3, true, true, ExecutionStageStatus::Pass),
    ]);
    assert_eq!(
        result,
        Err(ExecutionStageEvidenceError::SequenceGap {
            expected: 2,
            actual: 3
        })
    );
}

#[test]
fn sequence_must_start_at_one() {
    let result =
        project_execution_stages(&[stage("policy", 0, true, true, ExecutionStageStatus::Pass)]);
    assert_eq!(
        result,
        Err(ExecutionStageEvidenceError::SequenceGap {
            expected: 1,
            actual: 0
        })
    );
}

#[test]
fn duplicate_sequence_fails_closed() {
    let result = project_execution_stages(&[
        stage("policy", 1, true, true, ExecutionStageStatus::Pass),
        stage("runtime", 1, true, true, ExecutionStageStatus::Pass),
    ]);
    assert_eq!(
        result,
        Err(ExecutionStageEvidenceError::SequenceGap {
            expected: 2,
            actual: 1
        })
    );
}

#[test]
fn input_order_is_normalized_by_explicit_sequence() {
    let report = project_execution_stages(&[
        stage("runtime", 2, true, true, ExecutionStageStatus::Pass),
        stage("policy", 1, true, true, ExecutionStageStatus::Pass),
    ])
    .expect("report");
    assert_eq!(report.stages[0].stage_id, "policy");
    assert_eq!(report.stages[1].stage_id, "runtime");
}

#[test]
fn blocked_stage_is_requested_but_not_executed() {
    let report = project_execution_stages(&[stage(
        "policy",
        1,
        true,
        false,
        ExecutionStageStatus::Blocked,
    )])
    .expect("report");
    assert_eq!(report.blocked, 1);
    assert_eq!(report.passed, 0);
}

#[test]
fn deterministic_projection_has_no_acceptance_or_telemetry_authority() {
    let input = [
        stage("policy", 1, true, true, ExecutionStageStatus::Pass),
        stage("runtime", 2, true, false, ExecutionStageStatus::Skipped),
    ];
    let left = project_execution_stages(&input).expect("left");
    let right = project_execution_stages(&input).expect("right");
    assert_eq!(left, right);

    let encoded = serde_json::to_string(&left).expect("serialize");
    for forbidden in [
        "AcceptanceDecision",
        "telemetry_authority",
        "dispatch",
        "provider_sdk",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
