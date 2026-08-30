use std::collections::BTreeSet;

use metao_contracts::runtime_certification::{
    CertificationCategoryResult, CertificationCategoryStatus, RuntimeCertificationBinding,
    RuntimeCertificationDecision, RuntimeCertificationError, RuntimeCertificationEvidenceBasis,
    RuntimeCertificationReport,
};

fn binding() -> RuntimeCertificationBinding {
    RuntimeCertificationBinding {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "cfg-a".to_string(),
        execution_context_id: "exec-context-1".to_string(),
        verification_context_id: "verify-context-1".to_string(),
    }
}

fn category(status: CertificationCategoryStatus, evidence_ref: Option<&str>) -> CertificationCategoryResult {
    CertificationCategoryResult {
        category_id: "prompt-injection".to_string(),
        status,
        benign_utility_passed: None,
        forbidden_action_observed: None,
        evidence_ref: evidence_ref.map(str::to_string),
        reason: "independent evaluator result".to_string(),
    }
}

fn report(result: CertificationCategoryResult) -> RuntimeCertificationReport {
    RuntimeCertificationReport {
        binding: binding(),
        evaluator_id: "independent-evaluator".to_string(),
        evaluator_version: "1.0.0".to_string(),
        evaluator_evidence_basis: RuntimeCertificationEvidenceBasis::IndependentEvaluator,
        evaluator_evidence_ref: "evaluator-run:sha256:abc123".to_string(),
        evaluated_at_epoch: 100,
        expires_at_epoch: Some(200),
        required_categories: BTreeSet::from(["prompt-injection".to_string()]),
        category_results: vec![result],
    }
}

#[test]
fn conclusive_pass_or_fail_requires_nonblank_evidence_reference() {
    for status in [CertificationCategoryStatus::Pass, CertificationCategoryStatus::Fail] {
        for evidence in [None, Some(""), Some("   ")] {
            let value = report(category(status, evidence));
            assert_eq!(value.validate(), Err(RuntimeCertificationError::BlankEvidenceRef));
        }
    }
}

#[test]
fn evidence_backed_pass_can_certify_but_incomplete_state_need_not_fake_evidence() {
    let passed = report(category(
        CertificationCategoryStatus::Pass,
        Some("evidence:prompt-injection:1"),
    ));
    assert_eq!(
        passed.project(&binding(), 150).expect("projection").decision,
        RuntimeCertificationDecision::Certified
    );

    let skipped = report(category(CertificationCategoryStatus::Skipped, None));
    assert_eq!(
        skipped.project(&binding(), 150).expect("projection").decision,
        RuntimeCertificationDecision::Incomplete
    );
}

#[test]
fn report_level_evaluator_origin_is_required_in_addition_to_category_evidence() {
    let mut value = report(category(
        CertificationCategoryStatus::Pass,
        Some("evidence:prompt-injection:1"),
    ));
    value.evaluator_evidence_basis = RuntimeCertificationEvidenceBasis::SelfReported;
    assert_eq!(
        value.validate(),
        Err(RuntimeCertificationError::InvalidEvaluatorEvidenceBasis)
    );

    let mut missing = report(category(
        CertificationCategoryStatus::Pass,
        Some("evidence:prompt-injection:1"),
    ));
    missing.evaluator_evidence_ref = String::new();
    assert_eq!(
        missing.validate(),
        Err(RuntimeCertificationError::BlankEvaluatorEvidenceRef)
    );
}
