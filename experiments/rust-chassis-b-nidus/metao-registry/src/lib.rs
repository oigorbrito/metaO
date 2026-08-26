use metao_contracts::{ExecutionRequest, ExecutionResult, Orchestrator, RuntimeId};
use std::collections::HashMap;
use std::panic::{catch_unwind, AssertUnwindSafe};

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
