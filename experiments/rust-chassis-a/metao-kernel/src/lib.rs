use metao_contracts::{
    AcceptanceBudget, AcceptanceContext, AcceptanceDecision, AcceptanceResult, AggregationResult,
    ApprovalRecord, ApprovalRequest, BudgetReservation, ConflictDecision, ContractError, Evidence,
    EvidenceEnvelope, ExecutionRequest, ExecutionResult, ExecutionStatus, PolicyDecision,
    PolicyEffect, RequiredEvidenceSet, RuntimeId,
};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::Mutex;

fn check_provenance(
    evidence: &EvidenceEnvelope,
    context: &AcceptanceContext,
) -> Result<(), (AcceptanceDecision, &'static str)> {
    if evidence.payload_digest.is_empty() || evidence.provenance_root.is_empty() {
        return Err((AcceptanceDecision::Block, "missing_provenance"));
    }
    if !context.trusted_verifiers.is_empty()
        && !context.trusted_verifiers.contains(&evidence.verifier_id)
    {
        return Err((AcceptanceDecision::Block, "untrusted_verifier"));
    }
    if !context.trusted_provenance_roots.is_empty()
        && !context
            .trusted_provenance_roots
            .contains(&evidence.provenance_root)
    {
        return Err((AcceptanceDecision::Block, "untrusted_provenance_root"));
    }
    Ok(())
}

fn check_authority(
    evidence: &EvidenceEnvelope,
    context: &AcceptanceContext,
) -> Result<(), (AcceptanceDecision, &'static str)> {
    if evidence.authority_id.is_empty() {
        return Err((AcceptanceDecision::Block, "missing_authority"));
    }
    if !context.authorized_authorities.is_empty()
        && !context
            .authorized_authorities
            .contains(&evidence.authority_id)
    {
        return Err((AcceptanceDecision::Block, "unauthorized_authority"));
    }
    Ok(())
}

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

pub fn aggregate_evidence(
    required: &RequiredEvidenceSet,
    evidence: &[EvidenceEnvelope],
) -> AggregationResult {
    let mut by_obligation: std::collections::BTreeMap<String, &EvidenceEnvelope> =
        std::collections::BTreeMap::new();
    let mut seen_ids = std::collections::BTreeSet::new();

    for item in evidence {
        if !seen_ids.insert(item.evidence_id.clone()) {
            return AggregationResult {
                decision: AcceptanceDecision::Block,
                reasons: vec!["duplicate_evidence_id".into()],
                conflict: ConflictDecision::Duplicate,
            };
        }
        if !required.obligations.contains(&item.obligation_id) {
            return AggregationResult {
                decision: AcceptanceDecision::Block,
                reasons: vec![format!("unexpected_obligation:{}", item.obligation_id)],
                conflict: ConflictDecision::Unexpected,
            };
        }
        if let Some(existing) = by_obligation.get(&item.obligation_id) {
            let reason = if *existing == item {
                "duplicate_obligation_evidence"
            } else {
                "conflicting_obligation_evidence"
            };
            let conflict = if *existing == item {
                ConflictDecision::Duplicate
            } else {
                ConflictDecision::Conflict
            };
            return AggregationResult {
                decision: AcceptanceDecision::Block,
                reasons: vec![reason.into()],
                conflict,
            };
        }
        by_obligation.insert(item.obligation_id.clone(), item);
    }

    let seen: std::collections::BTreeSet<_> = by_obligation.keys().cloned().collect();
    let missing: Vec<_> = required.obligations.difference(&seen).cloned().collect();
    if !missing.is_empty() {
        return AggregationResult {
            decision: AcceptanceDecision::NotDone,
            reasons: missing
                .into_iter()
                .map(|name| format!("missing_obligation:{name}"))
                .collect(),
            conflict: ConflictDecision::None,
        };
    }

    let failed: Vec<_> = by_obligation
        .iter()
        .filter_map(|(name, item)| (!item.passed).then_some(name.clone()))
        .collect();
    if !failed.is_empty() {
        return AggregationResult {
            decision: AcceptanceDecision::NotDone,
            reasons: failed
                .into_iter()
                .map(|name| format!("failed_obligation:{name}"))
                .collect(),
            conflict: ConflictDecision::None,
        };
    }

    AggregationResult {
        decision: AcceptanceDecision::Accept,
        reasons: Vec::new(),
        conflict: ConflictDecision::None,
    }
}

pub fn evaluate_policy(
    policy_bundle_id: impl Into<String>,
    allowed: bool,
    require_human: bool,
    reason: impl Into<String>,
) -> PolicyDecision {
    let reason = reason.into();
    if !allowed {
        return PolicyDecision {
            effect: PolicyEffect::Deny,
            policy_bundle_id: policy_bundle_id.into(),
            reason: if reason.is_empty() {
                "policy_denied".to_string()
            } else {
                reason
            },
        };
    }
    if require_human {
        return PolicyDecision {
            effect: PolicyEffect::RequireHuman,
            policy_bundle_id: policy_bundle_id.into(),
            reason: if reason.is_empty() {
                "human_approval_required".to_string()
            } else {
                reason
            },
        };
    }
    PolicyDecision {
        effect: PolicyEffect::Allow,
        policy_bundle_id: policy_bundle_id.into(),
        reason,
    }
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

pub fn require_human(
    approval_id: impl Into<String>,
    mission_id: impl Into<String>,
    execution_id: impl Into<String>,
    subject_state_id: impl Into<String>,
    policy_bundle_id: impl Into<String>,
    reason: impl Into<String>,
) -> ApprovalRequest {
    ApprovalRequest {
        approval_id: approval_id.into(),
        mission_id: mission_id.into(),
        execution_id: execution_id.into(),
        subject_state_id: subject_state_id.into(),
        policy_bundle_id: policy_bundle_id.into(),
        reason: reason.into(),
    }
}

pub fn resume_after_approval(
    request: &ApprovalRequest,
    record: &ApprovalRecord,
) -> AcceptanceDecision {
    let bindings = [
        request.approval_id == record.approval_id,
        request.mission_id == record.mission_id,
        request.execution_id == record.execution_id,
        request.subject_state_id == record.subject_state_id,
        request.policy_bundle_id == record.policy_bundle_id,
    ];
    if bindings.iter().any(|binding| !binding) {
        return AcceptanceDecision::Block;
    }
    if record.approved {
        AcceptanceDecision::Accept
    } else {
        AcceptanceDecision::Block
    }
}

pub fn apply_confidence_after_hard_gates(
    hard_gate_decision: AcceptanceDecision,
    confidence: f64,
    threshold: f64,
) -> Result<AcceptanceDecision, ContractError> {
    if hard_gate_decision != AcceptanceDecision::Accept {
        return Ok(hard_gate_decision);
    }
    if !(0.0..=1.0).contains(&confidence) || !(0.0..=1.0).contains(&threshold) {
        return Err(ContractError::InvalidConfidence);
    }
    if confidence < threshold {
        Ok(AcceptanceDecision::RequireHuman)
    } else {
        Ok(AcceptanceDecision::Accept)
    }
}

fn budget_exhausted() -> ContractError {
    ContractError::BudgetExhausted
}

fn pending_totals(reservations: &BTreeMap<String, BudgetReservation>) -> (f64, u64, f64, u64) {
    reservations
        .values()
        .filter(|reservation| !reservation.settled)
        .fold((0.0, 0, 0.0, 0), |acc, reservation| {
            (
                acc.0 + reservation.money,
                acc.1 + reservation.tokens,
                acc.2 + reservation.wall_time_s,
                acc.3 + reservation.verifier_attempts,
            )
        })
}

pub struct AcceptanceBudgetAuthority {
    budget: Mutex<AcceptanceBudget>,
    reservations: Mutex<BTreeMap<String, BudgetReservation>>,
}

impl AcceptanceBudgetAuthority {
    pub fn new(budget: AcceptanceBudget) -> Self {
        Self {
            budget: Mutex::new(budget),
            reservations: Mutex::new(BTreeMap::new()),
        }
    }

    pub fn snapshot(&self) -> AcceptanceBudget {
        self.budget.lock().expect("budget lock").clone()
    }

    pub fn reservation(&self, reservation_id: &str) -> Option<BudgetReservation> {
        self.reservations
            .lock()
            .expect("reservations lock")
            .get(reservation_id)
            .cloned()
    }

    pub fn reserve(
        &self,
        reservation_id: impl Into<String>,
        money: f64,
        tokens: u64,
        wall_time_s: f64,
        verifier_attempts: u64,
    ) -> Result<BudgetReservation, ContractError> {
        let reservation_id = reservation_id.into();
        if reservation_id.trim().is_empty() {
            return Err(ContractError::EmptyReservationId);
        }
        if money < 0.0 || wall_time_s < 0.0 {
            return Err(ContractError::NegativeReservation);
        }

        let mut reservations = self.reservations.lock().expect("reservations lock");
        let budget = self.budget.lock().expect("budget lock");
        let requested = (money, tokens, wall_time_s, verifier_attempts);
        if let Some(existing) = reservations.get(&reservation_id) {
            if existing.request_tuple() != requested {
                return Err(ContractError::ReplayConflict);
            }
            return Ok(existing.clone());
        }

        let (pending_money, pending_tokens, pending_wall_time, pending_attempts) =
            pending_totals(&reservations);
        if budget.money_used + pending_money + money > budget.money_limit
            || budget.tokens_used + pending_tokens + tokens > budget.token_limit
            || budget.wall_time_used_s + pending_wall_time + wall_time_s > budget.wall_time_limit_s
            || budget.verifier_attempts_used + pending_attempts + verifier_attempts
                > budget.verifier_attempt_limit
        {
            return Err(budget_exhausted());
        }

        let reservation = BudgetReservation {
            reservation_id: reservation_id.clone(),
            money,
            tokens,
            wall_time_s,
            verifier_attempts,
            settled: false,
        };
        reservations.insert(reservation_id, reservation.clone());
        Ok(reservation)
    }

    pub fn settle(&self, reservation_id: &str) -> Result<AcceptanceBudget, ContractError> {
        let mut reservations = self.reservations.lock().expect("reservations lock");
        let mut budget = self.budget.lock().expect("budget lock");
        let reservation = reservations
            .get_mut(reservation_id)
            .ok_or_else(|| ContractError::UnknownReservation(reservation_id.to_string()))?;
        if reservation.settled {
            return Ok(budget.clone());
        }
        let next = budget.clone().apply_usage(
            reservation.money,
            reservation.tokens,
            reservation.wall_time_s,
            reservation.verifier_attempts,
        )?;
        *budget = next.clone();
        reservation.settled = true;
        Ok(next)
    }
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
        if by_obligation
            .insert(item.obligation_id.clone(), item)
            .is_some()
        {
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
        for gate in [
            check_provenance(item, context),
            check_authority(item, context),
        ] {
            if let Err((decision, reason)) = gate {
                return acceptance_result(
                    decision,
                    vec![reason.into()],
                    evidence
                        .iter()
                        .map(|item| item.evidence_id.clone())
                        .collect(),
                );
            }
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
