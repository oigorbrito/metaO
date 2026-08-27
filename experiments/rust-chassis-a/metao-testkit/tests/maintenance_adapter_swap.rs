use metao_contracts::{ExecutionRequest, ExecutionResult, ExecutionStatus, MissionId, ExecutionId, Orchestrator, RuntimeId};
use metao_registry::Registry;

fn runtime_id(value: &str) -> RuntimeId {
    RuntimeId::new(value).unwrap()
}

fn request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: ExecutionId::new("maint-exec-1").unwrap(),
        mission_id: MissionId::new("maint-mission-1").unwrap(),
    }
}

struct LegacyAdapter;
struct ReplacementAdapter;

impl Orchestrator for LegacyAdapter {
    fn id(&self) -> RuntimeId { runtime_id("swap-runtime") }
    fn version(&self) -> String { "1".into() }
    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: request.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}

impl Orchestrator for ReplacementAdapter {
    fn id(&self) -> RuntimeId { runtime_id("swap-runtime") }
    fn version(&self) -> String { "2".into() }
    fn execute(&self, request: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: request.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Failed,
        }
    }
}

#[test]
fn fake_runtime_adapter_can_be_replaced_without_kernel_contract_change() {
    let mut registry = Registry::default();
    registry.register(Box::new(LegacyAdapter)).unwrap();
    let before = registry
        .execute_contained(&runtime_id("swap-runtime"), &request())
        .unwrap();
    assert_eq!(before.status, ExecutionStatus::Succeeded);

    assert!(registry.unregister(&runtime_id("swap-runtime")));
    registry.register(Box::new(ReplacementAdapter)).unwrap();
    let after = registry
        .execute_contained(&runtime_id("swap-runtime"), &request())
        .unwrap();
    assert_eq!(after.status, ExecutionStatus::Failed);
}
