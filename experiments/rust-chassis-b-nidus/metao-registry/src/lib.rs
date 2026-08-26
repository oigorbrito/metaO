use std::collections::HashMap;
use std::panic::{catch_unwind, AssertUnwindSafe};

use metao_contracts::{ExecutionRequest, ExecutionResult, Orchestrator, RuntimeId};

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RegistryError {
    Duplicate(RuntimeId),
    NotFound(RuntimeId),
    Panicked(RuntimeId),
}

#[derive(Default)]
pub struct Registry {
    runtimes: HashMap<RuntimeId, Box<dyn Orchestrator>>,
}

impl Registry {
    pub fn register(&mut self, runtime: Box<dyn Orchestrator>) -> Result<(), RegistryError> {
        let id = runtime.id();
        if self.runtimes.contains_key(&id) {
            return Err(RegistryError::Duplicate(id));
        }
        self.runtimes.insert(id, runtime);
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
        let Some(runtime) = self.runtimes.get(id) else {
            return Err(RegistryError::NotFound(id.clone()));
        };
        match catch_unwind(AssertUnwindSafe(|| runtime.execute(request))) {
            Ok(result) => Ok(result),
            Err(_) => Err(RegistryError::Panicked(id.clone())),
        }
    }
}
