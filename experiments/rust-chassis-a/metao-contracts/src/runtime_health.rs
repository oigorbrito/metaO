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
            return Err(RuntimeHealthError::InvalidPolicy);
        }
        Ok(())
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
        if !matches!(
            self.evidence_basis,
            RuntimeHealthEvidenceBasis::IndependentObservation
                | RuntimeHealthEvidenceBasis::AdapterVerified
        ) {
            return Err(RuntimeHealthError::InvalidEvidenceBasis);
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
        reasons.push("no factual execution observations in window".to_string());
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
            reasons.push("factual observations are currently healthy".to_string());
            RuntimeHealthState::Healthy
        }
    };

    if observation.self_reported_healthy == Some(true) && state != RuntimeHealthState::Healthy {
        reasons.push("runtime self-report healthy=true did not override factual state".to_string());
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
        return Ok(blocked(format!("retry causality gate blocked: {}", causal.reason)));
    }

    if health.retry_pressure_exceeded {
        return Ok(blocked("runtime retry pressure limit is exceeded".to_string()));
    }

    Ok(match health.state {
        RuntimeHealthState::Healthy | RuntimeHealthState::Degraded => BoundedRetryProjection {
            eligibility: BoundedRetryEligibility::Eligible,
            next_attempt: causal.next_attempt,
            health_state: health.state,
            retry_pressure_exceeded: false,
            reason: "causal retry is eligible and factual runtime retry pressure is bounded".to_string(),
        },
        RuntimeHealthState::Recovering => blocked(
            "recovering runtime is not eligible for ordinary retry; controlled recovery authority is required"
                .to_string(),
        ),
        RuntimeHealthState::Unknown => blocked(
            "unknown runtime health cannot be treated as a fresh healthy retry target".to_string(),
        ),
        RuntimeHealthState::Unhealthy | RuntimeHealthState::Quarantined => blocked(
            "unhealthy or quarantined runtime is not eligible for ordinary retry".to_string(),
        ),
    })
}
