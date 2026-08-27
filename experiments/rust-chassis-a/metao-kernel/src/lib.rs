use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionRequest, ExecutionResult, ExecutionStatus, PolicyEffect,
    RuntimeId,
};

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
            evaluate_acceptance(
                &request(),
                &result(),
                Some(&item),
                PolicyEffect::Allow,
                15,
            ),
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
