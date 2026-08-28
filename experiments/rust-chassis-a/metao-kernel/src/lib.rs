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
    use super::*;

    fn mission_id(value: &str) -> metao_contracts::MissionId {
        metao_contracts::MissionId::new(value).unwrap()
    }

    fn execution_id(value: &str) -> metao_contracts::ExecutionId {
        metao_contracts::ExecutionId::new(value).unwrap()
    }

    fn runtime_id(value: &str) -> RuntimeId {
        RuntimeId::new(value).unwrap()
    }

    #[test]
    fn unverified_evidence_with_exact_binding_is_blocked() {
        let request = ExecutionRequest {
            execution_id: execution_id("exec-1"),
            mission_id: mission_id("mission-1"),
        };
        let result = ExecutionResult {
            execution_id: execution_id("exec-1"),
            runtime_id: runtime_id("alpha"),
            status: ExecutionStatus::Succeeded,
        };
        let evidence = Evidence {
            mission_id: mission_id("mission-1"),
            execution_id: execution_id("exec-1"),
            runtime_id: runtime_id("alpha"),
            policy_version: "policy-v1".into(),
            verified: false,
            created_at_epoch: 10,
            expires_at_epoch: 20,
        };

        assert_eq!(
            evaluate_acceptance(&request, &result, Some(&evidence), PolicyEffect::Allow, 15),
            AcceptanceDecision::Block
        );
    }
}
