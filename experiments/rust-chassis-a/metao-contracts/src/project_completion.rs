use crate::project_contract::{ItemId, ProjectContract, ProjectContractBinding, ProjectContractDto};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompletionEvidenceStatus {
    Pass,
    Fail,
    NotProven,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompletionEvidenceBasis {
    IndependentAcceptance,
    VerifiedEvaluation,
    CallerDeclared,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectCompletionEvidence {
    pub evidence_id: String,
    pub obligation_id: ItemId,
    pub contract_binding: ProjectContractBinding,
    pub status: CompletionEvidenceStatus,
    pub evidence_basis: CompletionEvidenceBasis,
    pub verification_ref: Option<String>,
    pub reason: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProjectCompletionDecision {
    ProjectAccepted,
    NotDone,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObligationCompletionResult {
    pub obligation_id: ItemId,
    pub status: CompletionEvidenceStatus,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectCompletionResult {
    pub contract_binding: ProjectContractBinding,
    pub decision: ProjectCompletionDecision,
    pub obligations: Vec<ObligationCompletionResult>,
    pub reasons: Vec<String>,
}

pub struct ProjectCompletionGate;

impl ProjectCompletionGate {
    pub fn evaluate(
        contract: &ProjectContract,
        evidence: &[ProjectCompletionEvidence],
    ) -> ProjectCompletionResult {
        let binding = contract.binding();
        let dto: ProjectContractDto = contract.clone().into();
        let obligations = completion_obligations(&dto);
        let unresolved: BTreeSet<ItemId> = dto.unresolved_items.keys().cloned().collect();

        let mut indexed: BTreeMap<ItemId, Vec<&ProjectCompletionEvidence>> = BTreeMap::new();
        for record in evidence {
            if record.contract_binding == binding && valid_evidence_record(record) {
                indexed
                    .entry(record.obligation_id.clone())
                    .or_default()
                    .push(record);
            }
        }

        let mut obligation_results = Vec::new();
        let mut reasons = Vec::new();

        if obligations.is_empty() {
            reasons.push("project contract defines no completion obligations".to_string());
        }

        for obligation_id in obligations {
            let records = indexed.get(&obligation_id).cloned().unwrap_or_default();
            let result = evaluate_obligation(&obligation_id, &records);
            if result.status != CompletionEvidenceStatus::Pass {
                reasons.push(format!(
                    "obligation {} is not proven: {}",
                    obligation_id.0, result.reason
                ));
            }
            obligation_results.push(result);
        }

        if !unresolved.is_empty() {
            for item_id in unresolved {
                reasons.push(format!("unresolved contract item remains: {}", item_id.0));
            }
        }

        let decision = if reasons.is_empty() {
            ProjectCompletionDecision::ProjectAccepted
        } else {
            ProjectCompletionDecision::NotDone
        };

        ProjectCompletionResult {
            contract_binding: binding,
            decision,
            obligations: obligation_results,
            reasons,
        }
    }
}

fn valid_evidence_record(record: &ProjectCompletionEvidence) -> bool {
    if record.evidence_id.trim().is_empty()
        || record.obligation_id.0.trim().is_empty()
        || record.reason.trim().is_empty()
    {
        return false;
    }

    match record.status {
        CompletionEvidenceStatus::Pass | CompletionEvidenceStatus::Fail => {
            matches!(
                record.evidence_basis,
                CompletionEvidenceBasis::IndependentAcceptance
                    | CompletionEvidenceBasis::VerifiedEvaluation
            ) && record
                .verification_ref
                .as_deref()
                .is_some_and(|value| !value.trim().is_empty())
        }
        CompletionEvidenceStatus::NotProven => true,
    }
}

fn completion_obligations(dto: &ProjectContractDto) -> BTreeSet<ItemId> {
    let mut obligations = BTreeSet::new();
    for source in [
        &dto.required_capabilities,
        &dto.required_surfaces,
        &dto.user_requirements,
        &dto.technical_constraints,
        &dto.non_functional_requirements,
        &dto.acceptance_criteria,
        &dto.acceptance_tests,
        &dto.definition_of_done,
    ] {
        obligations.extend(source.keys().cloned());
    }
    obligations
}

fn evaluate_obligation(
    obligation_id: &ItemId,
    records: &[&ProjectCompletionEvidence],
) -> ObligationCompletionResult {
    if records.is_empty() {
        return ObligationCompletionResult {
            obligation_id: obligation_id.clone(),
            status: CompletionEvidenceStatus::NotProven,
            reason: "missing exact-binding verified evidence".to_string(),
        };
    }

    let statuses: BTreeSet<u8> = records
        .iter()
        .map(|record| match record.status {
            CompletionEvidenceStatus::Pass => 1,
            CompletionEvidenceStatus::Fail => 2,
            CompletionEvidenceStatus::NotProven => 3,
        })
        .collect();

    if statuses.len() > 1 {
        return ObligationCompletionResult {
            obligation_id: obligation_id.clone(),
            status: CompletionEvidenceStatus::NotProven,
            reason: "contradictory duplicate evidence".to_string(),
        };
    }

    let status = records[0].status;
    let reason = match status {
        CompletionEvidenceStatus::Pass => {
            "exact-binding independently verified obligation evidence passed".to_string()
        }
        CompletionEvidenceStatus::Fail => "verified obligation evidence failed".to_string(),
        CompletionEvidenceStatus::NotProven => "obligation evidence is not proven".to_string(),
    };

    ObligationCompletionResult {
        obligation_id: obligation_id.clone(),
        status,
        reason,
    }
}
