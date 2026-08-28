use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus,
    MissionId, Orchestrator, PolicyEffect, RuntimeId,
};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_registry::{Registry, RegistryError};

const NOW: i64 = 15;
const PYTHON_BASELINE_COMMIT: &str = "b69a4e502b07ddfa1f5e05399710e335d5edfbc0";

struct GoldenCase {
    name: String,
    executor_done: bool,
    evidence: String,
    expected: String,
}

fn json_string_field(line: &str, key: &str) -> String {
    let marker = format!("\"{key}\": \"");
    let start = line
        .find(&marker)
        .unwrap_or_else(|| panic!("missing key: {key}"))
        + marker.len();
    let rest = &line[start..];
    let end = rest
        .find('"')
        .unwrap_or_else(|| panic!("unterminated key: {key}"));
    rest[..end].to_string()
}

fn json_bool_field(line: &str, key: &str) -> bool {
    let marker = format!("\"{key}\": ");
    let start = line
        .find(&marker)
        .unwrap_or_else(|| panic!("missing key: {key}"))
        + marker.len();
    line[start..].starts_with("true")
}

fn golden_fixture_cases(raw: &str) -> Vec<GoldenCase> {
    assert!(
        raw.contains(&format!(
            "\"baseline_commit\": \"{PYTHON_BASELINE_COMMIT}\""
        )),
        "golden fixture baseline commit drifted"
    );
    raw.lines()
        .filter(|line| line.contains("\"name\""))
        .map(|line| GoldenCase {
            name: json_string_field(line, "name"),
            executor_done: json_bool_field(line, "executor_done"),
            evidence: json_string_field(line, "evidence"),
            expected: json_string_field(line, "expected"),
        })
        .collect()
}

fn mission_id(value: &str) -> MissionId {
    MissionId::new(value).unwrap()
}
fn execution_id(value: &str) -> ExecutionId {
    ExecutionId::new(value).unwrap()
}
fn runtime_id(value: &str) -> RuntimeId {
    RuntimeId::new(value).unwrap()
}
fn request() -> ExecutionRequest {
    ExecutionRequest {
        execution_id: execution_id("exec-1"),
        mission_id: mission_id("mission-1"),
    }
}
fn success(runtime: &str) -> ExecutionResult {
    ExecutionResult {
        execution_id: execution_id("exec-1"),
        runtime_id: runtime_id(runtime),
        status: ExecutionStatus::Succeeded,
    }
}
fn evidence(runtime: &str) -> Evidence {
    Evidence {
        mission_id: mission_id("mission-1"),
        execution_id: execution_id("exec-1"),
        runtime_id: runtime_id(runtime),
        policy_version: "policy-v1".into(),
        verified: true,
        created_at_epoch: 10,
        expires_at_epoch: 20,
    }
}

fn expected_decision(value: &str) -> AcceptanceDecision {
    match value {
        "ACCEPT" => AcceptanceDecision::Accept,
        "BLOCK" => AcceptanceDecision::Block,
        "NOT_DONE" => AcceptanceDecision::NotDone,
        "STALE" => AcceptanceDecision::Stale,
        other => panic!("unknown golden expected outcome: {other}"),
    }
}

struct Alpha;
struct AlphaV2;
struct Beta;
struct PanicRuntime;
impl Orchestrator for Alpha {
    fn id(&self) -> RuntimeId {
        runtime_id("alpha")
    }
    fn version(&self) -> String {
        "1".into()
    }
    fn execute(&self, r: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: r.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}
impl Orchestrator for AlphaV2 {
    fn id(&self) -> RuntimeId {
        runtime_id("alpha")
    }
    fn version(&self) -> String {
        "2".into()
    }
    fn execute(&self, r: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: r.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}
impl Orchestrator for Beta {
    fn id(&self) -> RuntimeId {
        runtime_id("beta")
    }
    fn version(&self) -> String {
        "1".into()
    }
    fn execute(&self, r: &ExecutionRequest) -> ExecutionResult {
        ExecutionResult {
            execution_id: r.execution_id.clone(),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
    }
}
impl Orchestrator for PanicRuntime {
    fn id(&self) -> RuntimeId {
        runtime_id("panic")
    }
    fn version(&self) -> String {
        "1".into()
    }
    fn execute(&self, _: &ExecutionRequest) -> ExecutionResult {
        panic!("simulated adapter failure")
    }
}

#[test]
fn whole_orchestrator_replacement_changes_no_kernel_contract() {
    let mut registry = Registry::default();
    registry.register(Box::new(Alpha)).unwrap();
    assert_eq!(
        registry
            .execute_contained(&runtime_id("alpha"), &request())
            .unwrap()
            .runtime_id,
        runtime_id("alpha")
    );
    assert!(registry.unregister(&runtime_id("alpha")));
    registry.register(Box::new(Beta)).unwrap();
    assert_eq!(
        registry
            .execute_contained(&runtime_id("beta"), &request())
            .unwrap()
            .runtime_id,
        runtime_id("beta")
    );
}

#[test]
fn duplicate_and_version_conflict_fail_deterministically() {
    let mut duplicate = Registry::default();
    duplicate.register(Box::new(Alpha)).unwrap();
    assert_eq!(
        duplicate.register(Box::new(Alpha)),
        Err(RegistryError::Duplicate(runtime_id("alpha")))
    );
    let mut conflict = Registry::default();
    conflict.register(Box::new(Alpha)).unwrap();
    assert_eq!(
        conflict.register(Box::new(AlphaV2)),
        Err(RegistryError::VersionConflict {
            id: runtime_id("alpha"),
            existing: "1".into(),
            incoming: "2".into()
        })
    );
}

#[test]
fn unknown_runtime_fails_closed() {
    let registry = Registry::default();
    assert_eq!(
        registry.execute_contained(&runtime_id("missing"), &request()),
        Err(RegistryError::NotFound(runtime_id("missing")))
    );
}

#[test]
fn invalid_identity_construction_is_rejected_by_public_api() {
    assert!(MissionId::new("").is_err());
    assert!(MissionId::new("   ").is_err());
    assert!(ExecutionId::new("").is_err());
    assert!(RuntimeId::new("").is_err());
}

#[test]
fn acceptance_hard_gates_match_python_baseline() {
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            None,
            PolicyEffect::Allow,
            NOW
        ),
        AcceptanceDecision::NotDone
    );
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Deny,
            NOW
        ),
        AcceptanceDecision::Block
    );
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
            NOW
        ),
        AcceptanceDecision::Accept
    );
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
            21
        ),
        AcceptanceDecision::Stale
    );
    assert_eq!(
        evaluate_acceptance(
            &request(),
            &success("alpha"),
            Some(&evidence("beta")),
            PolicyEffect::Allow,
            NOW
        ),
        AcceptanceDecision::Block
    );
}

#[test]
fn replays_python_golden_fixture_outcomes() {
    for case in golden_fixture_cases(include_str!("../../fixtures/chassis_v1.json")) {
        let mut item = evidence("alpha");
        let evidence = match case.evidence.as_str() {
            "none" => None,
            "bound" => Some(item),
            "evil_verifier" => {
                item.verified = false;
                Some(item)
            }
            "stale" => Some(item),
            other => panic!("unknown golden evidence fixture: {other}"),
        };
        let now_epoch = if case.evidence == "stale" { 21 } else { NOW };
        let result = success("alpha");
        let decision = evaluate_acceptance(
            &request(),
            &result,
            evidence.as_ref(),
            PolicyEffect::Allow,
            now_epoch,
        );
        assert_eq!(
            decision,
            expected_decision(&case.expected),
            "golden case {} executor_done={} drifted",
            case.name,
            case.executor_done
        );
    }
}

#[test]
fn adversarial_evidence_binding_matrix_only_accepts_exact_verified_binding() {
    for verified in [false, true] {
        for mission_matches in [false, true] {
            for execution_matches in [false, true] {
                for runtime_matches in [false, true] {
                    let mut item = evidence(if runtime_matches { "alpha" } else { "beta" });
                    item.verified = verified;
                    if !mission_matches {
                        item.mission_id = mission_id("wrong-mission");
                    }
                    if !execution_matches {
                        item.execution_id = execution_id("wrong-exec");
                    }
                    let decision = evaluate_acceptance(
                        &request(),
                        &success("alpha"),
                        Some(&item),
                        PolicyEffect::Allow,
                        NOW,
                    );
                    assert_eq!(
                        decision == AcceptanceDecision::Accept,
                        verified && mission_matches && execution_matches && runtime_matches
                    );
                }
            }
        }
    }
}

#[test]
fn failed_execution_never_accepts_and_panic_is_contained() {
    let failed = ExecutionResult {
        execution_id: execution_id("exec-1"),
        runtime_id: runtime_id("alpha"),
        status: ExecutionStatus::Failed,
    };
    assert_ne!(
        evaluate_acceptance(
            &request(),
            &failed,
            Some(&evidence("alpha")),
            PolicyEffect::Allow,
            NOW
        ),
        AcceptanceDecision::Accept
    );
    let mut registry = Registry::default();
    registry.register(Box::new(PanicRuntime)).unwrap();
    assert_eq!(
        registry.execute_contained(&runtime_id("panic"), &request()),
        Err(RegistryError::Panicked(runtime_id("panic")))
    );
}

#[test]
fn reconciliation_is_idempotent_and_deterministic() {
    let desired = vec![runtime_id("alpha"), runtime_id("beta")];
    let mut observed = vec![runtime_id("alpha")];
    let missing = reconcile_missing(&desired, &observed);
    assert_eq!(missing, vec![runtime_id("beta")]);
    observed.extend(missing);
    assert!(reconcile_missing(&desired, &observed).is_empty());
    assert!(reconcile_missing(&desired, &observed).is_empty());
    let duplicated = vec![runtime_id("beta"), runtime_id("alpha"), runtime_id("beta")];
    assert_eq!(
        reconcile_missing(&duplicated, &[]),
        vec![runtime_id("alpha"), runtime_id("beta")]
    );
}

#[test]
fn exhaustive_small_reconcile_state_space_satisfies_laws() {
    let universe = [runtime_id("alpha"), runtime_id("beta"), runtime_id("gamma")];
    for desired_mask in 0u8..8 {
        for observed_mask in 0u8..8 {
            let desired: Vec<_> = universe
                .iter()
                .enumerate()
                .filter(|(i, _)| desired_mask & (1 << i) != 0)
                .map(|(_, r)| r.clone())
                .collect();
            let observed: Vec<_> = universe
                .iter()
                .enumerate()
                .filter(|(i, _)| observed_mask & (1 << i) != 0)
                .map(|(_, r)| r.clone())
                .collect();
            let first = reconcile_missing(&desired, &observed);
            let second = reconcile_missing(&desired, &observed);
            assert_eq!(first, second, "reconcile must be deterministic");
            assert!(
                first.windows(2).all(|w| w[0] < w[1]),
                "missing must be sorted and deduplicated"
            );
            assert!(first
                .iter()
                .all(|r| desired.contains(r) && !observed.contains(r)));
            let mut converged = observed.clone();
            converged.extend(first);
            assert!(
                reconcile_missing(&desired, &converged).is_empty(),
                "one application must converge for this model"
            );
        }
    }
}

#[test]
fn kernel_is_platform_framework_and_unsafe_free() {
    let manifest = include_str!("../../metao-kernel/Cargo.toml").to_lowercase();
    for forbidden in [
        "axum",
        "tokio",
        "kube",
        "openai",
        "langgraph",
        "crewai",
        "sqlx",
        "windows",
        "libc",
    ] {
        assert!(
            !manifest.contains(forbidden),
            "forbidden kernel dependency: {forbidden}"
        );
    }
    let source = include_str!("../../metao-kernel/src/lib.rs").to_lowercase();
    for forbidden in ["unsafe", "cfg(target_os", "cfg(windows", "cfg(unix"] {
        assert!(!source.contains(forbidden), "kernel leak: {forbidden}");
    }
}
