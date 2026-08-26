#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct MissionId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ExecutionId(pub String);

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RuntimeId(pub String);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExecutionRequest {
    pub execution_id: ExecutionId,
    pub mission_id: MissionId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ExecutionStatus {
    Succeeded,
    Failed,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExecutionResult {
    pub execution_id: ExecutionId,
    pub runtime_id: RuntimeId,
    pub status: ExecutionStatus,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PolicyEffect {
    Allow,
    Deny,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Evidence {
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub runtime_id: RuntimeId,
    pub policy_version: String,
    pub verified: bool,
    pub created_at_epoch: i64,
    pub expires_at_epoch: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AcceptanceDecision {
    Accept,
    Block,
    NotDone,
    Stale,
}

pub trait Orchestrator: Send + Sync {
    fn id(&self) -> RuntimeId;
    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult;
}
