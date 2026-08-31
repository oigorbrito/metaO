use serde::{Deserialize, Serialize};

pub mod clarification_policy;
pub mod credential_lease;
pub mod discovery_coordinator;
pub mod execution_governance;
pub mod execution_lease;
pub mod execution_stage_evidence;
pub mod external_effect;
pub mod failure_causality;
pub mod project_completion;
pub mod project_contract;
pub mod reference_intake;
pub mod runtime_certification;
pub mod runtime_health;
pub mod runtime_security;
pub mod tech_stack_intake;
pub mod workload_identity;

pub const CONTRACT_VERSION: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractError {
    EmptyIdentity(&'static str),
    NegativeBudget,
    InitialUsageExceedsLimit,
    EmptyReservationId,
    NegativeReservation,
    ReplayConflict,
    BudgetExhausted,
    UnknownReservation(String),
    InvalidConfidence,
    AcceptanceProofDigestMismatch,
    UnknownVerifier(String),
    DuplicateVerifier(String),
    VerifierVersionConflict {
        id: String,
        existing: String,
        incoming: String,
    },
    DuplicateVerificationAttempt(String),
    DuplicateFactualAttempt(String),
    InvalidVerificationBinding,
    InvalidVerificationResult,
    MissingUsageFact(&'static str),
    VerificationPanic(String),
    RetryHistoryDuplicateRecord(String),
    RetryHistorySequenceGap {
        expected: u64,
        actual: u64,
    },
    RetryHistoryBindingMismatch,
    MissingRetryHistorySource,
    RetryHistoryProjectionMismatch,
    UnsupportedTerminalProofVersion(u32),
    TerminalProofMissingObservation(&'static str),
    TerminalProofDuplicateObservation(String),
    TerminalProofSequenceGap {
        expected: u64,
        actual: u64,
    },
    TerminalProofBindingMismatch,
    TerminalProofDigestMismatch,
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

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct VerifierId(String);

impl VerifierId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("verifier_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct VerificationRequestId(String);

impl VerificationRequestId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("verification_request_id", value.into()).map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct VerificationAttemptId(String);

impl VerificationAttemptId {
    pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
        validate_identity("verification_attempt_id", value.into()).map(Self)
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

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerificationRequest {
    pub request_id: VerificationRequestId,
    pub attempt_id: VerificationAttemptId,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub capability: String,
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

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VerificationAttemptStarted {
    pub request_id: VerificationRequestId,
    pub attempt_id: VerificationAttemptId,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub verifier_id: VerifierId,
    pub verifier_version: String,
    pub started_at_epoch: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum PolicyEffect {
    Allow,
    Deny,
    RequireHuman,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConflictDecision {
    None,
    Duplicate,
    Conflict,
    Unexpected,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequiredEvidenceSet {
    pub obligations: std::collections::BTreeSet<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AggregationResult {
    pub decision: AcceptanceDecision,
    pub reasons: Vec<String>,
    pub conflict: ConflictDecision,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyDecision {
    pub effect: PolicyEffect,
    pub policy_bundle_id: String,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalRequest {
    pub approval_id: String,
    pub mission_id: String,
    pub execution_id: String,
    pub subject_state_id: String,
    pub policy_bundle_id: String,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalRecord {
    pub approval_id: String,
    pub mission_id: String,
    pub execution_id: String,
    pub subject_state_id: String,
    pub policy_bundle_id: String,
    pub approver_id: String,
    pub approved: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ApprovalAuthorityTicket {
    pub approval_id: String,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub subject_state_id: String,
    pub policy_bundle_id: String,
    pub approver_id: String,
    pub capability_id: String,
    pub action: String,
    pub target: String,
    pub scope: String,
    pub authority_epoch: i64,
    pub not_before_epoch: Option<f64>,
    pub expires_at_epoch: Option<f64>,
    pub revoked: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AcceptanceBudget {
    pub money_limit: f64,
    pub token_limit: u64,
    pub wall_time_limit_s: f64,
    pub verifier_attempt_limit: u64,
    pub money_used: f64,
    pub tokens_used: u64,
    pub wall_time_used_s: f64,
    pub verifier_attempts_used: u64,
}

impl AcceptanceBudget {
    fn finite_nonnegative(value: f64) -> bool {
        value.is_finite() && value >= 0.0
    }

    fn validate_f64_field(value: f64) -> Result<(), ContractError> {
        if Self::finite_nonnegative(value) {
            Ok(())
        } else {
            Err(ContractError::NegativeBudget)
        }
    }

    fn validate_state(&self) -> Result<(), ContractError> {
        Self::validate_f64_field(self.money_limit)?;
        Self::validate_f64_field(self.wall_time_limit_s)?;
        Self::validate_f64_field(self.money_used)?;
        Self::validate_f64_field(self.wall_time_used_s)?;
        Ok(())
    }

    pub fn new(
        money_limit: f64,
        token_limit: u64,
        wall_time_limit_s: f64,
        verifier_attempt_limit: u64,
    ) -> Result<Self, ContractError> {
        Self::with_usage(
            (
                money_limit,
                token_limit,
                wall_time_limit_s,
                verifier_attempt_limit,
            ),
            (0.0, 0, 0.0, 0),
        )
    }

    pub fn with_usage(
        limits: (f64, u64, f64, u64),
        usage: (f64, u64, f64, u64),
    ) -> Result<Self, ContractError> {
        let (money_limit, token_limit, wall_time_limit_s, verifier_attempt_limit) = limits;
        let (money_used, tokens_used, wall_time_used_s, verifier_attempts_used) = usage;
        Self::validate_f64_field(money_limit)?;
        Self::validate_f64_field(wall_time_limit_s)?;
        Self::validate_f64_field(money_used)?;
        Self::validate_f64_field(wall_time_used_s)?;
        if money_used > money_limit
            || tokens_used > token_limit
            || wall_time_used_s > wall_time_limit_s
            || verifier_attempts_used > verifier_attempt_limit
        {
            return Err(ContractError::InitialUsageExceedsLimit);
        }
        Ok(Self {
            money_limit,
            token_limit,
            wall_time_limit_s,
            verifier_attempt_limit,
            money_used,
            tokens_used,
            wall_time_used_s,
            verifier_attempts_used,
        })
    }

    pub fn apply_usage(
        mut self,
        money: f64,
        tokens: u64,
        wall_time_s: f64,
        verifier_attempts: u64,
    ) -> Result<Self, ContractError> {
        self.validate_state()?;
        Self::validate_f64_field(money)?;
        Self::validate_f64_field(wall_time_s)?;
        let next_money = self.money_used + money;
        let next_wall_time = self.wall_time_used_s + wall_time_s;
        if !Self::finite_nonnegative(next_money) || !Self::finite_nonnegative(next_wall_time) {
            return Err(ContractError::BudgetExhausted);
        }
        let next_tokens = self
            .tokens_used
            .checked_add(tokens)
            .ok_or(ContractError::BudgetExhausted)?;
        let next_attempts = self
            .verifier_attempts_used
            .checked_add(verifier_attempts)
            .ok_or(ContractError::BudgetExhausted)?;
        if next_money > self.money_limit
            || next_tokens > self.token_limit
            || next_wall_time > self.wall_time_limit_s
            || next_attempts > self.verifier_attempt_limit
        {
            return Err(ContractError::BudgetExhausted);
        }
        self.money_used = next_money;
        self.tokens_used = next_tokens;
        self.wall_time_used_s = next_wall_time;
        self.verifier_attempts_used = next_attempts;
        Ok(self)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BudgetReservation {
    pub reservation_id: String,
    pub money: f64,
    pub tokens: u64,
    pub wall_time_s: f64,
    pub verifier_attempts: u64,
    pub settled: bool,
}

impl BudgetReservation {
    pub fn request_tuple(&self) -> (f64, u64, f64, u64) {
        (
            self.money,
            self.tokens,
            self.wall_time_s,
            self.verifier_attempts,
        )
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VerificationUsage {
    pub attempt_id: VerificationAttemptId,
    pub money: Option<f64>,
    pub tokens: Option<u64>,
    pub wall_time_s: Option<f64>,
    pub verifier_attempts: Option<u64>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RetryHistoryKind {
    AttemptStarted,
    RecoveryObserved,
    UsageRecorded,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RetryHistoryRecord {
    pub record_id: String,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub attempt_id: VerificationAttemptId,
    pub sequence: u64,
    pub kind: RetryHistoryKind,
    pub attempt_started: Option<VerificationAttemptStarted>,
    pub recovery_from_attempt_id: Option<VerificationAttemptId>,
    pub recovery_outcome: Option<ExecutionStatus>,
    pub usage: Option<VerificationUsage>,
}

pub trait RetryHistoryPort: Send + Sync {
    fn append(&self, record: RetryHistoryRecord) -> Result<(), ContractError>;
    fn history(
        &self,
        mission_id: &MissionId,
        execution_id: &ExecutionId,
    ) -> Option<Vec<RetryHistoryRecord>>;
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
    pub subject_id: String,
    pub subject_state_id: String,
    pub verification_context_id: String,
    pub policy_bundle_id: String,
    pub required_obligations: Vec<String>,
    pub trusted_verifiers: Vec<String>,
    pub trusted_provenance_roots: Vec<String>,
    pub authorized_authorities: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct TerminalClaims {
    pub subject_id: String,
    pub subject_state_id: String,
    pub authority_context_id: String,
    pub authority_id: String,
    pub policy_bundle_id: String,
    pub policy_bundle_root: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthoritativeSubjectState {
    pub subject_id: String,
    pub subject_state_id: String,
    pub state_epoch: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthoritativeAuthorityDecision {
    pub authority_context_id: String,
    pub authority_id: String,
    pub authority_epoch: i64,
    pub capability_id: Option<String>,
    pub reason: String,
    pub evidence_root: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthoritativePolicyBundle {
    pub policy_bundle_id: String,
    pub policy_bundle_root: String,
    pub bundle_epoch: i64,
    pub decision: PolicyDecision,
}

pub trait SubjectStatePort: Send + Sync {
    fn current(&self, subject_id: &str) -> Option<AuthoritativeSubjectState>;
}

pub trait AuthorityRegistryPort: Send + Sync {
    fn resolve(
        &self,
        authority_context_id: &str,
        request: &TerminalClaims,
    ) -> Option<AuthoritativeAuthorityDecision>;
}

pub trait PolicyRegistryPort: Send + Sync {
    fn get(&self, policy_bundle_id: &str) -> Option<AuthoritativePolicyBundle>;
}

pub trait ApprovalAuthorityPort: Send + Sync {
    fn current(&self, approval_id: &str) -> Option<ApprovalAuthorityTicket>;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProvenanceVerificationStatus {
    Verified,
    Unverified,
    Invalid,
    Stale,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProvenanceVerificationObservation {
    pub status: ProvenanceVerificationStatus,
    pub evidence_id: String,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub subject_id: String,
    pub subject_state_id: String,
    pub verification_context_id: String,
    pub policy_bundle_id: String,
    pub payload_digest: String,
    pub provenance_root: String,
    pub verifier_id: VerifierId,
    pub issuer_id: String,
    pub observed_at_epoch: f64,
    pub expires_at_epoch: Option<f64>,
    pub reason: String,
}

pub trait ProvenanceVerificationPort: Send + Sync {
    fn verify(&self, evidence: &EvidenceEnvelope) -> Option<ProvenanceVerificationObservation>;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum TerminalObservationKind {
    SubjectState,
    AuthorityResolution,
    PolicyBundle,
    RetryHistory,
    VerificationUsage,
    Approval,
    Provenance,
    Confidence,
    VerifierResult,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum TerminalObservation {
    SubjectState(AuthoritativeSubjectState),
    AuthorityResolution(AuthoritativeAuthorityDecision),
    PolicyBundle(AuthoritativePolicyBundle),
    RetryHistory(Vec<RetryHistoryRecord>),
    VerificationUsage {
        usage: VerificationUsage,
        budget: AcceptanceBudget,
    },
    Approval(ApprovalAuthorityTicket),
    Provenance(ProvenanceVerificationObservation),
    Confidence(BoundConfidence),
    VerifierResult(VerifierResult),
}

impl TerminalObservation {
    pub fn kind(&self) -> TerminalObservationKind {
        match self {
            TerminalObservation::SubjectState(_) => TerminalObservationKind::SubjectState,
            TerminalObservation::AuthorityResolution(_) => {
                TerminalObservationKind::AuthorityResolution
            }
            TerminalObservation::PolicyBundle(_) => TerminalObservationKind::PolicyBundle,
            TerminalObservation::RetryHistory(_) => TerminalObservationKind::RetryHistory,
            TerminalObservation::VerificationUsage { .. } => {
                TerminalObservationKind::VerificationUsage
            }
            TerminalObservation::Approval(_) => TerminalObservationKind::Approval,
            TerminalObservation::Provenance(_) => TerminalObservationKind::Provenance,
            TerminalObservation::Confidence(_) => TerminalObservationKind::Confidence,
            TerminalObservation::VerifierResult(_) => TerminalObservationKind::VerifierResult,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TerminalValidationProfile {
    pub required_kinds: std::collections::BTreeSet<TerminalObservationKind>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TerminalObservationEntry {
    pub observation_id: String,
    pub sequence: u64,
    pub observation: TerminalObservation,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TerminalDecisionProof {
    pub version: u32,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub acceptance_proof: AcceptanceProof,
    pub validation_profile: TerminalValidationProfile,
    pub observations: Vec<TerminalObservationEntry>,
    pub digest: String,
}

impl TerminalDecisionProof {
    pub const CURRENT_VERSION: u32 = 1;
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

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerifierDescriptor {
    pub verifier_id: VerifierId,
    pub version: String,
    pub capabilities: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct VerifierResult {
    pub request_id: VerificationRequestId,
    pub attempt_id: VerificationAttemptId,
    pub verifier_id: VerifierId,
    pub verifier_version: String,
    pub passed: bool,
    pub reason: String,
    pub score: Option<f64>,
    pub confidence: Option<f64>,
    pub usage: VerificationUsage,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BoundConfidence {
    pub verifier_id: VerifierId,
    pub verifier_version: String,
    pub mission_id: MissionId,
    pub execution_id: ExecutionId,
    pub subject_id: String,
    pub subject_state_id: String,
    pub verification_context_id: String,
    pub policy_bundle_id: String,
    pub payload_digest: String,
    pub score: Option<f64>,
    pub confidence: f64,
}

pub trait VerifierPort: Send + Sync {
    fn descriptor(&self) -> VerifierDescriptor;
    fn verify(&self, request: &VerificationRequest) -> VerifierResult;
}
