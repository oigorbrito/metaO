use serde::{Deserialize, Serialize};

pub const CONTRACT_VERSION: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractError {
    EmptyIdentity(&'static str),
}

fn validate_identity(kind: &'static str, value: String) -> Result<String, ContractError> {
    if value.trim().is_empty() {
        return Err(ContractError::EmptyIdentity(kind));
    }
    Ok(value)
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct MissionId(String);

impl MissionId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("mission_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ExecutionId(String);

impl ExecutionId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("execution_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct RuntimeId(String);

impl RuntimeId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("runtime_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRequest {
    pub execution_id: ExecutionId,
    pub mission_id: MissionId,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionStatus {
    Succeeded,
    Failed,
    Cancelled,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub execution_id: ExecutionId,
    pub runtime_id: RuntimeId,
    pub status: ExecutionStatus,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum PolicyEffect {
    Allow,
    Deny,
    RequireHuman,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Evidence {
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub runtime_id: RuntimeId,
    pub policy_version: String,
    pub verified: bool,
    pub created_at_epoch: i64,
    pub expires_at_epoch: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum AcceptanceDecision {
    Accept,
    Block,
    NotDone,
    Stale,
    RequireHuman,
}

pub trait Orchestrator: Send + Sync {
    fn id(&self) -> RuntimeId;
    fn version(&self) -> String;
    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult;
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct EvidenceEnvelope {
    pub evidence_id: String,
    pub obligation_id: String,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub orchestrator_id: RuntimeId,
    pub adapter_version: String,
    pub attempt_id: String,
    pub subject_id: String,
    pub subject_state_id: String,
    pub verification_context_id: String,
    pub policy_bundle_id: String,
    pub verifier_id: String,
    pub payload_digest: String,
    pub provenance_root: String,
    pub authority_id: String,
    pub passed: bool,
    pub created_at_epoch: f64,
    pub expires_at_epoch: Option<f64>,
    pub approval_id: Option<String>,
    pub confidence: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AcceptanceContext {
    pub mission_id: String,
    pub execution_id: String,
    pub runtime_id: String,
    pub subject_id: String,
    pub subject_state_id: String,
    pub verification_context_id: String,
    pub policy_bundle_id: String,
    pub required_obligations: Vec<String>,
    pub trusted_verifiers: Vec<String>,
    pub trusted_provenance_roots: Vec<String>,
    pub authorized_authorities: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConflictDecision {
    None,
    Duplicate,
    Conflict,
    Unexpected,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AcceptanceProof {
    pub decision: AcceptanceDecision,
    pub reasons: Vec<String>,
    pub evidence_ids: Vec<String>,
    pub digest: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AcceptanceResult {
    pub decision: AcceptanceDecision,
    pub reasons: Vec<String>,
    pub proof: Option<AcceptanceProof>,
}
