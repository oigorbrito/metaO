#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct MissionId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct RuntimeId(pub String);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ExecutionStatus {
    Succeeded,
    Failed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PolicyEffect {
    Allow,
    Deny,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AcceptanceDecision {
    Accept,
    Block,
    NotDone,
}

pub fn acceptance(
    status: ExecutionStatus,
    evidence_bound: bool,
    policy: PolicyEffect,
) -> AcceptanceDecision {
    if matches!(policy, PolicyEffect::Deny) {
        return AcceptanceDecision::Block;
    }
    if !matches!(status, ExecutionStatus::Succeeded) || !evidence_bound {
        return AcceptanceDecision::NotDone;
    }
    AcceptanceDecision::Accept
}
