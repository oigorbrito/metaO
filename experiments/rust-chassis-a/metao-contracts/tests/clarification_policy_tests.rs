use metao_contracts::clarification_policy::{
    apply_explicit_resolution, ClarificationAction, ClarificationDecision, ClarificationPolicy,
    ClarificationPolicyError, ExplicitResolution, Materiality, MaterialityReason, ResolutionKind,
    Reversibility, SafeDefault, UnresolvedDiscoveryItem,
};
use metao_contracts::project_contract::{Provenance, ProvenanceCategory, SemanticCategory};

fn provenance(category: ProvenanceCategory, source_id: &str) -> Provenance {
    Provenance {
        category,
        source_id: source_id.to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn item(materiality: Materiality, reversibility: Reversibility) -> UnresolvedDiscoveryItem {
    UnresolvedDiscoveryItem {
        item_id: "discovery-1".to_string(),
        description: "Choose a non-functional discovery default".to_string(),
        materiality,
        reversibility,
        materiality_reason: None,
        provenance: provenance(ProvenanceCategory::UserExplicit, "intake"),
        safe_default: None,
    }
}

fn safe_default() -> SafeDefault {
    SafeDefault {
        value: "Use the reversible default".to_string(),
        rationale: "Low-cost and reversible".to_string(),
        provenance: provenance(ProvenanceCategory::SystemDefault, "safe-default-policy"),
    }
}

#[test]
fn material_ambiguity_asks_human() {
    let value = item(Materiality::Material, Reversibility::Reversible);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    assert_eq!(decision.action, ClarificationAction::AskHuman);
    assert!(decision.assumption.is_none());
}

#[test]
fn irreversible_ambiguity_asks_human() {
    let value = item(Materiality::NonMaterial, Reversibility::Irreversible);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    assert_eq!(decision.action, ClarificationAction::AskHuman);
}

#[test]
fn safe_reversible_default_records_assumption() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    value.safe_default = Some(safe_default());
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    assert_eq!(decision.action, ClarificationAction::RecordSafeAssumption);
    let assumption = decision.assumption.expect("assumption is required");
    assert_eq!(assumption.category, SemanticCategory::Assumption);
    assert_ne!(assumption.category, SemanticCategory::UserRequirement);
    assert_eq!(assumption.description, "Use the reversible default");
    assert_eq!(assumption.provenance.source_id, "safe-default-policy");
}

#[test]
fn no_default_cannot_auto_continue() {
    let value = item(Materiality::NonMaterial, Reversibility::Reversible);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    assert_eq!(decision.action, ClarificationAction::AskHuman);
    assert!(decision.assumption.is_none());
}

#[test]
fn blank_safe_default_rationale_fails_closed() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    let mut default = safe_default();
    default.rationale = "   ".to_string();
    value.safe_default = Some(default);
    assert_eq!(
        ClarificationPolicy::classify(&value),
        Err(ClarificationPolicyError::InvalidSafeDefault)
    );
}

#[test]
fn invalid_safe_default_provenance_fails_closed() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    let mut default = safe_default();
    default.provenance.source_id = "   ".to_string();
    value.safe_default = Some(default);
    assert_eq!(
        ClarificationPolicy::classify(&value),
        Err(ClarificationPolicyError::InvalidSafeDefault)
    );
}

#[test]
fn high_impact_materiality_reason_cannot_be_downgraded() {
    for reason in [
        MaterialityReason::Destructive,
        MaterialityReason::RegulatoryOrSecurity,
        MaterialityReason::UserFixedTechnology,
        MaterialityReason::ScopeChanging,
        MaterialityReason::OtherMaterialImpact,
    ] {
        let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
        value.materiality_reason = Some(reason);
        value.safe_default = Some(safe_default());
        assert_eq!(
            ClarificationPolicy::classify(&value),
            Err(ClarificationPolicyError::InvalidMateriality)
        );
    }
}

#[test]
fn high_impact_reasons_are_representable_as_material() {
    for reason in [
        MaterialityReason::Destructive,
        MaterialityReason::RegulatoryOrSecurity,
        MaterialityReason::UserFixedTechnology,
        MaterialityReason::ScopeChanging,
        MaterialityReason::OtherMaterialImpact,
    ] {
        let mut value = item(Materiality::Material, Reversibility::Reversible);
        value.materiality_reason = Some(reason);
        let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
        assert_eq!(decision.action, ClarificationAction::AskHuman);
    }
}

#[test]
fn explicit_resolution_preserves_original_item_and_decision() {
    let mut value = item(Materiality::Material, Reversibility::Irreversible);
    value.materiality_reason = Some(MaterialityReason::ScopeChanging);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    let resolution = ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "User selected the scope explicitly".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "human-42"),
    };
    let resolved = apply_explicit_resolution(&value, &decision, resolution)
        .expect("explicit resolution should succeed");
    assert_eq!(resolved.original_item, value);
    assert_eq!(resolved.original_decision, decision);
    assert_eq!(resolved.next_action, ClarificationAction::NoAction);
    assert_eq!(resolved.resolution.provenance.source_id, "human-42");
}

#[test]
fn explicit_waiver_is_separate_from_historical_classification() {
    let value = item(Materiality::Material, Reversibility::Reversible);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    assert_eq!(decision.action, ClarificationAction::AskHuman);
    let resolution = ExplicitResolution {
        kind: ResolutionKind::ExplicitWaiver,
        rationale: "Authorized waiver".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "waiver-1"),
    };
    let resolved = apply_explicit_resolution(&value, &decision, resolution)
        .expect("waiver should be explicit and valid");
    assert_eq!(resolved.original_decision.action, ClarificationAction::AskHuman);
    assert_eq!(resolved.resolution.kind, ResolutionKind::ExplicitWaiver);
}

#[test]
fn forged_historical_decision_cannot_be_bound_to_resolution() {
    let value = item(Materiality::Material, Reversibility::Reversible);
    let forged = ClarificationDecision {
        action: ClarificationAction::NoAction,
        assumption: None,
        rationale: "caller-forged downgrade".to_string(),
    };
    let resolution = ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "Valid human resolution".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "human-1"),
    };
    assert_eq!(
        apply_explicit_resolution(&value, &forged, resolution),
        Err(ClarificationPolicyError::DecisionBindingMismatch)
    );
}

#[test]
fn blank_resolution_rationale_fails_closed() {
    let value = item(Materiality::Material, Reversibility::Reversible);
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    let resolution = ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "   ".to_string(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "human-1"),
    };
    assert_eq!(
        apply_explicit_resolution(&value, &decision, resolution),
        Err(ClarificationPolicyError::InvalidResolution)
    );
}

#[test]
fn policy_decision_is_deterministic_and_serializable() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    value.safe_default = Some(safe_default());
    let left = ClarificationPolicy::classify(&value).expect("first classification");
    let right = ClarificationPolicy::classify(&value).expect("second classification");
    assert_eq!(left, right);
    let encoded = serde_json::to_string(&left).expect("serialize decision");
    let decoded: ClarificationDecision =
        serde_json::from_str(&encoded).expect("deserialize decision");
    assert_eq!(decoded, left);
}

#[test]
fn policy_has_no_readiness_or_acceptance_authority() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    value.safe_default = Some(safe_default());
    let decision = ClarificationPolicy::classify(&value).expect("classification should succeed");
    let encoded = serde_json::to_string(&decision).expect("serialize decision");
    for forbidden in [
        "SPEC_READY",
        "PLAN_READY",
        "ACCEPTED",
        "acceptance_decision",
        "runtime_id",
        "provider_id",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}

#[test]
fn blank_item_identity_and_description_fail_closed() {
    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    value.item_id = "   ".to_string();
    assert_eq!(
        ClarificationPolicy::classify(&value),
        Err(ClarificationPolicyError::BlankItemIdentity)
    );

    let mut value = item(Materiality::NonMaterial, Reversibility::Reversible);
    value.description = "   ".to_string();
    assert_eq!(
        ClarificationPolicy::classify(&value),
        Err(ClarificationPolicyError::BlankDescription)
    );
}
