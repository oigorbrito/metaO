use std::collections::BTreeSet;

use metao_contracts::runtime_certification::{
    CertificationCategoryResult, CertificationCategoryStatus, RuntimeCertificationBinding,
    RuntimeCertificationDecision, RuntimeCertificationError, RuntimeCertificationReport,
};

fn binding(runtime_id: &str) -> RuntimeCertificationBinding {
    RuntimeCertificationBinding {
        runtime_id: runtime_id.to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "cfg-a".to_string(),
        execution_context_id: "exec-context-1".to_string(),
        verification_context_id: "verify-context-1".to_string(),
    }
}

fn result(category: &str, status: CertificationCategoryStatus) -> CertificationCategoryResult {
    CertificationCategoryResult {
        category_id: category.to_string(),
        status,
        benign_utility_passed: None,
        forbidden_action_observed: None,
        evidence_ref: Some(format!("evidence:{category}")),
        reason: format!("independent evaluator result for {category}"),
    }
}

fn report(runtime_id: &str) -> RuntimeCertificationReport {
    RuntimeCertificationReport {
        binding: binding(runtime_id),
        evaluator_id: "independent-redteam-evaluator".to_string(),
        evaluator_version: "1.0.0".to_string(),
        evaluated_at_epoch: 100,
        expires_at_epoch: Some(200),
        required_categories: BTreeSet::from([
            "prompt-injection".to_string(),
            "unauthorized-tool-use".to_string(),
        ]),
        category_results: vec![
            result("prompt-injection", CertificationCategoryStatus::Pass),
            result("unauthorized-tool-use", CertificationCategoryStatus::Pass),
        ],
    }
}

#[test]
fn all_required_categories_must_pass_for_certification() {
    let value = report("runtime-a");
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Certified);
}

#[test]
fn runtime_cannot_certify_itself() {
    let mut value = report("runtime-a");
    value.evaluator_id = "runtime-a".to_string();
    assert_eq!(
        value.validate(),
        Err(RuntimeCertificationError::SelfCertification)
    );
}

#[test]
fn certification_requires_explicit_expiry() {
    let mut value = report("runtime-a");
    value.expires_at_epoch = None;
    assert_eq!(
        value.validate(),
        Err(RuntimeCertificationError::MissingExpiry)
    );
    assert!(!value.applies_to(
        "runtime-a",
        "1.0.0",
        "cfg-a",
        "exec-context-1",
        "verify-context-1",
        150,
    ));
}

#[test]
fn report_is_not_applicable_before_it_was_evaluated() {
    let value = report("runtime-a");
    assert!(!value.applies_to(
        "runtime-a",
        "1.0.0",
        "cfg-a",
        "exec-context-1",
        "verify-context-1",
        99,
    ));
    let projection = value.project(&binding("runtime-a"), 99).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Stale);
}

#[test]
fn security_failure_is_not_rescued_by_benign_utility_success() {
    let mut value = report("runtime-a");
    value.category_results[1].status = CertificationCategoryStatus::Fail;
    value.category_results[1].benign_utility_passed = Some(true);
    value.category_results[1].forbidden_action_observed = Some(true);
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::NotCertified);
    assert_eq!(projection.failed_categories, vec!["unauthorized-tool-use"]);
}

#[test]
fn pass_cannot_coexist_with_observed_forbidden_action() {
    let mut value = report("runtime-a");
    value.category_results[0].forbidden_action_observed = Some(true);
    assert_eq!(
        value.validate(),
        Err(RuntimeCertificationError::ContradictoryPassFacts(
            "prompt-injection".to_string()
        ))
    );
}

#[test]
fn skipped_required_category_is_incomplete_not_pass() {
    let mut value = report("runtime-a");
    value.category_results[0].status = CertificationCategoryStatus::Skipped;
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Incomplete);
}

#[test]
fn not_requested_required_category_is_incomplete() {
    let mut value = report("runtime-a");
    value.category_results[0].status = CertificationCategoryStatus::NotRequested;
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Incomplete);
}

#[test]
fn evaluator_error_is_not_runtime_security_pass_or_fail() {
    let mut value = report("runtime-a");
    value.category_results[0].status = CertificationCategoryStatus::EvaluatorError;
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Incomplete);
    assert!(projection.failed_categories.is_empty());
    assert_eq!(projection.incomplete_categories, vec!["prompt-injection"]);
}

#[test]
fn omitted_required_category_is_incomplete() {
    let mut value = report("runtime-a");
    value.category_results.remove(0);
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Incomplete);
}

#[test]
fn empty_required_profile_cannot_mint_certification() {
    let mut value = report("runtime-a");
    value.required_categories.clear();
    let projection = value.project(&binding("runtime-a"), 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Incomplete);
}

#[test]
fn config_or_version_mutation_makes_prior_report_stale() {
    let value = report("runtime-a");
    let mut current = binding("runtime-a");
    current.config_id = "cfg-b".to_string();
    let projection = value.project(&current, 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Stale);

    let mut version_changed = binding("runtime-a");
    version_changed.runtime_version = "2.0.0".to_string();
    let projection = value.project(&version_changed, 150).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Stale);
}

#[test]
fn expired_report_is_stale() {
    let value = report("runtime-a");
    let projection = value.project(&binding("runtime-a"), 200).expect("projection");
    assert_eq!(projection.decision, RuntimeCertificationDecision::Stale);
}

#[test]
fn invalid_public_report_cannot_bypass_validation_through_applies_to() {
    let mut value = report("runtime-a");
    value.expires_at_epoch = Some(100);
    assert!(!value.applies_to(
        "runtime-a",
        "1.0.0",
        "cfg-a",
        "exec-context-1",
        "verify-context-1",
        100,
    ));
}

#[test]
fn duplicate_category_results_fail_closed() {
    let mut value = report("runtime-a");
    value.category_results.push(result(
        "prompt-injection",
        CertificationCategoryStatus::Fail,
    ));
    assert_eq!(
        value.validate(),
        Err(RuntimeCertificationError::DuplicateCategory(
            "prompt-injection".to_string()
        ))
    );
}

#[test]
fn materially_different_runtimes_use_same_generic_evidence_shape() {
    let first = report("runtime-a")
        .project(&binding("runtime-a"), 150)
        .expect("first");
    let second = report("runtime-b")
        .project(&binding("runtime-b"), 150)
        .expect("second");
    assert_eq!(first.decision, RuntimeCertificationDecision::Certified);
    assert_eq!(second.decision, RuntimeCertificationDecision::Certified);
    assert_ne!(first.binding.runtime_id, second.binding.runtime_id);
    assert_eq!(first.required_categories, second.required_categories);
}

#[test]
fn serialization_is_deterministic_and_authority_free() {
    let projection = report("runtime-a")
        .project(&binding("runtime-a"), 150)
        .expect("projection");
    let encoded = serde_json::to_string(&projection).expect("serialize");
    let decoded: metao_contracts::runtime_certification::RuntimeCertificationProjection =
        serde_json::from_str(&encoded).expect("deserialize");
    assert_eq!(decoded, projection);
    for forbidden in [
        "AcceptanceDecision",
        "PolicyEffect",
        "approval",
        "dispatch",
        "MVP_ACCEPTED",
        "universal_safety",
        "agentdojo",
        "pyrit",
    ] {
        assert!(!encoded.to_lowercase().contains(&forbidden.to_lowercase()));
    }
}
