use serde::{Deserialize, Serialize};

use crate::failure_causality::{
    evaluate_retry_eligibility, FailureCausalityFacts, RetryEligibility,
};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthError {
    BlankRuntimeIdentity,
    BlankRuntimeVersion,
    BlankConfigIdentity,
    BlankEvidenceRef,
    InvalidEvidenceBasis,
    InvalidObservationWindow,
    InvalidCounters,
    InvalidPolicy,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthState {
    Unknown,
    Healthy,
    Degraded,
    Unhealthy,
    Quarantined,
    Recovering,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthEvidenceBasis {
    IndependentObservation,
    AdapterVerified,
    SelfReported,
    Unknown,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeHealthPolicy {
    pub quarantine_consecutive_failures: u32,
    pub unhealthy_failure_percent: u8,
    pub recovery_successes_required: u32,
    pub retry_pressure_limit: u32,
}
impl RuntimeHealthPolicy {
    pub fn validate(&self) -> Result<(), RuntimeHealthError> {
        if self.quarantine_consecutive_failures == 0
            || self.recovery_successes_required == 0
            || self.unhealthy_failure_percent == 0
            || self.unhealthy_failure_percent > 100
        {
            Err(RuntimeHealthError::InvalidPolicy)
        } else {
            Ok(())
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeHealthObservation {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub evidence_basis: RuntimeHealthEvidenceBasis,
    pub evidence_ref: String,
    pub window_start_sequence: u64,
    pub window_end_sequence: u64,
    pub attempts: u32,
    pub successes: u32,
    pub failures: u32,
    pub consecutive_failures: u32,
    pub timeouts: u32,
    pub transport_failures: u32,
    pub active_retries: u32,
    pub fresh_successes_since_unhealthy: u32,
    pub prior_state: Option<RuntimeHealthState>,
    pub self_reported_healthy: Option<bool>,
}
impl RuntimeHealthObservation {
    pub fn validate(&self) -> Result<(), RuntimeHealthError> {
        if self.runtime_id.trim().is_empty() {
            return Err(RuntimeHealthError::BlankRuntimeIdentity);
        }
        if self.runtime_version.trim().is_empty() {
            return Err(RuntimeHealthError::BlankRuntimeVersion);
        }
        if self.config_id.trim().is_empty() {
            return Err(RuntimeHealthError::BlankConfigIdentity);
        }
        if self.evidence_ref.trim().is_empty() {
            return Err(RuntimeHealthError::BlankEvidenceRef);
        }
        if self.window_end_sequence < self.window_start_sequence {
            return Err(RuntimeHealthError::InvalidObservationWindow);
        }
        if self.successes.checked_add(self.failures) != Some(self.attempts)
            || self.consecutive_failures > self.failures
            || self.timeouts > self.failures
            || self.transport_failures > self.failures
            || self.fresh_successes_since_unhealthy > self.successes
        {
            return Err(RuntimeHealthError::InvalidCounters);
        }
        if self.attempts == 0 {
            if self.evidence_basis != RuntimeHealthEvidenceBasis::Unknown {
                return Err(RuntimeHealthError::InvalidEvidenceBasis);
            }
        } else if !matches!(
            self.evidence_basis,
            RuntimeHealthEvidenceBasis::IndependentObservation
                | RuntimeHealthEvidenceBasis::AdapterVerified
        ) {
            return Err(RuntimeHealthError::InvalidEvidenceBasis);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeHealthProjection {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub state: RuntimeHealthState,
    pub attempts: u32,
    pub successes: u32,
    pub failures: u32,
    pub consecutive_failures: u32,
    pub timeouts: u32,
    pub transport_failures: u32,
    pub active_retries: u32,
    pub retry_pressure_exceeded: bool,
    pub self_reported_healthy: Option<bool>,
    pub reasons: Vec<String>,
}
pub fn derive_runtime_health(
    observation: &RuntimeHealthObservation,
    policy: &RuntimeHealthPolicy,
) -> Result<RuntimeHealthProjection, RuntimeHealthError> {
    observation.validate()?;
    policy.validate()?;
    let retry_pressure_exceeded = observation.active_retries > policy.retry_pressure_limit;
    let mut reasons = Vec::new();
    let state = if observation.attempts == 0 {
        reasons.push("no factual execution observations in window".into());
        RuntimeHealthState::Unknown
    } else if observation.consecutive_failures >= policy.quarantine_consecutive_failures {
        reasons.push(format!(
            "consecutive failures {} reached quarantine threshold {}",
            observation.consecutive_failures, policy.quarantine_consecutive_failures
        ));
        RuntimeHealthState::Quarantined
    } else {
        let failure_scaled = u64::from(observation.failures) * 100;
        let unhealthy_scaled =
            u64::from(observation.attempts) * u64::from(policy.unhealthy_failure_percent);
        if failure_scaled >= unhealthy_scaled {
            reasons.push(format!(
                "failure ratio {}/{} reached unhealthy threshold {}%",
                observation.failures, observation.attempts, policy.unhealthy_failure_percent
            ));
            RuntimeHealthState::Unhealthy
        } else if matches!(
            observation.prior_state,
            Some(RuntimeHealthState::Quarantined)
                | Some(RuntimeHealthState::Unhealthy)
                | Some(RuntimeHealthState::Recovering)
        ) {
            if observation.failures == 0
                && observation.fresh_successes_since_unhealthy >= policy.recovery_successes_required
            {
                reasons.push(format!(
                    "fresh successes {} satisfied recovery threshold {}",
                    observation.fresh_successes_since_unhealthy, policy.recovery_successes_required
                ));
                RuntimeHealthState::Healthy
            } else {
                reasons.push(format!(
                    "runtime is recovering; fresh successes {}/{}",
                    observation.fresh_successes_since_unhealthy, policy.recovery_successes_required
                ));
                RuntimeHealthState::Recovering
            }
        } else if observation.failures > 0
            || observation.timeouts > 0
            || observation.transport_failures > 0
            || retry_pressure_exceeded
        {
            if observation.failures > 0 {
                reasons.push(format!(
                    "{} factual failure(s) observed below unhealthy/quarantine thresholds",
                    observation.failures
                ));
            }
            if retry_pressure_exceeded {
                reasons.push(format!(
                    "active retries {} exceed configured pressure limit {}",
                    observation.active_retries, policy.retry_pressure_limit
                ));
            }
            RuntimeHealthState::Degraded
        } else {
            reasons.push("factual observations are currently healthy".into());
            RuntimeHealthState::Healthy
        }
    };
    if observation.self_reported_healthy == Some(true) && state != RuntimeHealthState::Healthy {
        reasons.push("runtime self-report healthy=true did not override factual state".into());
    }
    Ok(RuntimeHealthProjection {
        runtime_id: observation.runtime_id.clone(),
        runtime_version: observation.runtime_version.clone(),
        config_id: observation.config_id.clone(),
        state,
        attempts: observation.attempts,
        successes: observation.successes,
        failures: observation.failures,
        consecutive_failures: observation.consecutive_failures,
        timeouts: observation.timeouts,
        transport_failures: observation.transport_failures,
        active_retries: observation.active_retries,
        retry_pressure_exceeded,
        self_reported_healthy: observation.self_reported_healthy,
        reasons,
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum BoundedRetryEligibility {
    Eligible,
    Ineligible,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundedRetryProjection {
    pub eligibility: BoundedRetryEligibility,
    pub next_attempt: Option<u64>,
    pub health_state: RuntimeHealthState,
    pub retry_pressure_exceeded: bool,
    pub reason: String,
}
pub fn evaluate_bounded_retry(
    facts: &FailureCausalityFacts,
    observation: &RuntimeHealthObservation,
    policy: &RuntimeHealthPolicy,
) -> Result<BoundedRetryProjection, RuntimeHealthError> {
    let health = derive_runtime_health(observation, policy)?;
    let causal = evaluate_retry_eligibility(facts);
    let blocked = |reason: String| BoundedRetryProjection {
        eligibility: BoundedRetryEligibility::Ineligible,
        next_attempt: None,
        health_state: health.state,
        retry_pressure_exceeded: health.retry_pressure_exceeded,
        reason,
    };
    if causal.eligibility == RetryEligibility::Ineligible {
        return Ok(blocked(format!(
            "retry causality gate blocked: {}",
            causal.reason
        )));
    }
    if health.retry_pressure_exceeded {
        return Ok(blocked("runtime retry pressure limit is exceeded".into()));
    }
    Ok(match health.state{RuntimeHealthState::Healthy|RuntimeHealthState::Degraded=>BoundedRetryProjection{eligibility:BoundedRetryEligibility::Eligible,next_attempt:causal.next_attempt,health_state:health.state,retry_pressure_exceeded:false,reason:"causal retry is eligible and factual runtime retry pressure is bounded".into()},RuntimeHealthState::Recovering=>blocked("recovering runtime is not eligible for ordinary retry; controlled recovery authority is required".into()),RuntimeHealthState::Unknown=>blocked("unknown runtime health cannot be treated as a fresh healthy retry target".into()),RuntimeHealthState::Unhealthy|RuntimeHealthState::Quarantined=>blocked("unhealthy or quarantined runtime is not eligible for ordinary retry".into())})
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryProbeIntentAuthority {
    pub intent_id: String,
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub authority_generation: u64,
    pub fencing_token: u64,
    pub evidence_ref: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryProbeIntentClaim {
    pub intent_id: String,
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub authority_generation: u64,
    pub fencing_token: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryProbeIntentError {
    InvalidAuthority,
    BindingMismatch,
    StaleAuthority,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundRecoveryProbeIntent {
    pub intent_id: String,
    pub execution_id: crate::ExecutionId,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub authority_generation: u64,
    pub fencing_token: u64,
    pub evidence_ref: String,
}
pub fn bind_recovery_probe_intent(
    claim: &RecoveryProbeIntentClaim,
    authority: &RecoveryProbeIntentAuthority,
    current_generation: u64,
    current_fencing_token: u64,
) -> Result<BoundRecoveryProbeIntent, RecoveryProbeIntentError> {
    if authority.intent_id.trim().is_empty()
        || authority.runtime_id.trim().is_empty()
        || authority.runtime_version.trim().is_empty()
        || authority.config_id.trim().is_empty()
        || authority.evidence_ref.trim().is_empty()
        || authority.authority_generation == 0
        || authority.fencing_token == 0
    {
        return Err(RecoveryProbeIntentError::InvalidAuthority);
    }
    if authority.authority_generation != current_generation
        || authority.fencing_token != current_fencing_token
    {
        return Err(RecoveryProbeIntentError::StaleAuthority);
    }
    if claim.intent_id != authority.intent_id
        || claim.mission_id != authority.mission_id
        || claim.execution_id != authority.execution_id
        || claim.runtime_id != authority.runtime_id
        || claim.runtime_version != authority.runtime_version
        || claim.config_id != authority.config_id
        || claim.authority_generation != authority.authority_generation
        || claim.fencing_token != authority.fencing_token
    {
        return Err(RecoveryProbeIntentError::BindingMismatch);
    }
    Ok(BoundRecoveryProbeIntent {
        intent_id: authority.intent_id.clone(),
        execution_id: authority.execution_id.clone(),
        runtime_id: authority.runtime_id.clone(),
        runtime_version: authority.runtime_version.clone(),
        config_id: authority.config_id.clone(),
        authority_generation: authority.authority_generation,
        fencing_token: authority.fencing_token,
        evidence_ref: authority.evidence_ref.clone(),
    })
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryProbeApprovalContext {
    pub mission_id: crate::MissionId,
    pub execution_id: crate::ExecutionId,
    pub subject_state_id: String,
    pub policy_bundle_id: String,
    pub action: String,
    pub target: String,
    pub scope: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryProbeGovernanceProjection {
    pub policy_denied: bool,
    pub risk_stopped: bool,
    pub budget_blocked: bool,
    pub human_approval_required: bool,
    pub human_approval_satisfied: bool,
    pub budget_version: u64,
    pub decision: crate::execution_governance::ExecutionGateDecision,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryProbeGovernanceError {
    IntentBindingMismatch,
    InvalidApprovalContext,
}
#[allow(clippy::too_many_arguments)]
pub fn project_recovery_probe_governance(
    intent: &BoundRecoveryProbeIntent,
    policy: crate::execution_governance::ExecutionPolicyEffect,
    risk: crate::execution_governance::ExecutionRiskDecision,
    accounting: &crate::execution_governance::ExecutionAccountingAuthority,
    requested: &crate::execution_governance::ExecutionUsage,
    candidate_approval: Option<&crate::ApprovalAuthorityTicket>,
    approval_port: &dyn crate::ApprovalAuthorityPort,
    context: &RecoveryProbeApprovalContext,
    now_epoch: f64,
) -> Result<RecoveryProbeGovernanceProjection, RecoveryProbeGovernanceError> {
    if intent.execution_id != context.execution_id {
        return Err(RecoveryProbeGovernanceError::IntentBindingMismatch);
    }
    if context.action != "recovery_probe"
        || context.scope.trim().is_empty()
        || context.target.trim().is_empty()
    {
        return Err(RecoveryProbeGovernanceError::InvalidApprovalContext);
    }
    let snapshot = accounting.snapshot();
    let mut effective = snapshot.budget.clone();
    effective.money_used += snapshot.reserved.money;
    effective.wall_time_used_s += snapshot.reserved.wall_time_s;
    effective.tokens_used = effective
        .tokens_used
        .saturating_add(snapshot.reserved.tokens);
    effective.attempts_used = effective
        .attempts_used
        .saturating_add(snapshot.reserved.attempts);
    let generic_context = crate::execution_governance::RetryApprovalContext {
        mission_id: context.mission_id.clone(),
        execution_id: context.execution_id.clone(),
        subject_state_id: context.subject_state_id.clone(),
        policy_bundle_id: context.policy_bundle_id.clone(),
        action: context.action.clone(),
        target: context.target.clone(),
        scope: context.scope.clone(),
    };
    let generic = crate::execution_governance::project_retry_governance(
        policy,
        risk,
        &effective,
        requested,
        candidate_approval,
        approval_port,
        &generic_context,
        now_epoch,
    );
    Ok(RecoveryProbeGovernanceProjection {
        policy_denied: generic.policy_denied,
        risk_stopped: generic.risk_stopped,
        budget_blocked: generic.budget_blocked,
        human_approval_required: generic.human_approval_required,
        human_approval_satisfied: generic.human_approval_satisfied,
        budget_version: snapshot.version,
        decision: generic.decision,
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryProbeEligibility {
    Eligible,
    Ineligible,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RecoveryProbeEligibilityProjection {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub health_state: RuntimeHealthState,
    pub eligibility: RecoveryProbeEligibility,
    pub budget_version: u64,
    pub reason: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecoveryProbeEligibilityError {
    IntentHealthBindingMismatch,
}
pub fn evaluate_controlled_recovery_probe(
    intent: &BoundRecoveryProbeIntent,
    governance: &RecoveryProbeGovernanceProjection,
    observation: &RuntimeHealthObservation,
    policy: &RuntimeHealthPolicy,
) -> Result<RecoveryProbeEligibilityProjection, RecoveryProbeEligibilityError> {
    if intent.runtime_id != observation.runtime_id
        || intent.runtime_version != observation.runtime_version
        || intent.config_id != observation.config_id
    {
        return Err(RecoveryProbeEligibilityError::IntentHealthBindingMismatch);
    }
    let health = match derive_runtime_health(observation, policy) {
        Ok(v) => v,
        Err(_) => {
            return Ok(RecoveryProbeEligibilityProjection {
                runtime_id: intent.runtime_id.clone(),
                runtime_version: intent.runtime_version.clone(),
                config_id: intent.config_id.clone(),
                health_state: RuntimeHealthState::Unknown,
                eligibility: RecoveryProbeEligibility::Ineligible,
                budget_version: governance.budget_version,
                reason: "invalid factual runtime-health evidence blocks recovery probe".into(),
            })
        }
    };
    if governance.decision != crate::execution_governance::ExecutionGateDecision::Proceed {
        return Ok(RecoveryProbeEligibilityProjection {
            runtime_id: health.runtime_id,
            runtime_version: health.runtime_version,
            config_id: health.config_id,
            health_state: health.state,
            eligibility: RecoveryProbeEligibility::Ineligible,
            budget_version: governance.budget_version,
            reason: "canonical recovery-probe governance did not permit execution".into(),
        });
    }
    let eligible = matches!(
        health.state,
        RuntimeHealthState::Unhealthy
            | RuntimeHealthState::Quarantined
            | RuntimeHealthState::Recovering
    );
    Ok(RecoveryProbeEligibilityProjection {
        runtime_id: health.runtime_id,
        runtime_version: health.runtime_version,
        config_id: health.config_id,
        health_state: health.state,
        eligibility: if eligible {
            RecoveryProbeEligibility::Eligible
        } else {
            RecoveryProbeEligibility::Ineligible
        },
        budget_version: governance.budget_version,
        reason: if eligible {
            "canonical intent and governance permit a controlled recovery-probe reservation; execution remains separate authority".into()
        } else {
            "runtime state does not require controlled recovery probing".into()
        },
    })
}
