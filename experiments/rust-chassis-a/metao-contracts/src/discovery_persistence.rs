use crate::discovery_coordinator::{
    DiscoveryCoordinator, DiscoveryCoordinatorError, DiscoveryCoordinatorInput, DiscoveryEvaluation,
};
use crate::project_contract::ProjectContractBinding;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoverySnapshot {
    pub binding: ProjectContractBinding,
    pub input: DiscoveryCoordinatorInput,
    pub evaluation: DiscoveryEvaluation,
}

impl DiscoverySnapshot {
    pub fn capture(input: DiscoveryCoordinatorInput) -> Result<Self, DiscoveryPersistenceError> {
        let evaluation = DiscoveryCoordinator::evaluate(&input)?;
        let binding = input.contract.binding();
        if !evaluation.applies_to(&binding) {
            return Err(DiscoveryPersistenceError::BindingMismatch);
        }
        Ok(Self {
            binding,
            input,
            evaluation,
        })
    }

    pub fn resume(&self) -> Result<DiscoveryEvaluation, DiscoveryPersistenceError> {
        if self.input.contract.binding() != self.binding {
            return Err(DiscoveryPersistenceError::BindingMismatch);
        }
        let reevaluated = DiscoveryCoordinator::evaluate(&self.input)?;
        if reevaluated.binding != self.binding {
            return Err(DiscoveryPersistenceError::BindingMismatch);
        }
        Ok(reevaluated)
    }

    pub fn resume_for(
        &self,
        expected_binding: &ProjectContractBinding,
    ) -> Result<DiscoveryEvaluation, DiscoveryPersistenceError> {
        if &self.binding != expected_binding {
            return Err(DiscoveryPersistenceError::BindingMismatch);
        }
        self.resume()
    }
}

pub trait DiscoveryStateStore {
    fn save(&self, snapshot: &DiscoverySnapshot) -> Result<(), DiscoveryPersistenceError>;
    fn load(
        &self,
        binding: &ProjectContractBinding,
    ) -> Result<Option<DiscoverySnapshot>, DiscoveryPersistenceError>;
    fn delete(&self, binding: &ProjectContractBinding) -> Result<(), DiscoveryPersistenceError>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DiscoveryPersistenceError {
    Coordinator(DiscoveryCoordinatorError),
    Io(String),
    Decode(String),
    BindingMismatch,
}

impl From<DiscoveryCoordinatorError> for DiscoveryPersistenceError {
    fn from(value: DiscoveryCoordinatorError) -> Self {
        Self::Coordinator(value)
    }
}

#[derive(Clone, Debug)]
pub struct FileDiscoveryStateStore {
    root: PathBuf,
}

impl FileDiscoveryStateStore {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn snapshot_path(&self, binding: &ProjectContractBinding) -> PathBuf {
        let digest = sanitize_path_component(&binding.contract_digest);
        self.root.join(format!(
            "{}__{}__v{}__{}.json",
            sanitize_path_component(&binding.project_id.0),
            sanitize_path_component(&binding.contract_id.0),
            binding.version,
            digest
        ))
    }
}

impl DiscoveryStateStore for FileDiscoveryStateStore {
    fn save(&self, snapshot: &DiscoverySnapshot) -> Result<(), DiscoveryPersistenceError> {
        snapshot.resume()?;
        fs::create_dir_all(&self.root)
            .map_err(|err| DiscoveryPersistenceError::Io(err.to_string()))?;
        let payload = serde_json::to_vec_pretty(snapshot)
            .map_err(|err| DiscoveryPersistenceError::Decode(err.to_string()))?;
        fs::write(self.snapshot_path(&snapshot.binding), payload)
            .map_err(|err| DiscoveryPersistenceError::Io(err.to_string()))
    }

    fn load(
        &self,
        binding: &ProjectContractBinding,
    ) -> Result<Option<DiscoverySnapshot>, DiscoveryPersistenceError> {
        let path = self.snapshot_path(binding);
        if !path.exists() {
            return Ok(None);
        }
        let bytes = fs::read(path).map_err(|err| DiscoveryPersistenceError::Io(err.to_string()))?;
        let snapshot: DiscoverySnapshot = serde_json::from_slice(&bytes)
            .map_err(|err| DiscoveryPersistenceError::Decode(err.to_string()))?;
        if snapshot.binding != *binding {
            return Err(DiscoveryPersistenceError::BindingMismatch);
        }
        snapshot.resume_for(binding)?;
        Ok(Some(snapshot))
    }

    fn delete(&self, binding: &ProjectContractBinding) -> Result<(), DiscoveryPersistenceError> {
        let path = self.snapshot_path(binding);
        match fs::remove_file(path) {
            Ok(()) => Ok(()),
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(err) => Err(DiscoveryPersistenceError::Io(err.to_string())),
        }
    }
}

fn sanitize_path_component(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.') {
                ch
            } else {
                '_'
            }
        })
        .collect()
}
