use metao_contracts::clarification_policy::{
    apply_explicit_resolution, ClarificationAction, ClarificationPolicy, ExplicitResolution,
    Materiality, MaterialityReason, ResolutionKind, Reversibility, SafeDefault,
    UnresolvedDiscoveryItem,
};
use metao_contracts::project_completion::{
    CompletionEvidenceBasis, CompletionEvidenceStatus, ProjectCompletionDecision,
    ProjectCompletionEvidence, ProjectCompletionGate,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, Provenance, ProvenanceCategory,
    SemanticCategory, SemanticItem,
};
use metao_contracts::reference_intake::{
    PromotionTargetCategory, ReferenceInput, ReferenceIntake, ReferenceKind, ReferenceTrait,
    TraitId,
};
use std::collections::BTreeSet;

fn provenance(category: ProvenanceCategory, source_id: &str) -> Provenance {
    Provenance {
        category,
        source_id: source_id.into(),
        derived_from: None,
        authorization: None,
    }
}

fn marketplace_reference_input() -> ReferenceInput {
    ReferenceInput {
        reference_id: metao_contracts::project_contract::ReferenceId("ref-marketplace-web".into()),
        reference_kind: ReferenceKind::Url,
        locator: "https://example.com/marketplace".into(),
        desired_traits: vec![ReferenceTrait {
            trait_id: TraitId("catalog-browse".into()),
            description: "Browse product catalog and listings".into(),
        }],
        undesired_traits: vec![],
        provenance: provenance(ProvenanceCategory::UserExplicit, "reference-intake"),
    }
}

fn project(goal: &str, version_note: &str) -> ProjectContract {
    let user_requirement = SemanticItem {
        item_id: ItemId("req-discovery-marketplace".into()),
        category: SemanticCategory::UserRequirement,
        description: goal.into(),
        provenance: provenance(ProvenanceCategory::UserExplicit, version_note),
    };
    let acceptance = SemanticItem {
        item_id: ItemId("done-marketplace".into()),
        category: SemanticCategory::DefinitionOfDone,
        description: "Project completion requires exact-binding independent acceptance".into(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, version_note),
    };

    ProjectContract::new(
        ProjectId("marketplace-project".into()),
        ContractId("marketplace-contract".into()),
        goal.into(),
        BTreeSet::new(),
        vec![user_requirement, acceptance],
        vec![],
    )
    .expect("project contract")
}

#[test]
fn discovery_composition_crosses_ambiguity_reference_contract_versioning_and_completion_gate() {
    let unresolved = UnresolvedDiscoveryItem {
        item_id: "discovery-ambiguity-1".into(),
        description: "Build a marketplace without specifying mobile vs web scope".into(),
        materiality: Materiality::Material,
        reversibility: Reversibility::Reversible,
        materiality_reason: Some(MaterialityReason::ScopeChanging),
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-intent"),
        safe_default: None,
    };
    let ambiguity = ClarificationPolicy::classify(&unresolved).expect("clarification policy");
    assert_eq!(ambiguity.action, ClarificationAction::AskHuman);

    let safe = UnresolvedDiscoveryItem {
        item_id: "discovery-ambiguity-2".into(),
        description: "Default storefront color".into(),
        materiality: Materiality::NonMaterial,
        reversibility: Reversibility::Reversible,
        materiality_reason: None,
        provenance: provenance(ProvenanceCategory::UserExplicit, "initial-intent"),
        safe_default: Some(SafeDefault {
            value: "Use the reversible default".into(),
            rationale: "Low-cost and reversible".into(),
            provenance: provenance(ProvenanceCategory::SystemDefault, "safe-default-policy"),
        }),
    };
    let assumption = ClarificationPolicy::classify(&safe).expect("safe default");
    assert_eq!(assumption.action, ClarificationAction::RecordSafeAssumption);
    assert!(assumption.assumption.is_some());

    let reference = ReferenceIntake::evaluate_reference(&marketplace_reference_input())
        .expect("reference evaluation")
        .expect("reference should be valid");
    assert!(reference
        .selected_desired_traits
        .contains_key("catalog-browse"));

    let promoted = ReferenceIntake::promote_reference_trait(
        &reference,
        &TraitId("catalog-browse".into()),
        PromotionTargetCategory::UserRequirement,
        ItemId("req-catalog".into()),
        provenance(ProvenanceCategory::UserConfirmed, "reference-confirmation"),
    )
    .expect("reference promotion");
    assert_eq!(promoted.category, SemanticCategory::UserRequirement);

    let contract_v1 = project("Build a marketplace.", "contract-v1");
    assert_eq!(contract_v1.version(), 1);
    assert!(contract_v1
        .user_requirements()
        .contains_key(&ItemId("req-discovery-marketplace".into())));

    let contract_v2 = ProjectContract::revise_contract(
        &contract_v1,
        "Build a marketplace with explicit catalog browsing.".into(),
        BTreeSet::new(),
        vec![promoted.clone()],
        vec![],
        "incorporate selected reference trait".into(),
        provenance(ProvenanceCategory::UserConfirmed, "contract-revision"),
    )
    .expect("contract revision");
    assert_eq!(contract_v2.version(), 2);
    assert_ne!(contract_v1.contract_digest(), contract_v2.contract_digest());

    let replayed_resolution = ExplicitResolution {
        kind: ResolutionKind::HumanResolution,
        rationale: "user chose explicit catalog scope".into(),
        provenance: provenance(ProvenanceCategory::UserConfirmed, "human-clarification"),
    };
    let decision =
        ClarificationPolicy::classify(&unresolved).expect("clarification decision to replay");
    let resolved = apply_explicit_resolution(&unresolved, &decision, replayed_resolution)
        .expect("resolution application");
    assert_eq!(
        resolved.original_decision.action,
        ClarificationAction::AskHuman
    );

    let completion_v1 = ProjectCompletionGate::evaluate(
        &contract_v1,
        &[
            ProjectCompletionEvidence {
                evidence_id: "evidence-v1".into(),
                obligation_id: ItemId("req-discovery-marketplace".into()),
                contract_binding: contract_v1.binding(),
                status: CompletionEvidenceStatus::Pass,
                evidence_basis: CompletionEvidenceBasis::IndependentAcceptance,
                verification_ref: Some("verification-v1".into()),
                reason: "exact-binding evidence for v1".into(),
            },
            ProjectCompletionEvidence {
                evidence_id: "evidence-v1b".into(),
                obligation_id: ItemId("done-marketplace".into()),
                contract_binding: contract_v1.binding(),
                status: CompletionEvidenceStatus::Pass,
                evidence_basis: CompletionEvidenceBasis::IndependentAcceptance,
                verification_ref: Some("verification-v1b".into()),
                reason: "definition of done proven on exact binding".into(),
            },
        ],
    );
    assert_eq!(
        completion_v1.decision,
        ProjectCompletionDecision::ProjectAccepted
    );

    let stale_completion = ProjectCompletionGate::evaluate(
        &contract_v2,
        &[ProjectCompletionEvidence {
            evidence_id: "evidence-v1".into(),
            obligation_id: ItemId("req-discovery-marketplace".into()),
            contract_binding: contract_v1.binding(),
            status: CompletionEvidenceStatus::Pass,
            evidence_basis: CompletionEvidenceBasis::IndependentAcceptance,
            verification_ref: Some("verification-v1".into()),
            reason: "stale binding must not carry forward".into(),
        }],
    );
    assert_eq!(
        stale_completion.decision,
        ProjectCompletionDecision::NotDone
    );
    assert!(stale_completion
        .reasons
        .iter()
        .any(|reason| reason.contains("missing exact-binding verified evidence")));
}
