mod project_contract {
    pub use metao_contracts::project_contract::*;
}

#[path = "../src/tech_stack_intake.rs"]
mod tech_stack_intake;

use project_contract::{Provenance, ProvenanceCategory};
use std::collections::BTreeSet;
use tech_stack_intake::{
    TechStackDecisionMode, TechStackIntakeError, TechnicalPreferenceProfile, Technology,
};

fn provenance(category: ProvenanceCategory, source_id: &str) -> Provenance {
    Provenance {
        category,
        source_id: source_id.to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn tech(value: &str) -> Technology {
    Technology::new(value).expect("test technology must be valid")
}

fn profile(mode: TechStackDecisionMode) -> TechnicalPreferenceProfile {
    TechnicalPreferenceProfile {
        mode,
        required_languages: BTreeSet::new(),
        preferred_languages: BTreeSet::new(),
        required_frameworks: BTreeSet::new(),
        preferred_frameworks: BTreeSet::new(),
        forbidden_technologies: BTreeSet::new(),
        frontend_preference: None,
        backend_preference: None,
        database_preference: None,
        mobile_requirement: None,
        deployment_target: None,
        hosting_constraints: None,
        cost_constraints: None,
        team_environment_constraints: None,
        rationale: match mode {
            TechStackDecisionMode::UserFixed => None,
            TechStackDecisionMode::UserPreferred => Some("user preference".to_string()),
            TechStackDecisionMode::MetaoRecommended => Some("evaluated recommendation".to_string()),
        },
        provenance: provenance(ProvenanceCategory::UserExplicit, "test-source"),
    }
}

#[test]
fn arbitrary_languages_and_technologies_are_data() {
    for value in ["C#", "Python", "PHP", "Go", "TypeScript/Node", "Elixir/Phoenix"] {
        assert_eq!(tech(value).as_str(), value.trim().to_lowercase());
    }
}

#[test]
fn blank_technology_identity_fails_closed() {
    assert_eq!(
        Technology::new("   "),
        Err(TechStackIntakeError::BlankTechnologyIdentity)
    );
}

#[test]
fn required_preferred_and_forbidden_remain_distinct() {
    let mut value = profile(TechStackDecisionMode::UserFixed);
    value.required_languages.insert(tech("Rust"));
    value.preferred_languages.insert(tech("Python"));
    value.forbidden_technologies.insert(tech("PHP"));
    assert!(value.validate().is_ok());
    assert!(value.required_languages.contains(&tech("rust")));
    assert!(value.preferred_languages.contains(&tech("python")));
    assert!(value.forbidden_technologies.contains(&tech("php")));
}

#[test]
fn required_forbidden_conflict_is_typed() {
    let mut value = profile(TechStackDecisionMode::UserFixed);
    value.required_languages.insert(tech("Rust"));
    value.forbidden_technologies.insert(tech("rust"));
    assert_eq!(
        value.validate(),
        Err(TechStackIntakeError::ConflictRequiredForbidden)
    );
}

#[test]
fn preferred_forbidden_conflict_is_typed() {
    let mut value = profile(TechStackDecisionMode::UserFixed);
    value.preferred_frameworks.insert(tech("Axum"));
    value.forbidden_technologies.insert(tech("axum"));
    assert_eq!(
        value.validate(),
        Err(TechStackIntakeError::ConflictPreferredForbidden)
    );
}

#[test]
fn required_preferred_conflict_is_typed() {
    let mut value = profile(TechStackDecisionMode::UserFixed);
    value.required_languages.insert(tech("Rust"));
    value.preferred_languages.insert(tech("rust"));
    assert_eq!(
        value.validate(),
        Err(TechStackIntakeError::ConflictRequiredPreferred)
    );
}

#[test]
fn user_fixed_is_valid_without_override_rationale() {
    assert!(profile(TechStackDecisionMode::UserFixed).validate().is_ok());
}

#[test]
fn user_fixed_override_is_forbidden() {
    let original = profile(TechStackDecisionMode::UserFixed);
    let replacement = profile(TechStackDecisionMode::MetaoRecommended);
    assert_eq!(
        original.explicit_override(
            replacement,
            "explicit replacement",
            provenance(ProvenanceCategory::UserConfirmed, "override")
        ),
        Err(TechStackIntakeError::UserFixedOverrideForbidden)
    );
}

#[test]
fn user_preferred_requires_material_rationale() {
    let mut value = profile(TechStackDecisionMode::UserPreferred);
    value.rationale = Some("   ".to_string());
    assert_eq!(value.validate(), Err(TechStackIntakeError::MissingRationale));
}

#[test]
fn user_preferred_override_requires_rationale() {
    let original = profile(TechStackDecisionMode::UserPreferred);
    let replacement = profile(TechStackDecisionMode::MetaoRecommended);
    assert_eq!(
        original.explicit_override(
            replacement,
            "   ",
            provenance(ProvenanceCategory::UserConfirmed, "override")
        ),
        Err(TechStackIntakeError::MissingRationale)
    );
}

#[test]
fn invalid_profile_provenance_fails_closed() {
    let mut value = profile(TechStackDecisionMode::UserPreferred);
    value.provenance = provenance(ProvenanceCategory::UserExplicit, "   ");
    assert_eq!(value.validate(), Err(TechStackIntakeError::InvalidProvenance));
}

#[test]
fn explicit_override_requires_valid_provenance() {
    let original = profile(TechStackDecisionMode::UserPreferred);
    let replacement = profile(TechStackDecisionMode::MetaoRecommended);
    assert_eq!(
        original.explicit_override(
            replacement,
            "explicit replacement",
            provenance(ProvenanceCategory::UserConfirmed, "   ")
        ),
        Err(TechStackIntakeError::InvalidProvenance)
    );
}

#[test]
fn user_preferred_explicit_override_passes_and_preserves_decision_evidence() {
    let original = profile(TechStackDecisionMode::UserPreferred);
    let mut replacement = profile(TechStackDecisionMode::MetaoRecommended);
    replacement.required_languages.insert(tech("Rust"));
    let result = original
        .explicit_override(
            replacement,
            "benchmark evidence",
            provenance(ProvenanceCategory::UserConfirmed, "decision-42")
        )
        .expect("explicit override should pass");
    assert_eq!(result.mode, TechStackDecisionMode::MetaoRecommended);
    assert_eq!(result.rationale.as_deref(), Some("benchmark evidence"));
    assert_eq!(result.provenance.source_id, "decision-42");
}

#[test]
fn metao_recommended_can_be_replaced_only_through_explicit_boundary() {
    let original = profile(TechStackDecisionMode::MetaoRecommended);
    let replacement = profile(TechStackDecisionMode::UserPreferred);
    let result = original
        .explicit_override(
            replacement,
            "user changed preference",
            provenance(ProvenanceCategory::UserConfirmed, "human-decision")
        )
        .expect("explicit replacement should pass");
    assert_eq!(result.mode, TechStackDecisionMode::UserPreferred);
}

#[test]
fn recommendation_provenance_is_preserved() {
    let mut value = profile(TechStackDecisionMode::MetaoRecommended);
    value.provenance = provenance(ProvenanceCategory::MetaoRecommendation, "benchmark-7");
    assert!(value.validate().is_ok());
    assert_eq!(value.provenance.category, ProvenanceCategory::MetaoRecommendation);
    assert_eq!(value.provenance.source_id, "benchmark-7");
}

#[test]
fn serialization_roundtrip_preserves_mode_sets_and_provenance() {
    let mut value = profile(TechStackDecisionMode::MetaoRecommended);
    value.required_languages.insert(tech("Rust"));
    value.preferred_frameworks.insert(tech("Axum"));
    value.forbidden_technologies.insert(tech("PHP"));
    value.provenance = provenance(ProvenanceCategory::MetaoRecommendation, "eval-1");
    let encoded = serde_json::to_string(&value).expect("serialize profile");
    let decoded: TechnicalPreferenceProfile =
        serde_json::from_str(&encoded).expect("deserialize profile");
    assert_eq!(decoded, value);
}

#[test]
fn recommendation_serialization_does_not_mint_user_requirement() {
    let value = profile(TechStackDecisionMode::MetaoRecommended);
    let encoded = serde_json::to_string(&value).expect("serialize profile");
    assert!(!encoded.contains("UserRequirement"));
    assert!(!encoded.contains("SPEC_READY"));
    assert!(!encoded.contains("PLAN_READY"));
    assert!(!encoded.contains("ACCEPTED"));
}

#[test]
fn framework_neutral_constraints_roundtrip_as_plain_data() {
    let mut value = profile(TechStackDecisionMode::UserPreferred);
    value.frontend_preference = Some("server-rendered".to_string());
    value.backend_preference = Some("modular monolith".to_string());
    value.database_preference = Some("relational".to_string());
    value.mobile_requirement = Some("cross-platform".to_string());
    value.deployment_target = Some("self-hosted Linux".to_string());
    value.hosting_constraints = Some("no provider lock-in".to_string());
    value.cost_constraints = Some("bounded monthly cost".to_string());
    value.team_environment_constraints = Some("Windows dev machines".to_string());
    let encoded = serde_json::to_string(&value).expect("serialize profile");
    let decoded: TechnicalPreferenceProfile =
        serde_json::from_str(&encoded).expect("deserialize profile");
    assert_eq!(decoded, value);
}

#[test]
fn domain_has_no_runtime_or_acceptance_authority_fields() {
    let value = profile(TechStackDecisionMode::MetaoRecommended);
    let encoded = serde_json::to_string(&value).expect("serialize profile");
    for forbidden in [
        "runtime_id",
        "provider_id",
        "acceptance_decision",
        "spec_ready",
        "plan_ready",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
