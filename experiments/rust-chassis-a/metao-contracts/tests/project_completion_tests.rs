use metao_contracts::project_completion::{
    CompletionEvidenceBasis, CompletionEvidenceStatus, ProjectCompletionDecision,
    ProjectCompletionEvidence, ProjectCompletionGate,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, Provenance, ProvenanceCategory,
    SemanticCategory, SemanticItem,
};
use std::collections::BTreeSet;

fn provenance(source: &str) -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: source.to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn item(id: &str, category: SemanticCategory, description: &str) -> SemanticItem {
    SemanticItem {
        item_id: ItemId(id.to_string()),
        category,
        description: description.to_string(),
        provenance: provenance("contract-source"),
    }
}

fn contract(items: Vec<SemanticItem>) -> ProjectContract {
    ProjectContract::new(
        ProjectId("project-1".to_string()),
        ContractId("contract-1".to_string()),
        "Build an integrated MVP".to_string(),
        BTreeSet::from(["buyer".to_string()]),
        items,
        vec![],
    )
    .expect("fixture contract must be valid")
}

fn evidence(
    contract: &ProjectContract,
    id: &str,
    obligation: &str,
    status: CompletionEvidenceStatus,
) -> ProjectCompletionEvidence {
    ProjectCompletionEvidence {
        evidence_id: id.to_string(),
        obligation_id: ItemId(obligation.to_string()),
        contract_binding: contract.binding(),
        status,
        evidence_basis: CompletionEvidenceBasis::IndependentAcceptance,
        verification_ref: Some(format!("independent-acceptance:{id}")),
        reason: "independent completion check".to_string(),
    }
}

#[test]
fn all_exact_binding_obligations_pass_project_accepts() {
    let contract = contract(vec![
        item("surface", SemanticCategory::RequiredSurface, "Public catalog"),
        item("api", SemanticCategory::RequiredCapability, "Backend API"),
        item("persist", SemanticCategory::UserRequirement, "Durable persistence"),
        item("accept", SemanticCategory::AcceptanceTest, "E2E journey passes"),
        item("dod", SemanticCategory::DefinitionOfDone, "Reproducible startup"),
    ]);
    let proof = [
        evidence(&contract, "e1", "surface", CompletionEvidenceStatus::Pass),
        evidence(&contract, "e2", "api", CompletionEvidenceStatus::Pass),
        evidence(&contract, "e3", "persist", CompletionEvidenceStatus::Pass),
        evidence(&contract, "e4", "accept", CompletionEvidenceStatus::Pass),
        evidence(&contract, "e5", "dod", CompletionEvidenceStatus::Pass),
    ];

    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::ProjectAccepted);
    assert!(result.reasons.is_empty());
    assert!(result
        .obligations
        .iter()
        .all(|row| row.status == CompletionEvidenceStatus::Pass));
}

#[test]
fn verified_evaluation_can_prove_completion_obligation() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);
    let mut proof = evidence(&contract, "api-proof", "api", CompletionEvidenceStatus::Pass);
    proof.evidence_basis = CompletionEvidenceBasis::VerifiedEvaluation;
    proof.verification_ref = Some("verified-evaluator:api:1".to_string());

    let result = ProjectCompletionGate::evaluate(&contract, &[proof]);
    assert_eq!(result.decision, ProjectCompletionDecision::ProjectAccepted);
}

#[test]
fn caller_declared_or_unknown_pass_cannot_mint_project_acceptance() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);

    for basis in [
        CompletionEvidenceBasis::CallerDeclared,
        CompletionEvidenceBasis::Unknown,
    ] {
        let mut proof = evidence(&contract, "api-proof", "api", CompletionEvidenceStatus::Pass);
        proof.evidence_basis = basis;
        let result = ProjectCompletionGate::evaluate(&contract, &[proof]);
        assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
        assert_eq!(result.obligations[0].status, CompletionEvidenceStatus::NotProven);
    }
}

#[test]
fn conclusive_evidence_requires_nonblank_verification_reference() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);

    for status in [CompletionEvidenceStatus::Pass, CompletionEvidenceStatus::Fail] {
        for reference in [None, Some(String::new()), Some("   ".to_string())] {
            let mut proof = evidence(&contract, "api-proof", "api", status);
            proof.verification_ref = reference;
            let result = ProjectCompletionGate::evaluate(&contract, &[proof]);
            assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
            assert_eq!(result.obligations[0].status, CompletionEvidenceStatus::NotProven);
        }
    }
}

#[test]
fn frontend_only_proof_cannot_complete_full_stack_contract() {
    let contract = contract(vec![
        item("frontend", SemanticCategory::RequiredSurface, "Marketplace UI"),
        item("backend", SemanticCategory::RequiredCapability, "Backend API"),
        item("persistence", SemanticCategory::UserRequirement, "Database persistence"),
    ]);
    let proof = [evidence(
        &contract,
        "surface-proof",
        "frontend",
        CompletionEvidenceStatus::Pass,
    )];

    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert_eq!(
        result
            .obligations
            .iter()
            .filter(|row| row.status != CompletionEvidenceStatus::Pass)
            .count(),
        2
    );
}

#[test]
fn explicit_verified_failure_returns_not_done() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);
    let proof = [evidence(
        &contract,
        "api-proof",
        "api",
        CompletionEvidenceStatus::Fail,
    )];
    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert_eq!(result.obligations[0].status, CompletionEvidenceStatus::Fail);
}

#[test]
fn unresolved_contract_item_blocks_completion() {
    let contract = contract(vec![
        item("api", SemanticCategory::RequiredCapability, "Backend API"),
        item(
            "open-question",
            SemanticCategory::UnresolvedItem,
            "Payment scope unresolved",
        ),
    ]);
    let proof = [evidence(
        &contract,
        "api-proof",
        "api",
        CompletionEvidenceStatus::Pass,
    )];
    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason.contains("open-question")));
}

#[test]
fn stale_contract_version_or_digest_cannot_satisfy_current_obligation() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);
    let mut wrong_version = evidence(
        &contract,
        "old-version",
        "api",
        CompletionEvidenceStatus::Pass,
    );
    wrong_version.contract_binding.version += 1;
    let mut wrong_digest = evidence(
        &contract,
        "old-digest",
        "api",
        CompletionEvidenceStatus::Pass,
    );
    wrong_digest.contract_binding.contract_digest = "stale-digest".to_string();

    for record in [wrong_version, wrong_digest] {
        let result = ProjectCompletionGate::evaluate(&contract, &[record]);
        assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
        assert_eq!(
            result.obligations[0].status,
            CompletionEvidenceStatus::NotProven
        );
    }
}

#[test]
fn assumptions_preferences_and_out_of_scope_do_not_create_completion_obligations() {
    let contract = contract(vec![
        item("api", SemanticCategory::RequiredCapability, "Backend API"),
        item("pref", SemanticCategory::Preference, "Prefer dark mode"),
        item("assume", SemanticCategory::Assumption, "Use UTC internally"),
        item("later", SemanticCategory::OutOfScope, "Native mobile app"),
    ]);
    let proof = [evidence(
        &contract,
        "api-proof",
        "api",
        CompletionEvidenceStatus::Pass,
    )];
    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::ProjectAccepted);
    assert_eq!(result.obligations.len(), 1);
    assert_eq!(result.obligations[0].obligation_id.0, "api");
}

#[test]
fn contradictory_duplicate_evidence_fails_closed() {
    let contract = contract(vec![item(
        "api",
        SemanticCategory::RequiredCapability,
        "Backend API",
    )]);
    let proof = [
        evidence(&contract, "pass", "api", CompletionEvidenceStatus::Pass),
        evidence(&contract, "fail", "api", CompletionEvidenceStatus::Fail),
    ];
    let result = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert_eq!(
        result.obligations[0].status,
        CompletionEvidenceStatus::NotProven
    );
    assert!(result.obligations[0]
        .reason
        .contains("contradictory duplicate evidence"));
}

#[test]
fn result_is_deterministic_serializable_and_project_scoped() {
    let contract = contract(vec![
        item("b", SemanticCategory::RequiredCapability, "Second obligation"),
        item("a", SemanticCategory::RequiredSurface, "First obligation"),
    ]);
    let proof = [
        evidence(&contract, "e-b", "b", CompletionEvidenceStatus::Pass),
        evidence(&contract, "e-a", "a", CompletionEvidenceStatus::Pass),
    ];
    let left = ProjectCompletionGate::evaluate(&contract, &proof);
    let right = ProjectCompletionGate::evaluate(&contract, &proof);
    assert_eq!(left, right);
    assert_eq!(left.obligations[0].obligation_id.0, "a");
    assert_eq!(left.obligations[1].obligation_id.0, "b");

    let encoded = serde_json::to_string(&left).expect("serialize completion result");
    let decoded: metao_contracts::project_completion::ProjectCompletionResult =
        serde_json::from_str(&encoded).expect("deserialize completion result");
    assert_eq!(decoded, left);
    for forbidden in ["AcceptanceDecision", "RuntimeId", "Orchestrator", "provider_id"] {
        assert!(!encoded.contains(forbidden));
    }
}
