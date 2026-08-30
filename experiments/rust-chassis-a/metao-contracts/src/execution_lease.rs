use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionLeaseError {
    BlankIdentity(&'static str),
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

    pub fn validate_successor(&self, successor: &ExecutionLease) -> Result<(), ExecutionLeaseError> {
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
