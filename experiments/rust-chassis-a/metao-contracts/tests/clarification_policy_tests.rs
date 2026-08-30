use metao_contracts::clarification_policy::{
    classify_clarification, ClarificationAction, ClarificationConcern, ClarificationDisposition,
    ClarificationPolicyError, Materiality, Reversibility, SafeDefault, UnresolvedDiscoveryItem,
};
use metao_contracts::project_contract::{
    ItemId, Provenance, ProvenanceCategory, SemanticCategory,
};

fn provenance(category: ProvenanceCategory, source: &str) -> Provenance {
    Provenance {
        category,
        source_id: source.to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn item(
    materiality: Materiality,
    reversibility: Reversibility,
    concern: ClarificationConcern,
    safe_default: Option<SafeDefault>,
) -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: ItemId("decision-1".into()),
        description: "Choose a low-impact implementation detail".into(),
        materiality,
        reversibility,
        concern,
        provenance: provenance(ProvenanceCategory::UserExplicit, "user-answer-1"),
        safe_default,
    }
}

fn safe_default() -> SafeDefault {
    SafeDefault {
        description: "Use the repository naming convention".into(),
        rationale: "Reversible and does not change product behavior".into(),
        provenance: provenance(ProvenanceCategory::MetaoAssumption, "default-policy-v1"),
    }
}

#[test]
fn material_ambiguity_requires_human() {
    let result = classify_clarification(
        &item(
            Materiality::Material,
            Reversibility::Reversible,
            ClarificationConcern::General,
            Some(safe_default()),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap();

    assert_eq!(result.action, ClarificationAction::AskHuman);
    assert!(result.assumption.is_none());
}

#[test]
fn irreversible_ambiguity_requires_human_even_if_non_material() {
    let result = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Irreversible,
            ClarificationConcern::General,
            Some(safe_default()),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap();

    assert_eq!(result.action, ClarificationAction::AskHuman);
}

#[test]
fn safe_reversible_default_becomes_assumption_only() {
    let result = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Reversible,
            ClarificationConcern::General,
            Some(safe_default()),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap();

    assert_eq!(result.action, ClarificationAction::RecordSafeAssumption);
    let semantic = result.assumption.unwrap().as_semantic_item();
    assert_eq!(semantic.category, SemanticCategory::Assumption);
    assert_ne!(semantic.category, SemanticCategory::UserRequirement);
}

#[test]
fn missing_safe_default_cannot_auto_continue() {
    let result = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Reversible,
            ClarificationConcern::General,
            None,
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap();

    assert_eq!(result.action, ClarificationAction::AskHuman);
    assert!(result.assumption.is_none());
}

#[test]
fn blank_default_rationale_fails_closed() {
    let mut default = safe_default();
    default.rationale = "   ".into();

    let error = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Reversible,
            ClarificationConcern::General,
            Some(default),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap_err();

    assert_eq!(
        error,
        ClarificationPolicyError::InvalidSafeDefault("blank default rationale")
    );
}

#[test]
fn blank_default_provenance_fails_closed() {
    let mut default = safe_default();
    default.provenance.source_id = " ".into();

    let error = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Reversible,
            ClarificationConcern::General,
            Some(default),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap_err();

    assert_eq!(error, ClarificationPolicyError::InvalidProvenance);
}

#[test]
fn high_impact_concerns_cannot_be_downgraded_to_non_material() {
    for concern in [
        ClarificationConcern::DestructiveChoice,
        ClarificationConcern::RegulatoryOrSecurity,
        ClarificationConcern::UserFixedTechnology,
        ClarificationConcern::ScopeChanging,
    ] {
        let error = classify_clarification(
            &item(
                Materiality::NonMaterial,
                Reversibility::Reversible,
                concern,
                Some(safe_default()),
            ),
            &ClarificationDisposition::Unresolved,
        )
        .unwrap_err();

        assert_eq!(
            error,
            ClarificationPolicyError::InvalidDisposition(
                "high-impact concern must be material"
            )
        );
    }
}

#[test]
fn explicit_resolution_is_separate_and_does_not_create_assumption() {
    let unresolved = item(
        Materiality::Material,
        Reversibility::Irreversible,
        ClarificationConcern::ScopeChanging,
        None,
    );
    let before = unresolved.clone();

    let result = classify_clarification(
        &unresolved,
        &ClarificationDisposition::Resolved {
            resolution: "Web only for MVP".into(),
            provenance: provenance(ProvenanceCategory::UserExplicit, "user-answer-2"),
        },
    )
    .unwrap();

    assert_eq!(result.action, ClarificationAction::NoAction);
    assert!(result.assumption.is_none());
    assert_eq!(unresolved, before);
}

#[test]
fn waiver_requires_explicit_rationale_and_provenance() {
    let unresolved = item(
        Materiality::Material,
        Reversibility::Reversible,
        ClarificationConcern::General,
        None,
    );

    let error = classify_clarification(
        &unresolved,
        &ClarificationDisposition::Waived {
            rationale: " ".into(),
            provenance: provenance(ProvenanceCategory::UserConfirmed, "user-waiver-1"),
        },
    )
    .unwrap_err();

    assert_eq!(
        error,
        ClarificationPolicyError::InvalidDisposition("blank waiver rationale")
    );
}

#[test]
fn result_round_trip_preserves_action_without_readiness_authority() {
    let result = classify_clarification(
        &item(
            Materiality::NonMaterial,
            Reversibility::Reversible,
            ClarificationConcern::General,
            Some(safe_default()),
        ),
        &ClarificationDisposition::Unresolved,
    )
    .unwrap();

    let json = serde_json::to_string(&result).unwrap();
    let decoded: metao_contracts::clarification_policy::ClarificationPolicyResult =
        serde_json::from_str(&json).unwrap();

    assert_eq!(decoded, result);
    assert!(!json.contains("SPEC_READY"));
    assert!(!json.contains("PLAN_READY"));
    assert!(!json.contains("ACCEPTED"));
}
