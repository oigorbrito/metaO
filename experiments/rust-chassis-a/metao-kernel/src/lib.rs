use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, AcceptanceResult, Evidence, EvidenceEnvelope,
    ExecutionRequest, ExecutionResult, ExecutionStatus, PolicyEffect, RuntimeId,
};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

pub fn evaluate_acceptance(
    request: &ExecutionRequest,
    result: &ExecutionResult,
    evidence: Option<&Evidence>,
    policy: PolicyEffect,
    now_epoch: i64,
) -> AcceptanceDecision {
    if matches!(policy, PolicyEffect::Deny) {
        return AcceptanceDecision::Block;
    }

    if !matches!(result.status, ExecutionStatus::Succeeded) {
        return AcceptanceDecision::NotDone;
    }

    let Some(evidence) = evidence else {
        return AcceptanceDecision::NotDone;
    };

    if !evidence.verified
        || evidence.mission_id != request.mission_id
        || evidence.execution_id != request.execution_id
        || evidence.execution_id != result.execution_id
        || evidence.runtime_id != result.runtime_id
    {
        return AcceptanceDecision::Block;
    }

    if now_epoch < evidence.created_at_epoch {
        return AcceptanceDecision::Block;
    }

    if now_epoch > evidence.expires_at_epoch {
        return AcceptanceDecision::Stale;
    }

    AcceptanceDecision::Accept
}

pub fn reconcile_missing(desired: &[RuntimeId], observed: &[RuntimeId]) -> Vec<RuntimeId> {
    let mut missing: Vec<_> = desired
        .iter()
        .filter(|runtime| !observed.contains(runtime))
        .cloned()
        .collect();
    missing.sort();
    missing.dedup();
    missing
}

fn decision_value(decision: AcceptanceDecision) -> &'static str {
    match decision {
        AcceptanceDecision::Accept => "ACCEPT",
        AcceptanceDecision::Block => "BLOCK",
        AcceptanceDecision::NotDone => "NOT_DONE",
        AcceptanceDecision::Stale => "STALE",
        AcceptanceDecision::RequireHuman => "REQUIRE_HUMAN",
    }
}

fn digest_payload(
    decision: AcceptanceDecision,
    reasons: &[String],
    evidence_ids: &[String],
) -> String {
    let payload = json!({
        "decision": decision_value(decision),
        "reasons": reasons,
        "evidence_ids": evidence_ids,
    });
    let bytes = serde_json::to_vec(&payload).expect("stable acceptance digest");
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn acceptance_result(
    decision: AcceptanceDecision,
    reasons: Vec<String>,
    evidence_ids: Vec<String>,
) -> AcceptanceResult {
    let mut evidence_ids = evidence_ids;
    evidence_ids.sort();
    let digest = digest_payload(decision, &reasons, &evidence_ids);
    AcceptanceResult {
        proof: Some(metao_contracts::AcceptanceProof {
            decision,
            reasons: reasons.clone(),
            evidence_ids: evidence_ids.clone(),
            digest,
        }),
        decision,
        reasons,
    }
}

pub fn canonical_acceptance(
    context: &AcceptanceContext,
    evidence: &[EvidenceEnvelope],
    now_epoch: f64,
) -> AcceptanceResult {
    let mut seen_ids = BTreeSet::new();
    let mut by_obligation: BTreeMap<String, &EvidenceEnvelope> = BTreeMap::new();
    let required: BTreeSet<_> = context.required_obligations.iter().cloned().collect();

    for item in evidence {
        if !seen_ids.insert(item.evidence_id.clone()) {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["duplicate_evidence_id".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if !required.contains(&item.obligation_id) {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["unknown_obligation".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if by_obligation.insert(item.obligation_id.clone(), item).is_some() {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["duplicate_or_conflicting_obligation_evidence".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.subject_id != context.subject_id {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["subject_mismatch".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.subject_state_id != context.subject_state_id {
            return acceptance_result(
                AcceptanceDecision::Stale,
                vec!["subject_state_mismatch".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.verification_context_id != context.verification_context_id {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["verification_context_mismatch".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.policy_bundle_id != context.policy_bundle_id {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["policy_bundle_mismatch".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item
            .expires_at_epoch
            .is_some_and(|expires| now_epoch > expires)
        {
            return acceptance_result(
                AcceptanceDecision::Stale,
                vec!["evidence_expired".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.created_at_epoch != 0.0 && item.created_at_epoch > now_epoch {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["evidence_from_future".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.payload_digest.is_empty() || item.provenance_root.is_empty() {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["missing_provenance".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if !context.trusted_verifiers.is_empty()
            && !context.trusted_verifiers.contains(&item.verifier_id)
        {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["untrusted_verifier".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if !context.trusted_provenance_roots.is_empty()
            && !context
                .trusted_provenance_roots
                .contains(&item.provenance_root)
        {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["untrusted_provenance_root".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if item.authority_id.is_empty() {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["missing_authority".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
        if !context.authorized_authorities.is_empty()
            && !context.authorized_authorities.contains(&item.authority_id)
        {
            return acceptance_result(
                AcceptanceDecision::Block,
                vec!["unauthorized_authority".into()],
                evidence
                    .iter()
                    .map(|item| item.evidence_id.clone())
                    .collect(),
            );
        }
    }

    let seen: BTreeSet<_> = by_obligation.keys().cloned().collect();
    let missing: Vec<_> = required.difference(&seen).cloned().collect();
    if !missing.is_empty() {
        return acceptance_result(
            AcceptanceDecision::NotDone,
            missing
                .into_iter()
                .map(|name| format!("missing_obligation:{name}"))
                .collect(),
            evidence
                .iter()
                .map(|item| item.evidence_id.clone())
                .collect(),
        );
    }

    let failed: Vec<_> = by_obligation
        .iter()
        .filter_map(|(name, item)| (!item.passed).then_some(name.clone()))
        .collect();
    if !failed.is_empty() {
        return acceptance_result(
            AcceptanceDecision::NotDone,
            failed
                .into_iter()
                .map(|name| format!("failed_obligation:{name}"))
                .collect(),
            evidence
                .iter()
                .map(|item| item.evidence_id.clone())
                .collect(),
        );
    }

    acceptance_result(
        AcceptanceDecision::Accept,
        Vec::new(),
        evidence
            .iter()
            .map(|item| item.evidence_id.clone())
            .collect(),
    )
}

#[cfg(test)]
mod tests {
    use super::evaluate_acceptance;
    use metao_contracts::{
        AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult,
        ExecutionStatus, MissionId, PolicyEffect, RuntimeId,
    };

    fn request() -> ExecutionRequest {
        ExecutionRequest {
            execution_id: ExecutionId::new("exec-1").unwrap(),
            mission_id: MissionId::new("mission-1").unwrap(),
        }
    }

    fn result() -> ExecutionResult {
        ExecutionResult {
            execution_id: ExecutionId::new("exec-1").unwrap(),
            runtime_id: RuntimeId::new("runtime-1").unwrap(),
            status: ExecutionStatus::Succeeded,
        }
    }

    fn evidence() -> Evidence {
        Evidence {
            mission_id: MissionId::new("mission-1").unwrap(),
            execution_id: ExecutionId::new("exec-1").unwrap(),
            runtime_id: RuntimeId::new("runtime-1").unwrap(),
            policy_version: "policy-1".into(),
            verified: true,
            created_at_epoch: 10,
            expires_at_epoch: 20,
        }
    }

    #[test]
    fn unverified_exact_binding_is_blocked() {
        let mut item = evidence();
        item.verified = false;
        assert_eq!(
            evaluate_acceptance(&request(), &result(), Some(&item), PolicyEffect::Allow, 15,),
            AcceptanceDecision::Block,
        );
    }

    #[test]
    fn evidence_from_future_is_blocked_like_python_oracle() {
        assert_eq!(
            evaluate_acceptance(
                &request(),
                &result(),
                Some(&evidence()),
                PolicyEffect::Allow,
                9,
            ),
            AcceptanceDecision::Block,
        );
    }

    #[test]
    fn evidence_is_valid_at_creation_boundary() {
        assert_eq!(
            evaluate_acceptance(
                &request(),
                &result(),
                Some(&evidence()),
                PolicyEffect::Allow,
                10,
            ),
            AcceptanceDecision::Accept,
        );
    }

    #[test]
    fn evidence_is_valid_at_expiry_boundary() {
        assert_eq!(
            evaluate_acceptance(
                &request(),
                &result(),
                Some(&evidence()),
                PolicyEffect::Allow,
                20,
            ),
            AcceptanceDecision::Accept,
        );
    }
}
