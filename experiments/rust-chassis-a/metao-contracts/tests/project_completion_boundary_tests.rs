use metao_contracts::project_completion::{
    CompletionEvidenceBasis, CompletionEvidenceStatus, ProjectCompletionDecision,
    ProjectCompletionEvidence, ProjectCompletionGate,
};
use metao_contracts::project_contract::{
    ContractId, ItemId, ProjectContract, ProjectId, Provenance, ProvenanceCategory,
    SemanticCategory, SemanticItem,
};
use std::collections::BTreeSet;

fn provenance() -> Provenance {
    Provenance {
        category: ProvenanceCategory::UserExplicit,
        source_id: "boundary-test".to_string(),
        derived_from: None,
        authorization: None,
    }
}

fn contract(items: Vec<SemanticItem>) -> ProjectContract {
    ProjectContract::new(
        ProjectId("project-boundary".to_string()),
        ContractId("contract-boundary".to_string()),
        "Boundary completion contract".to_string(),
        BTreeSet::from(["operator".to_string()]),
        items,
        vec![],
    )
    .expect("boundary fixture contract must be valid")
}

fn required_capability() -> SemanticItem {
    SemanticItem {
        item_id: ItemId("api".to_string()),
        category: SemanticCategory::RequiredCapability,
        description: "Backend API".to_string(),
        provenance: provenance(),
    }
}

fn pass_evidence(contract: &ProjectContract) -> ProjectCompletionEvidence {
    ProjectCompletionEvidence {
        evidence_id: "pass-proof".to_string(),
        obligation_id: ItemId("api".to_string()),
        contract_binding: contract.binding(),
        status: CompletionEvidenceStatus::Pass,
        evidence_basis: CompletionEvidenceBasis::IndependentAcceptance,
        verification_ref: Some("independent-acceptance:api".to_string()),
        reason: "independent pass".to_string(),
    }
}

#[test]
fn zero_completion_obligations_is_not_done() {
    let contract = contract(vec![SemanticItem {
        item_id: ItemId("preference-only".to_string()),
        category: SemanticCategory::Preference,
        description: "Prefer compact navigation".to_string(),
        provenance: provenance(),
    }]);

    let result = ProjectCompletionGate::evaluate(&contract, &[]);

    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert!(result.obligations.is_empty());
    assert!(result
        .reasons
        .iter()
        .any(|reason| reason == "project contract defines no completion obligations"));
}

#[test]
fn malformed_pass_evidence_cannot_prove_obligation() {
    let contract = contract(vec![required_capability()]);

    for (evidence_id, reason) in [
        ("", "independent pass"),
        ("   ", "independent pass"),
        ("pass-proof", ""),
        ("pass-proof", "   "),
    ] {
        let mut malformed = pass_evidence(&contract);
        malformed.evidence_id = evidence_id.to_string();
        malformed.reason = reason.to_string();

        let result = ProjectCompletionGate::evaluate(&contract, &[malformed]);
        assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
        assert_eq!(result.obligations.len(), 1);
        assert_eq!(
            result.obligations[0].status,
            CompletionEvidenceStatus::NotProven
        );
        assert_eq!(
            result.obligations[0].reason,
            "missing exact-binding verified evidence"
        );
    }
}

#[test]
fn caller_declared_pass_is_not_independent_completion_evidence() {
    let contract = contract(vec![required_capability()]);
    let mut forged = pass_evidence(&contract);
    forged.evidence_basis = CompletionEvidenceBasis::CallerDeclared;

    let result = ProjectCompletionGate::evaluate(&contract, &[forged]);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert_eq!(result.obligations[0].status, CompletionEvidenceStatus::NotProven);
}

#[test]
fn missing_verification_reference_cannot_prove_pass() {
    let contract = contract(vec![required_capability()]);
    let mut malformed = pass_evidence(&contract);
    malformed.verification_ref = None;

    let result = ProjectCompletionGate::evaluate(&contract, &[malformed]);
    assert_eq!(result.decision, ProjectCompletionDecision::NotDone);
    assert_eq!(result.obligations[0].status, CompletionEvidenceStatus::NotProven);
}
