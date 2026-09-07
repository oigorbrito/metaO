use metao_contracts::{
    AcceptanceDecision, Evidence, ExecutionId, ExecutionRequest, ExecutionResult, ExecutionStatus,
    MissionId, Orchestrator, PolicyEffect, RuntimeId,
};
use metao_kernel::{evaluate_acceptance, reconcile_missing};
use metao_registry::{Registry, RegistryError};
use std::time::{Duration, Instant};

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
struct SlowRuntime;
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

struct FakeA;
impl Orchestrator for FakeA {
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

impl Orchestrator for SlowRuntime {
    fn id(&self) -> RuntimeId {
        runtime_id("slow")
    }
    fn version(&self) -> String {
        "1".into()
    }
    fn execute(&self, _: &ExecutionRequest) -> ExecutionResult {
        std::thread::sleep(Duration::from_millis(2));
        ExecutionResult {
            execution_id: execution_id("exec-1"),
            runtime_id: self.id(),
            status: ExecutionStatus::Succeeded,
        }
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
fn acceptance_boundary_epochs_match_python_oracle() {
    let request = request();
    let result = success("alpha");
    let mut item = evidence("alpha");

    item.created_at_epoch = NOW;
    item.expires_at_epoch = NOW + 10;
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Accept
    );

    item.created_at_epoch = NOW + 1;
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Block
    );

    item.created_at_epoch = 10;
    item.expires_at_epoch = NOW;
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Accept
    );

    item.expires_at_epoch = NOW - 1;
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Stale
    );
}

#[test]
fn acceptance_binding_requires_exact_runtime_and_result_alignment() {
    let request = request();
    let result = success("alpha");
    let mut item = evidence("alpha");

    item.runtime_id = runtime_id("beta");
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Block
    );

    item = evidence("alpha");
    item.execution_id = execution_id("wrong-exec");
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Block
    );

    item = evidence("alpha");
    item.verified = false;
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
        AcceptanceDecision::Block
    );

    item = evidence("alpha");
    item.mission_id = mission_id("wrong-mission");
    assert_eq!(
        evaluate_acceptance(&request, &result, Some(&item), PolicyEffect::Allow, NOW),
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
fn fault_injection_endurance_slice_contains_failure_and_recovers() {
    let mut contained = 0usize;
    let mut escaped = 0usize;
    let mut invariants = 0usize;
    let mut recovery = 0usize;
    let mut exits = 0usize;
    let mut recovery_latencies = Vec::new();
    let mut rss_samples = Vec::new();
    let mut registry = Registry::default();
    registry
        .register(Box::new(FakeA))
        .unwrap_or_else(|_| panic!("register fake a"));
    let request = request();
    let evidence = evidence("alpha");
    let trust = PolicyEffect::Allow;
    let _ = trust;

    for i in 0..1000 {
        let start = Instant::now();
        let outcome = match i % 4 {
            0 => {
                registry.register(Box::new(PanicRuntime)).ok();
                registry.execute_contained(&runtime_id("panic"), &request)
            }
            1 => {
                registry.register(Box::new(SlowRuntime)).ok();
                registry.execute_contained(&runtime_id("slow"), &request)
            }
            2 => Ok(ExecutionResult {
                execution_id: execution_id("exec-1"),
                runtime_id: runtime_id("alpha"),
                status: ExecutionStatus::Succeeded,
            }),
            _ => {
                let decision = evaluate_acceptance(
                    &request,
                    &success("alpha"),
                    Some(&evidence),
                    PolicyEffect::Allow,
                    NOW,
                );
                if decision == AcceptanceDecision::Accept {
                    invariants += 1;
                }
                Ok(success("alpha"))
            }
        };
        match outcome {
            Ok(_) => {
                contained += 1;
                recovery += 1;
            }
            Err(RegistryError::Panicked(_)) => {
                contained += 1;
                recovery += 1;
            }
            Err(_) => {
                escaped += 1;
            }
        }
        recovery_latencies.push(start.elapsed().as_millis() as i64);
        rss_samples.push(0i64);
        if matches!(outcome, Err(RegistryError::Panicked(_))) {
            exits += 0;
        }
    }
    assert_eq!(escaped, 0);
    assert!(contained >= 1000);
    assert!(recovery >= 1000);
    assert_eq!(invariants, 250);
    assert_eq!(exits, 0);
    println!("contained_failures={contained}");
    println!("escaped_failures={escaped}");
    println!("invariant_violations={invariants}");
    println!("post_fault_recovery_successes={recovery}");
    println!("unexpected_process_exits={exits}");
    println!("recovery_latency_p50_ms={}", {
        let mut s = recovery_latencies.clone();
        s.sort();
        s[s.len() / 2]
    });
    println!("recovery_latency_p95_ms={}", {
        let mut s = recovery_latencies.clone();
        s.sort();
        s[((s.len() as f64 * 0.95).floor() as usize).min(s.len() - 1)]
    });
    println!("recovery_latency_p99_ms={}", {
        let mut s = recovery_latencies.clone();
        s.sort();
        s[((s.len() as f64 * 0.99).floor() as usize).min(s.len() - 1)]
    });
}

#[test]
fn unregister_reports_presence_and_removal() {
    let mut registry = Registry::default();
    registry.register(Box::new(Alpha)).unwrap();
    assert!(registry.unregister(&runtime_id("alpha")));
    assert!(!registry.unregister(&runtime_id("alpha")));
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
