use std::collections::{BTreeMap, HashMap};
use std::panic::{catch_unwind, AssertUnwindSafe};

use metao_contracts::{
    ExecutionRequest, ExecutionResult, Orchestrator, RuntimeId, VerifierDescriptor, VerifierId,
    VerifierPort, VerifierResult,
};

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RegistryError {
    Duplicate(RuntimeId),
    VersionConflict {
        id: RuntimeId,
        existing: String,
        incoming: String,
    },
    NotFound(RuntimeId),
    Panicked(RuntimeId),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum VerifierRegistryError {
    Duplicate(VerifierId),
    VersionConflict {
        id: VerifierId,
        existing: String,
        incoming: String,
    },
    NotFound(VerifierId),
    Panicked(VerifierId),
}

struct RegisteredRuntime {
    version: String,
    runtime: Box<dyn Orchestrator>,
}

#[derive(Default)]
pub struct Registry {
    runtimes: HashMap<RuntimeId, RegisteredRuntime>,
}

impl Registry {
    pub fn register(&mut self, runtime: Box<dyn Orchestrator>) -> Result<(), RegistryError> {
        let id = runtime.id();
        let version = runtime.version();
        if let Some(existing) = self.runtimes.get(&id) {
            if existing.version == version {
                return Err(RegistryError::Duplicate(id));
            }
            return Err(RegistryError::VersionConflict {
                id,
                existing: existing.version.clone(),
                incoming: version,
            });
        }
        self.runtimes
            .insert(id, RegisteredRuntime { version, runtime });
        Ok(())
    }

    pub fn unregister(&mut self, id: &RuntimeId) -> bool {
        self.runtimes.remove(id).is_some()
    }

    pub fn execute_contained(
        &self,
        id: &RuntimeId,
        request: &ExecutionRequest,
    ) -> Result<ExecutionResult, RegistryError> {
        let Some(registered) = self.runtimes.get(id) else {
            return Err(RegistryError::NotFound(id.clone()));
        };
        match catch_unwind(AssertUnwindSafe(|| registered.runtime.execute(request))) {
            Ok(result) => Ok(result),
            Err(_) => Err(RegistryError::Panicked(id.clone())),
        }
    }
}

struct RegisteredVerifier {
    descriptor: VerifierDescriptor,
    verifier: Box<dyn VerifierPort>,
}

#[derive(Default)]
pub struct VerifierRegistry {
    verifiers: BTreeMap<VerifierId, RegisteredVerifier>,
}

impl VerifierRegistry {
    pub fn register(
        &mut self,
        verifier: Box<dyn VerifierPort>,
    ) -> Result<(), VerifierRegistryError> {
        let descriptor = verifier.descriptor();
        let id = descriptor.verifier_id.clone();
        let version = descriptor.version.clone();
        if let Some(existing) = self.verifiers.get(&id) {
            if existing.descriptor.version == version {
                return Err(VerifierRegistryError::Duplicate(id));
            }
            return Err(VerifierRegistryError::VersionConflict {
                id,
                existing: existing.descriptor.version.clone(),
                incoming: version,
            });
        }
        self.verifiers.insert(
            id,
            RegisteredVerifier {
                descriptor,
                verifier,
            },
        );
        Ok(())
    }

    pub fn unregister(&mut self, id: &VerifierId) -> bool {
        self.verifiers.remove(id).is_some()
    }

    pub fn descriptor(&self, id: &VerifierId) -> Option<VerifierDescriptor> {
        self.verifiers
            .get(id)
            .map(|registered| registered.descriptor.clone())
    }

    pub fn eligible(&self, capability: &str) -> Vec<VerifierDescriptor> {
        self.verifiers
            .values()
            .filter(|registered| {
                registered
                    .descriptor
                    .capabilities
                    .iter()
                    .any(|item| item == capability)
            })
            .map(|registered| registered.descriptor.clone())
            .collect()
    }

    pub fn select_eligible(&self, capability: &str) -> Option<VerifierDescriptor> {
        self.eligible(capability).into_iter().next()
    }

    pub fn execute_contained(
        &self,
        id: &VerifierId,
        request: &metao_contracts::VerificationRequest,
    ) -> Result<VerifierResult, VerifierRegistryError> {
        let Some(registered) = self.verifiers.get(id) else {
            return Err(VerifierRegistryError::NotFound(id.clone()));
        };
        match catch_unwind(AssertUnwindSafe(|| registered.verifier.verify(request))) {
            Ok(result) => Ok(result),
            Err(_) => Err(VerifierRegistryError::Panicked(id.clone())),
        }
    }
}
