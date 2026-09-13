use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionLeaseError {
    BlankIdentity(&'static str),
    BlankEvidenceRef,
    InvalidEvidenceBasis,
    ZeroGeneration,
    ZeroFencingToken,
    InvalidTimeWindow,
    LeaseBindingMismatch,
    GenerationRegression,
    FenceRegression,
    TimeRegression,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum LeaseState {
    Active,
    Released,
    Expired,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum LeaseAssurance {
    AuthoritativeStore,
    SingleInstanceDevelopment,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum LeaseEvidenceBasis {
    AuthoritativeStoreRead,
    DevelopmentLocal,
    CallerDeclared,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionLease {
    pub mission_id: String,
    pub logical_execution_key: String,
    pub execution_id: String,
    pub holder_identity: String,
    pub generation: u64,
    pub fencing_token: u64,
    pub acquired_at_epoch: i64,
    pub renewed_at_epoch: i64,
    pub expires_at_epoch: i64,
    pub state: LeaseState,
    pub assurance: LeaseAssurance,
    pub evidence_basis: LeaseEvidenceBasis,
    pub evidence_ref: Option<String>,
}

impl ExecutionLease {
    pub fn validate(&self) -> Result<(), ExecutionLeaseError> {
        for (name, value) in [
            ("mission_id", self.mission_id.as_str()),
            ("logical_execution_key", self.logical_execution_key.as_str()),
            ("execution_id", self.execution_id.as_str()),
            ("holder_identity", self.holder_identity.as_str()),
        ] {
            if value.trim().is_empty() {
                return Err(ExecutionLeaseError::BlankIdentity(name));
            }
        }
        match (self.assurance, self.evidence_basis) {
            (LeaseAssurance::AuthoritativeStore, LeaseEvidenceBasis::AuthoritativeStoreRead) => {
                if self
                    .evidence_ref
                    .as_deref()
                    .is_none_or(|value| value.trim().is_empty())
                {
                    return Err(ExecutionLeaseError::BlankEvidenceRef);
                }
            }
            (LeaseAssurance::SingleInstanceDevelopment, LeaseEvidenceBasis::DevelopmentLocal) => {}
            _ => return Err(ExecutionLeaseError::InvalidEvidenceBasis),
        }
        if self.generation == 0 {
            return Err(ExecutionLeaseError::ZeroGeneration);
        }
        if self.fencing_token == 0 {
            return Err(ExecutionLeaseError::ZeroFencingToken);
        }
        if self.renewed_at_epoch < self.acquired_at_epoch
            || self.expires_at_epoch <= self.renewed_at_epoch
        {
            return Err(ExecutionLeaseError::InvalidTimeWindow);
        }
        Ok(())
    }

    pub fn is_active_at(&self, now_epoch: i64) -> bool {
        self.validate().is_ok()
            && self.state == LeaseState::Active
            && now_epoch >= self.renewed_at_epoch
            && now_epoch < self.expires_at_epoch
    }

    pub fn authorizes(
        &self,
        presented_holder: &str,
        presented_generation: u64,
        presented_fence: u64,
        now_epoch: i64,
    ) -> bool {
        self.is_active_at(now_epoch)
            && self.holder_identity == presented_holder
            && self.generation == presented_generation
            && self.fencing_token == presented_fence
    }

    pub fn validate_successor(
        &self,
        successor: &ExecutionLease,
    ) -> Result<(), ExecutionLeaseError> {
        self.validate()?;
        successor.validate()?;
        if successor.mission_id != self.mission_id
            || successor.logical_execution_key != self.logical_execution_key
        {
            return Err(ExecutionLeaseError::LeaseBindingMismatch);
        }
        if successor.generation < self.generation {
            return Err(ExecutionLeaseError::GenerationRegression);
        }
        if successor.fencing_token < self.fencing_token {
            return Err(ExecutionLeaseError::FenceRegression);
        }
        let holder_changed = successor.holder_identity != self.holder_identity;
        let execution_changed = successor.execution_id != self.execution_id;
        let reactivated = self.state != LeaseState::Active && successor.state == LeaseState::Active;
        let requires_new_generation = holder_changed || execution_changed || reactivated;
        if requires_new_generation && successor.generation <= self.generation {
            return Err(ExecutionLeaseError::GenerationRegression);
        }
        if requires_new_generation && successor.fencing_token <= self.fencing_token {
            return Err(ExecutionLeaseError::FenceRegression);
        }
        if !requires_new_generation
            && (successor.renewed_at_epoch < self.renewed_at_epoch
                || successor.expires_at_epoch < self.expires_at_epoch)
        {
            return Err(ExecutionLeaseError::TimeRegression);
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionRuntimeBindingBasis {
    CanonicalDispatch,
    AdapterVerified,
    CallerDeclared,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRuntimeBindingProducer {
    pub producer_id: String,
    pub mission_id: String,
    pub logical_execution_key: String,
    pub execution_id: String,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub lease_generation: u64,
    pub fencing_token: u64,
    pub basis: ExecutionRuntimeBindingBasis,
    pub evidence_ref: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRuntimeBindingClaim {
    pub mission_id: String,
    pub logical_execution_key: String,
    pub execution_id: String,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub lease_generation: u64,
    pub fencing_token: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundExecutionRuntimeIdentity {
    pub producer_id: String,
    pub mission_id: String,
    pub logical_execution_key: String,
    pub execution_id: String,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub lease_generation: u64,
    pub fencing_token: u64,
    pub evidence_ref: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionRuntimeBindingError {
    InvalidProducer,
    LeaseBindingMismatch,
    ClaimBindingMismatch,
    StaleGenerationOrFence,
}

pub fn bind_execution_runtime_identity(
    claim: &ExecutionRuntimeBindingClaim,
    producer: &ExecutionRuntimeBindingProducer,
    current_lease: &ExecutionLease,
) -> Result<BoundExecutionRuntimeIdentity, ExecutionRuntimeBindingError> {
    for value in [
        producer.producer_id.as_str(),
        producer.mission_id.as_str(),
        producer.logical_execution_key.as_str(),
        producer.execution_id.as_str(),
        producer.runtime_id.as_str(),
        producer.runtime_version.as_str(),
        producer.config_id.as_str(),
        producer.evidence_ref.as_str(),
    ] {
        if value.trim().is_empty() {
            return Err(ExecutionRuntimeBindingError::InvalidProducer);
        }
    }
    if producer.basis != ExecutionRuntimeBindingBasis::CanonicalDispatch
        || producer.lease_generation == 0
        || producer.fencing_token == 0
    {
        return Err(ExecutionRuntimeBindingError::InvalidProducer);
    }
    current_lease
        .validate()
        .map_err(|_| ExecutionRuntimeBindingError::LeaseBindingMismatch)?;
    if producer.mission_id != current_lease.mission_id
        || producer.logical_execution_key != current_lease.logical_execution_key
        || producer.execution_id != current_lease.execution_id
    {
        return Err(ExecutionRuntimeBindingError::LeaseBindingMismatch);
    }
    if producer.lease_generation != current_lease.generation
        || producer.fencing_token != current_lease.fencing_token
    {
        return Err(ExecutionRuntimeBindingError::StaleGenerationOrFence);
    }
    if claim.mission_id != producer.mission_id
        || claim.logical_execution_key != producer.logical_execution_key
        || claim.execution_id != producer.execution_id
        || claim.runtime_id != producer.runtime_id
        || claim.runtime_version != producer.runtime_version
        || claim.config_id != producer.config_id
        || claim.lease_generation != producer.lease_generation
        || claim.fencing_token != producer.fencing_token
    {
        return Err(ExecutionRuntimeBindingError::ClaimBindingMismatch);
    }

    Ok(BoundExecutionRuntimeIdentity {
        producer_id: producer.producer_id.clone(),
        mission_id: producer.mission_id.clone(),
        logical_execution_key: producer.logical_execution_key.clone(),
        execution_id: producer.execution_id.clone(),
        runtime_id: producer.runtime_id.clone(),
        runtime_version: producer.runtime_version.clone(),
        config_id: producer.config_id.clone(),
        lease_generation: producer.lease_generation,
        fencing_token: producer.fencing_token,
        evidence_ref: producer.evidence_ref.clone(),
    })
}
