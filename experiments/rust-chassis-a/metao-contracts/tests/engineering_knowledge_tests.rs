#[path = "../src/engineering_knowledge.rs"]
mod engineering_knowledge;

use engineering_knowledge::*;

fn source(
    id: &str,
    kind: SourceKind,
    observed_at: u64,
    max_age: u64,
    refresh_interval: u64,
    vendor_or_country: Option<&str>,
) -> KnowledgeSource {
    KnowledgeSource {
        source_id: id.to_string(),
        kind,
        locator: format!("https://example.invalid/{id}"),
        authorized: true,
        observed_at_epoch_s: observed_at,
        freshness: FreshnessPolicy {
            max_age_s: max_age,
            refresh_interval_s: refresh_interval,
        },
        vendor_or_country: vendor_or_country.map(str::to_string),
    }
}

fn claim(
    id: &str,
    source_id: &str,
    disposition: ClaimDisposition,
    class: ConstraintClass,
    strength: EvidenceStrength,
    confidence: u16,
) -> EngineeringClaim {
    EngineeringClaim {
        claim_id: id.to_string(),
        source_id: source_id.to_string(),
        disposition,
        constraint_class: class,
        strength,
        confidence_basis_points: confidence,
        evidence_ref: format!("evidence:{id}"),
    }
}

#[test]
fn stale_authorized_source_requires_refresh_for_material_decision() {
    let sources = [source(
        "nist",
        SourceKind::EngineeringStandard,
        100,
        50,
        25,
        None,
    )];
    let claims = [claim(
        "c1",
        "nist",
        ClaimDisposition::SupportsRequestedAction,
        ConstraintClass::Advisory,
        EvidenceStrength::Documented,
        9000,
    )];

    let decision = evaluate_engineering_authority(&sources, &claims, DecisionRisk::Material, 200)
        .unwrap();
    assert_eq!(decision.action, EngineeringAuthorityAction::RequireRefresh);
    assert_eq!(decision.stale_source_ids, vec!["nist"]);
}

#[test]
fn stronger_empirical_evidence_can_override_project_documentation() {
    let sources = [
        source(
            "project-doc",
            SourceKind::ProjectDocumentation,
            100,
            1_000,
            100,
            None,
        ),
        source(
            "experiment",
            SourceKind::EmpiricalTest,
            100,
            1_000,
            100,
            None,
        ),
    ];
    let claims = [
        claim(
            "doc-support",
            "project-doc",
            ClaimDisposition::SupportsRequestedAction,
            ConstraintClass::Advisory,
            EvidenceStrength::Documented,
            9900,
        ),
        claim(
            "test-conflict",
            "experiment",
            ClaimDisposition::ConflictsWithRequestedAction,
            ConstraintClass::Advisory,
            EvidenceStrength::EmpiricallyReproduced,
            9000,
        ),
    ];

    let decision = evaluate_engineering_authority(&sources, &claims, DecisionRisk::High, 200)
        .unwrap();
    assert_eq!(
        decision.action,
        EngineeringAuthorityAction::RequireConfirmation
    );
    assert_eq!(decision.required_confirmations, 2);
    assert!(decision.conflicting_claim_ids.contains(&"test-conflict".to_string()));
}

#[test]
fn hard_safety_or_policy_conflict_cannot_be_user_overridden() {
    let sources = [source(
        "security",
        SourceKind::SecurityAdvisory,
        100,
        1_000,
        100,
        None,
    )];
    let claims = [claim(
        "unsafe",
        "security",
        ClaimDisposition::ConflictsWithRequestedAction,
        ConstraintClass::HardSafetyOrPolicy,
        EvidenceStrength::IndependentlyObserved,
        9500,
    )];

    let decision = evaluate_engineering_authority(&sources, &claims, DecisionRisk::High, 200)
        .unwrap();
    assert_eq!(decision.action, EngineeringAuthorityAction::Block);
    assert_eq!(
        apply_user_override(
            &decision,
            &UserOverride {
                confirmation_count: 7,
                rationale: "do it anyway".to_string(),
                evidence_acknowledged: true,
            }
        ),
        Err(EngineeringKnowledgeError::InvalidOverride)
    );
}

#[test]
fn explicit_override_can_authorize_non_hard_deviation_and_preserves_conflict() {
    let sources = [source(
        "experiment",
        SourceKind::EmpiricalTest,
        100,
        1_000,
        100,
        None,
    )];
    let claims = [claim(
        "conflict",
        "experiment",
        ClaimDisposition::ConflictsWithRequestedAction,
        ConstraintClass::Advisory,
        EvidenceStrength::EmpiricallyReproduced,
        9900,
    )];

    let decision = evaluate_engineering_authority(&sources, &claims, DecisionRisk::Irreversible, 200)
        .unwrap();
    assert_eq!(decision.required_confirmations, 3);

    let overridden = apply_user_override(
        &decision,
        &UserOverride {
            confirmation_count: 3,
            rationale: "business owner accepts the measured engineering tradeoff".to_string(),
            evidence_acknowledged: true,
        },
    )
    .unwrap();

    assert_eq!(overridden.action, EngineeringAuthorityAction::Proceed);
    assert_eq!(overridden.conflicting_claim_ids, vec!["conflict"]);
}

#[test]
fn insufficient_evidence_fails_closed_for_material_action() {
    let decision = evaluate_engineering_authority(&[], &[], DecisionRisk::Material, 200).unwrap();
    assert_eq!(decision.action, EngineeringAuthorityAction::Block);
}

#[test]
fn vendor_or_country_identity_has_no_authority_effect() {
    let cn = source(
        "cn-source",
        SourceKind::ProviderDocumentation,
        100,
        1_000,
        100,
        Some("CN"),
    );
    let us = source(
        "us-source",
        SourceKind::ProviderDocumentation,
        100,
        1_000,
        100,
        Some("US"),
    );
    let cn_claim = claim(
        "cn",
        "cn-source",
        ClaimDisposition::SupportsRequestedAction,
        ConstraintClass::Advisory,
        EvidenceStrength::Documented,
        9000,
    );
    let us_claim = claim(
        "us",
        "us-source",
        ClaimDisposition::SupportsRequestedAction,
        ConstraintClass::Advisory,
        EvidenceStrength::Documented,
        9000,
    );

    let cn_decision = evaluate_engineering_authority(&[cn], &[cn_claim], DecisionRisk::Low, 200)
        .unwrap();
    let us_decision = evaluate_engineering_authority(&[us], &[us_claim], DecisionRisk::Low, 200)
        .unwrap();
    assert_eq!(cn_decision.action, us_decision.action);
}

#[test]
fn refresh_cadence_is_explicit_and_auditable() {
    let src = source(
        "daily",
        SourceKind::ProviderDocumentation,
        100,
        1_000,
        86_400,
        None,
    );
    assert!(!src.refresh_due(100 + 86_399));
    assert!(src.refresh_due(100 + 86_400));
}
