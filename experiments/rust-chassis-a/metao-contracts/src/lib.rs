#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ContractError {
    EmptyIdentity(&'static str),
}

fn validate_identity(kind: &'static str, value: String) -> Result<String, ContractError> {
    if value.trim().is_empty() {
        return Err(ContractError::EmptyIdentity(kind));
    }
    Ok(value)
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct MissionId(String);

impl MissionId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("mission_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ExecutionId(String);

impl ExecutionId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("execution_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct AttemptId(String);

impl AttemptId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("attempt_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RuntimeId(String);

impl RuntimeId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("runtime_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

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
    fn version(&self) -> String;
    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult;
}
