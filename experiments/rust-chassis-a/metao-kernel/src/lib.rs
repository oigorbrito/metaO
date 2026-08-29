use metao_contracts::{
    AcceptanceBudget, AcceptanceContext, AcceptanceDecision, AcceptanceResult, AggregationResult,
    ApprovalRecord, ApprovalRequest, AuthoritativeAuthorityDecision, AuthoritativePolicyBundle,
    AuthoritativeSubjectState, AuthorityRegistryPort, BudgetReservation, ConflictDecision,
    ContractError, Evidence, EvidenceEnvelope, ExecutionRequest, ExecutionResult, ExecutionStatus,
    PolicyDecision, PolicyEffect, PolicyRegistryPort, RequiredEvidenceSet, RetryHistoryKind,
    RetryHistoryPort, RetryHistoryRecord, RuntimeId, SubjectStatePort, TerminalClaims,
    VerificationAttemptId, VerificationAttemptStarted, VerificationRequest, VerificationUsage,
    VerifierDescriptor, VerifierResult,
};
use metao_registry::{VerifierRegistry, VerifierRegistryError};
use serde::{Deserialize, Serialize};
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

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum TerminalSourceDecision {
    Continue,
    Stale,
    Block,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuthoritativeTerminalSources {
    pub subject_state: AuthoritativeSubjectState,
    pub authority_resolution: AuthoritativeAuthorityDecision,
    pub policy_bundle: AuthoritativePolicyBundle,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TerminalSourceAssessment {
    pub decision: TerminalSourceDecision,
    pub reasons: Vec<String>,
    pub sources: Option<AuthoritativeTerminalSources>,
}

fn terminal_assessment(
    decision: TerminalSourceDecision,
    reasons: Vec<String>,
    sources: Option<AuthoritativeTerminalSources>,
) -> TerminalSourceAssessment {
    TerminalSourceAssessment {
        decision,
        reasons,
        sources,
    }
}

pub fn resolve_authoritative_terminal_sources(
    claims: &TerminalClaims,
    evidence: &[EvidenceEnvelope],
    subject_port: &dyn SubjectStatePort,
    authority_port: &dyn AuthorityRegistryPort,
    policy_port: &dyn PolicyRegistryPort,
) -> TerminalSourceAssessment {
    if claims.subject_id.trim().is_empty()
        || claims.subject_state_id.trim().is_empty()
        || claims.authority_context_id.trim().is_empty()
        || claims.authority_id.trim().is_empty()
        || claims.policy_bundle_id.trim().is_empty()
        || claims.policy_bundle_root.trim().is_empty()
    {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["missing_terminal_claim".into()],
            None,
        );
    }

    if evidence.is_empty() {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["missing_candidate_evidence".into()],
            None,
        );
    }

    let Some(subject_state) = subject_port.current(&claims.subject_id) else {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["missing_subject_source".into()],
            None,
        );
    };

    let Some(authority_resolution) = authority_port.resolve(&claims.authority_context_id, claims)
    else {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["missing_authority_source".into()],
            None,
        );
    };

    let Some(policy_bundle) = policy_port.get(&claims.policy_bundle_id) else {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["missing_policy_source".into()],
            None,
        );
    };

    if policy_bundle.decision.effect == PolicyEffect::Deny {
        return terminal_assessment(
            TerminalSourceDecision::Block,
            vec!["authoritative_policy_deny".into()],
            None,
        );
    }

    for item in evidence {
        if item.subject_id != claims.subject_id {
            return terminal_assessment(
                TerminalSourceDecision::Block,
                vec!["subject_id_mismatch".into()],
                None,
            );
        }
        if item.subject_state_id != claims.subject_state_id
            || item.subject_state_id != subject_state.subject_state_id
        {
            let decision = if subject_state.state_epoch as f64 > item.created_at_epoch {
                TerminalSourceDecision::Stale
            } else {
                TerminalSourceDecision::Block
            };
            return terminal_assessment(decision, vec!["subject_state_mismatch".into()], None);
        }
        if item.authority_id != claims.authority_id
            || authority_resolution.authority_id != claims.authority_id
            || authority_resolution.authority_context_id != claims.authority_context_id
        {
            let decision = if authority_resolution.authority_epoch as f64 > item.created_at_epoch {
                TerminalSourceDecision::Stale
            } else {
                TerminalSourceDecision::Block
            };
            return terminal_assessment(decision, vec!["authority_mismatch".into()], None);
        }
        if item.policy_bundle_id != claims.policy_bundle_id
            || policy_bundle.policy_bundle_id != claims.policy_bundle_id
            || policy_bundle.policy_bundle_root != claims.policy_bundle_root
        {
            let decision = if policy_bundle.bundle_epoch as f64 > item.created_at_epoch {
                TerminalSourceDecision::Stale
            } else {
                TerminalSourceDecision::Block
            };
            return terminal_assessment(decision, vec!["policy_bundle_mismatch".into()], None);
        }
        if item.provenance_root != authority_resolution.evidence_root {
            let decision = if authority_resolution.authority_epoch as f64 > item.created_at_epoch {
                TerminalSourceDecision::Stale
            } else {
                TerminalSourceDecision::Block
            };
            return terminal_assessment(
                decision,
                vec!["authority_provenance_mismatch".into()],
                None,
            );
        }
    }

    terminal_assessment(
        TerminalSourceDecision::Continue,
        Vec::new(),
        Some(AuthoritativeTerminalSources {
            subject_state,
            authority_resolution,
            policy_bundle,
        }),
    )
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

    pub fn apply_exact_usage(
        &self,
        usage: &VerificationUsage,
    ) -> Result<AcceptanceBudget, ContractError> {
        let money = usage
            .money
            .ok_or(ContractError::MissingUsageFact("money"))?;
        let tokens = usage
            .tokens
            .ok_or(ContractError::MissingUsageFact("tokens"))?;
        let wall_time_s = usage
            .wall_time_s
            .ok_or(ContractError::MissingUsageFact("wall_time"))?;
        let verifier_attempts = usage
            .verifier_attempts
            .ok_or(ContractError::MissingUsageFact("attempts"))?;
        let mut budget = self.budget.lock().expect("budget lock");
        let next = budget
            .clone()
            .apply_usage(money, tokens, wall_time_s, verifier_attempts)?;
        *budget = next.clone();
        Ok(next)
    }
}

fn verification_attempt_key(started: &VerificationAttemptStarted) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}|{:016x}",
        started.request_id.as_str(),
        started.attempt_id.as_str(),
        started.mission_id.as_str(),
        started.execution_id.as_str(),
        started.verifier_id.as_str(),
        started.verifier_version,
        started.started_at_epoch.to_bits()
    )
}

pub struct VerificationAccountingAuthority {
    budget: AcceptanceBudgetAuthority,
    attempts: Mutex<BTreeMap<VerificationAttemptId, VerificationAttemptStarted>>,
    attempt_facts: Mutex<BTreeSet<String>>,
    usages: Mutex<BTreeMap<VerificationAttemptId, VerificationUsage>>,
    retry_history: Mutex<
        BTreeMap<
            (metao_contracts::MissionId, metao_contracts::ExecutionId),
            Vec<RetryHistoryRecord>,
        >,
    >,
    retry_record_ids: Mutex<BTreeSet<String>>,
}

impl VerificationAccountingAuthority {
    pub fn new(budget: AcceptanceBudget) -> Self {
        Self {
            budget: AcceptanceBudgetAuthority::new(budget),
            attempts: Mutex::new(BTreeMap::new()),
            attempt_facts: Mutex::new(BTreeSet::new()),
            usages: Mutex::new(BTreeMap::new()),
            retry_history: Mutex::new(BTreeMap::new()),
            retry_record_ids: Mutex::new(BTreeSet::new()),
        }
    }

    pub fn budget(&self) -> AcceptanceBudget {
        self.budget.snapshot()
    }

    pub fn attempt_started(
        &self,
        attempt_id: &VerificationAttemptId,
    ) -> Option<VerificationAttemptStarted> {
        self.attempts
            .lock()
            .expect("attempts lock")
            .get(attempt_id)
            .cloned()
    }

    pub fn usage(&self, attempt_id: &VerificationAttemptId) -> Option<VerificationUsage> {
        self.usages
            .lock()
            .expect("usages lock")
            .get(attempt_id)
            .cloned()
    }

    pub fn retry_history(
        &self,
        mission_id: &metao_contracts::MissionId,
        execution_id: &metao_contracts::ExecutionId,
    ) -> Option<Vec<RetryHistoryRecord>> {
        self.retry_history
            .lock()
            .expect("retry_history lock")
            .get(&(mission_id.clone(), execution_id.clone()))
            .cloned()
    }

    fn append_retry_history_record(&self, record: RetryHistoryRecord) -> Result<(), ContractError> {
        if record.record_id.trim().is_empty() {
            return Err(ContractError::EmptyIdentity("retry_history_record_id"));
        }

        let scope = (record.mission_id.clone(), record.execution_id.clone());
        let mut history_by_scope = self.retry_history.lock().expect("retry_history lock");
        let history = history_by_scope.entry(scope).or_default();
        let expected_sequence = history.len() as u64;
        if record.sequence != expected_sequence {
            return Err(ContractError::RetryHistorySequenceGap {
                expected: expected_sequence,
                actual: record.sequence,
            });
        }

        let mut record_ids = self.retry_record_ids.lock().expect("retry_record_ids lock");
        if record_ids.contains(&record.record_id) {
            return Err(ContractError::RetryHistoryDuplicateRecord(
                record.record_id.clone(),
            ));
        }

        match &record.kind {
            RetryHistoryKind::AttemptStarted => {
                let Some(started) = record.attempt_started.as_ref() else {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                };
                if started.mission_id != record.mission_id
                    || started.execution_id != record.execution_id
                    || started.attempt_id != record.attempt_id
                {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                }
                let mut attempts = self.attempts.lock().expect("attempts lock");
                if attempts.contains_key(&record.attempt_id) {
                    return Err(ContractError::DuplicateVerificationAttempt(
                        record.attempt_id.as_str().to_string(),
                    ));
                }
                let mut attempt_facts = self.attempt_facts.lock().expect("attempt facts lock");
                let fact_key = verification_attempt_key(started);
                if !attempt_facts.insert(fact_key.clone()) {
                    return Err(ContractError::DuplicateFactualAttempt(fact_key));
                }
                attempts.insert(record.attempt_id.clone(), started.clone());
            }
            RetryHistoryKind::UsageRecorded => {
                let Some(usage) = record.usage.as_ref() else {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                };
                if usage.attempt_id != record.attempt_id {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                }
                let attempts = self.attempts.lock().expect("attempts lock");
                let Some(started) = attempts.get(&record.attempt_id) else {
                    return Err(ContractError::InvalidVerificationBinding);
                };
                if started.mission_id != record.mission_id
                    || started.execution_id != record.execution_id
                {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                }
                drop(attempts);
                let mut usages = self.usages.lock().expect("usages lock");
                if usages.contains_key(&record.attempt_id) {
                    return Err(ContractError::DuplicateVerificationAttempt(
                        record.attempt_id.as_str().to_string(),
                    ));
                }
                usages.insert(record.attempt_id.clone(), usage.clone());
            }
            RetryHistoryKind::RecoveryObserved => {
                if record.recovery_from_attempt_id.is_none() || record.recovery_outcome.is_none() {
                    return Err(ContractError::RetryHistoryBindingMismatch);
                }
            }
        }

        record_ids.insert(record.record_id.clone());
        history.push(record);
        Ok(())
    }

    pub fn replay_history(&self, records: &[RetryHistoryRecord]) -> Result<(), ContractError> {
        for record in records {
            self.append_retry_history_record(record.clone())?;
            if let (RetryHistoryKind::UsageRecorded, Some(usage)) = (&record.kind, &record.usage) {
                self.budget.apply_exact_usage(usage)?;
            }
        }
        Ok(())
    }

    pub fn start_attempt(&self, started: VerificationAttemptStarted) -> Result<(), ContractError> {
        let attempts = self.attempts.lock().expect("attempts lock");
        if attempts.contains_key(&started.attempt_id) {
            return Err(ContractError::DuplicateVerificationAttempt(
                started.attempt_id.as_str().to_string(),
            ));
        }
        drop(attempts);
        let record = RetryHistoryRecord {
            record_id: verification_attempt_key(&started),
            mission_id: started.mission_id.clone(),
            execution_id: started.execution_id.clone(),
            attempt_id: started.attempt_id.clone(),
            sequence: self
                .retry_history
                .lock()
                .expect("retry_history lock")
                .get(&(started.mission_id.clone(), started.execution_id.clone()))
                .map(|history| history.len() as u64)
                .unwrap_or(0),
            kind: RetryHistoryKind::AttemptStarted,
            attempt_started: Some(started),
            recovery_from_attempt_id: None,
            recovery_outcome: None,
            usage: None,
        };
        self.append_retry_history_record(record)
    }

    pub fn record_usage(&self, usage: VerificationUsage) -> Result<(), ContractError> {
        let started = self
            .attempt_started(&usage.attempt_id)
            .ok_or(ContractError::InvalidVerificationBinding)?;
        let record = RetryHistoryRecord {
            record_id: format!("usage:{}", usage.attempt_id.as_str()),
            mission_id: started.mission_id.clone(),
            execution_id: started.execution_id.clone(),
            attempt_id: usage.attempt_id.clone(),
            sequence: self
                .retry_history
                .lock()
                .expect("retry_history lock")
                .get(&(started.mission_id.clone(), started.execution_id.clone()))
                .map(|history| history.len() as u64)
                .unwrap_or(0),
            kind: RetryHistoryKind::UsageRecorded,
            attempt_started: None,
            recovery_from_attempt_id: None,
            recovery_outcome: None,
            usage: Some(usage),
        };
        if !self
            .attempts
            .lock()
            .expect("attempts lock")
            .contains_key(&record.attempt_id)
        {
            return Err(ContractError::InvalidVerificationBinding);
        }
        self.append_retry_history_record(record)
    }

    pub fn apply_usage(
        &self,
        usage: &VerificationUsage,
    ) -> Result<AcceptanceBudget, ContractError> {
        self.budget.apply_exact_usage(usage)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VerificationExecutionOutcome {
    pub attempt_started: VerificationAttemptStarted,
    pub verifier_result: VerifierResult,
    pub budget: AcceptanceBudget,
}

fn binding_matches(
    request: &VerificationRequest,
    descriptor: &VerifierDescriptor,
    result: &VerifierResult,
) -> bool {
    result.request_id == request.request_id
        && result.attempt_id == request.attempt_id
        && result.verifier_id == descriptor.verifier_id
        && result.verifier_version == descriptor.version
}

pub fn execute_verification(
    registry: &VerifierRegistry,
    accounting: &VerificationAccountingAuthority,
    request: VerificationRequest,
    started_at_epoch: f64,
) -> Result<VerificationExecutionOutcome, ContractError> {
    let descriptor = registry
        .select_eligible(&request.capability)
        .ok_or_else(|| ContractError::UnknownVerifier(request.capability.clone()))?;
    let started = VerificationAttemptStarted {
        request_id: request.request_id.clone(),
        attempt_id: request.attempt_id.clone(),
        mission_id: request.mission_id.clone(),
        execution_id: request.execution_id.clone(),
        verifier_id: descriptor.verifier_id.clone(),
        verifier_version: descriptor.version.clone(),
        started_at_epoch,
    };
    accounting.start_attempt(started.clone())?;
    let verifier_result = match registry.execute_contained(&descriptor.verifier_id, &request) {
        Ok(result) => result,
        Err(VerifierRegistryError::Duplicate(id)) => {
            return Err(ContractError::DuplicateVerifier(id.as_str().to_string()))
        }
        Err(VerifierRegistryError::VersionConflict {
            id,
            existing,
            incoming,
        }) => {
            return Err(ContractError::VerifierVersionConflict {
                id: id.as_str().to_string(),
                existing,
                incoming,
            })
        }
        Err(VerifierRegistryError::NotFound(id)) => {
            return Err(ContractError::UnknownVerifier(id.as_str().to_string()))
        }
        Err(VerifierRegistryError::Panicked(id)) => {
            return Err(ContractError::VerificationPanic(id.as_str().to_string()))
        }
    };
    if !binding_matches(&request, &descriptor, &verifier_result) {
        return Err(ContractError::InvalidVerificationBinding);
    }
    accounting.record_usage(verifier_result.usage.clone())?;
    let budget = accounting.apply_usage(&verifier_result.usage)?;
    Ok(VerificationExecutionOutcome {
        attempt_started: started,
        verifier_result,
        budget,
    })
}

pub fn validate_retry_history_projection(
    history_port: &dyn RetryHistoryPort,
    mission_id: &metao_contracts::MissionId,
    execution_id: &metao_contracts::ExecutionId,
    caller_history: &[RetryHistoryRecord],
) -> Result<(), ContractError> {
    let Some(authoritative_history) = history_port.history(mission_id, execution_id) else {
        return Err(ContractError::MissingRetryHistorySource);
    };

    if authoritative_history.len() != caller_history.len() {
        return Err(ContractError::RetryHistoryProjectionMismatch);
    }

    for (index, (authoritative, caller)) in authoritative_history
        .iter()
        .zip(caller_history.iter())
        .enumerate()
    {
        let expected_sequence = index as u64;
        if authoritative.sequence != expected_sequence || caller.sequence != expected_sequence {
            return Err(ContractError::RetryHistorySequenceGap {
                expected: expected_sequence,
                actual: caller.sequence,
            });
        }
        if authoritative.mission_id != *mission_id
            || authoritative.execution_id != *execution_id
            || caller.mission_id != *mission_id
            || caller.execution_id != *execution_id
        {
            return Err(ContractError::RetryHistoryBindingMismatch);
        }
        if authoritative.record_id != caller.record_id
            || authoritative.attempt_id != caller.attempt_id
            || authoritative.kind != caller.kind
            || authoritative.attempt_started != caller.attempt_started
            || authoritative.recovery_from_attempt_id != caller.recovery_from_attempt_id
            || authoritative.recovery_outcome != caller.recovery_outcome
            || authoritative.usage != caller.usage
        {
            return Err(ContractError::RetryHistoryProjectionMismatch);
        }
    }

    Ok(())
}

impl RetryHistoryPort for VerificationAccountingAuthority {
    fn append(&self, record: RetryHistoryRecord) -> Result<(), ContractError> {
        self.append_retry_history_record(record)
    }

    fn history(
        &self,
        mission_id: &metao_contracts::MissionId,
        execution_id: &metao_contracts::ExecutionId,
    ) -> Option<Vec<RetryHistoryRecord>> {
        VerificationAccountingAuthority::retry_history(self, mission_id, execution_id)
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

pub fn replay_acceptance_decision(
    proof: &metao_contracts::AcceptanceProof,
) -> Result<AcceptanceDecision, ContractError> {
    let expected = digest_payload(proof.decision, &proof.reasons, &proof.evidence_ids);
    if expected != proof.digest {
        return Err(ContractError::AcceptanceProofDigestMismatch);
    }
    Ok(proof.decision)
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
