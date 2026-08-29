use std::sync::{Arc, Mutex};

use metao_contracts::{
    AcceptanceBudget, AcceptanceDecision, ContractError, ExecutionId, MissionId,
    VerificationAttemptId, VerificationRequest, VerificationRequestId, VerificationUsage,
    VerifierDescriptor, VerifierId, VerifierPort, VerifierResult,
};
use metao_kernel::{canonical_acceptance, execute_verification, VerificationAccountingAuthority};
use metao_registry::VerifierRegistry;

fn mission_id(value: &str) -> MissionId {
    MissionId::new(value).unwrap()
}

fn execution_id(value: &str) -> ExecutionId {
    ExecutionId::new(value).unwrap()
}

fn verifier_id(value: &str) -> VerifierId {
    VerifierId::new(value).unwrap()
}

fn request_id(value: &str) -> VerificationRequestId {
    VerificationRequestId::new(value).unwrap()
}

fn attempt_id(value: &str) -> VerificationAttemptId {
    VerificationAttemptId::new(value).unwrap()
}

fn base_request(capability: &str, attempt: &str) -> VerificationRequest {
    VerificationRequest {
        request_id: request_id("request-1"),
        attempt_id: attempt_id(attempt),
        mission_id: mission_id("mission-1"),
        execution_id: execution_id("exec-1"),
        capability: capability.into(),
    }
}

fn usage(
    attempt: &str,
    money: Option<f64>,
    tokens: Option<u64>,
    wall_time: Option<f64>,
) -> VerificationUsage {
    VerificationUsage {
        attempt_id: attempt_id(attempt),
        money,
        tokens,
        wall_time_s: wall_time,
        verifier_attempts: Some(1),
    }
}

#[derive(Clone)]
enum Behavior {
    Pass,
    Fail,
    Panic,
    RequestMismatch,
    VerifierMismatch,
    MissingUsage,
}

struct TestVerifier {
    descriptor: VerifierDescriptor,
    accounting: Arc<VerificationAccountingAuthority>,
    behavior: Behavior,
    started_seen: Arc<Mutex<Option<bool>>>,
    usage: VerificationUsage,
}

impl VerifierPort for TestVerifier {
    fn descriptor(&self) -> VerifierDescriptor {
        self.descriptor.clone()
    }

    fn verify(&self, request: &VerificationRequest) -> VerifierResult {
        *self.started_seen.lock().unwrap() = Some(
            self.accounting
                .attempt_started(&request.attempt_id)
                .is_some(),
        );
        match self.behavior {
            Behavior::Panic => panic!("simulated verifier failure"),
            Behavior::RequestMismatch => VerifierResult {
                request_id: request_id("other-request"),
                attempt_id: request.attempt_id.clone(),
                verifier_id: self.descriptor.verifier_id.clone(),
                verifier_version: self.descriptor.version.clone(),
                passed: true,
                reason: "mismatched request".into(),
                score: Some(0.9),
                confidence: Some(0.9),
                usage: self.usage.clone(),
            },
            Behavior::VerifierMismatch => VerifierResult {
                request_id: request.request_id.clone(),
                attempt_id: request.attempt_id.clone(),
                verifier_id: verifier_id("forged"),
                verifier_version: "forged-version".into(),
                passed: true,
                reason: "mismatched verifier".into(),
                score: Some(0.9),
                confidence: Some(0.9),
                usage: self.usage.clone(),
            },
            Behavior::MissingUsage => VerifierResult {
                request_id: request.request_id.clone(),
                attempt_id: request.attempt_id.clone(),
                verifier_id: self.descriptor.verifier_id.clone(),
                verifier_version: self.descriptor.version.clone(),
                passed: true,
                reason: "missing usage".into(),
                score: Some(0.9),
                confidence: Some(0.9),
                usage: usage(request.attempt_id.as_str(), None, None, Some(0.25)),
            },
            Behavior::Fail => VerifierResult {
                request_id: request.request_id.clone(),
                attempt_id: request.attempt_id.clone(),
                verifier_id: self.descriptor.verifier_id.clone(),
                verifier_version: self.descriptor.version.clone(),
                passed: false,
                reason: "explicit fail".into(),
                score: Some(0.0),
                confidence: Some(0.0),
                usage: self.usage.clone(),
            },
            Behavior::Pass => VerifierResult {
                request_id: request.request_id.clone(),
                attempt_id: request.attempt_id.clone(),
                verifier_id: self.descriptor.verifier_id.clone(),
                verifier_version: self.descriptor.version.clone(),
                passed: true,
                reason: "explicit pass".into(),
                score: Some(1.0),
                confidence: Some(1.0),
                usage: self.usage.clone(),
            },
        }
    }
}

fn descriptor(id: &str, version: &str, capabilities: Vec<&str>) -> VerifierDescriptor {
    VerifierDescriptor {
        verifier_id: verifier_id(id),
        version: version.into(),
        capabilities: capabilities.into_iter().map(String::from).collect(),
    }
}

fn register(
    registry: &mut VerifierRegistry,
    accounting: Arc<VerificationAccountingAuthority>,
    descriptor: VerifierDescriptor,
    behavior: Behavior,
    usage: VerificationUsage,
) -> Arc<Mutex<Option<bool>>> {
    let started_seen = Arc::new(Mutex::new(None));
    registry
        .register(Box::new(TestVerifier {
            descriptor,
            accounting,
            behavior,
            started_seen: started_seen.clone(),
            usage,
        }))
        .unwrap();
    started_seen
}

#[test]
fn t01_authorized_verifier_executes() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    let started_seen = register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.25), Some(5), Some(2.5)),
    );
    let outcome = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("authorized verifier should execute");
    assert!(outcome.verifier_result.passed);
    assert_eq!(*started_seen.lock().unwrap(), Some(true));
}

#[test]
fn t02_registry_selection_is_metao_owned() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("beta", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let selected = registry
        .select_eligible("analysis")
        .expect("eligible verifier");
    assert_eq!(selected.verifier_id, verifier_id("alpha"));
}

#[test]
fn t03_caller_fabricated_verifier_authority_rejected() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::VerifierMismatch,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("binding mismatch must fail closed");
    assert_eq!(err, ContractError::InvalidVerificationBinding);
}

#[test]
fn t04_verifier_pass_cannot_mint_metao_accepted() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let outcome = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("pass still only yields verification result");
    assert!(outcome.verifier_result.passed);
    let acceptance = canonical_acceptance(
        &metao_contracts::AcceptanceContext {
            subject_id: "subject-1".into(),
            subject_state_id: "state-1".into(),
            verification_context_id: "ctx-1".into(),
            policy_bundle_id: "policy-1".into(),
            required_obligations: vec!["must-pass".into()],
            trusted_verifiers: vec![],
            trusted_provenance_roots: vec![],
            authorized_authorities: vec![],
        },
        &[],
        1.0,
    );
    assert_eq!(acceptance.decision, AcceptanceDecision::NotDone);
}

#[test]
fn t05_attempt_start_exists_before_invocation() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    let started_seen = register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("attempt should be recorded before invocation");
    assert_eq!(*started_seen.lock().unwrap(), Some(true));
}

#[test]
fn t06_verifier_exception_preserves_attempt_start() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Panic,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("panic must be contained");
    assert_eq!(err, ContractError::VerificationPanic("alpha".into()));
    assert!(accounting
        .attempt_started(&attempt_id("attempt-1"))
        .is_some());
}

#[test]
fn t07_invalid_result_request_binding_fails_closed() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::RequestMismatch,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("request binding mismatch must fail closed");
    assert_eq!(err, ContractError::InvalidVerificationBinding);
}

#[test]
fn t08_invalid_verifier_binding_fails_closed() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::VerifierMismatch,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("verifier binding mismatch must fail closed");
    assert_eq!(err, ContractError::InvalidVerificationBinding);
}

#[test]
fn t09_exact_usage_appended() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.25), Some(5), Some(2.5)),
    );
    execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("usage should be appended");
    assert_eq!(
        accounting.usage(&attempt_id("attempt-1")).unwrap(),
        usage("attempt-1", Some(1.25), Some(5), Some(2.5))
    );
}

#[test]
fn t10_budget_consumes_exact_facts() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.25), Some(5), Some(2.5)),
    );
    let outcome = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("budget should consume exact usage");
    assert_eq!(outcome.budget.money_used, 1.25);
    assert_eq!(outcome.budget.tokens_used, 5);
    assert_eq!(outcome.budget.wall_time_used_s, 2.5);
    assert_eq!(outcome.budget.verifier_attempts_used, 1);
}

#[test]
fn t11_over_budget_usage_remains_persisted() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(1.0, 1, 1.0, 1).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(2.0), Some(2), Some(2.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("over budget must fail closed");
    assert_eq!(err, ContractError::BudgetExhausted);
    assert!(accounting.usage(&attempt_id("attempt-1")).is_some());
    assert!(accounting
        .attempt_started(&attempt_id("attempt-1"))
        .is_some());
}

#[test]
fn t12_unknown_exact_money_tokens_not_fabricated_as_zero() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::MissingUsage,
        usage("attempt-1", None, None, Some(1.0)),
    );
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("missing exact usage must fail closed");
    assert_eq!(err, ContractError::MissingUsageFact("money"));
    let stored = accounting.usage(&attempt_id("attempt-1")).unwrap();
    assert_eq!(stored.money, None);
    assert_eq!(stored.tokens, None);
}

#[test]
fn t13_duplicate_attempt_identity_deterministic_failure() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("first attempt should succeed");
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("duplicate attempt id must fail");
    assert_eq!(
        err,
        ContractError::DuplicateVerificationAttempt("attempt-1".into())
    );
}

#[test]
fn t14_missing_verifier_fail_closed() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let registry = VerifierRegistry::default();
    let err = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect_err("missing verifier must fail closed");
    assert_eq!(err, ContractError::UnknownVerifier("analysis".into()));
}

#[test]
fn t15_explicit_fail_records_attempt_and_usage() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Fail,
        usage("attempt-1", Some(0.5), Some(1), Some(0.25)),
    );
    let outcome = execute_verification(
        &registry,
        &accounting,
        base_request("analysis", "attempt-1"),
        1.0,
    )
    .expect("explicit verifier fail still yields a verifier result");
    assert!(!outcome.verifier_result.passed);
    assert_eq!(outcome.verifier_result.reason, "explicit fail");
    assert!(accounting
        .attempt_started(&attempt_id("attempt-1"))
        .is_some());
    assert!(accounting.usage(&attempt_id("attempt-1")).is_some());
    assert_eq!(
        canonical_acceptance(
            &metao_contracts::AcceptanceContext {
                subject_id: "subject-1".into(),
                subject_state_id: "state-1".into(),
                verification_context_id: "ctx-1".into(),
                policy_bundle_id: "policy-1".into(),
                required_obligations: vec!["must-pass".into()],
                trusted_verifiers: vec![],
                trusted_provenance_roots: vec![],
                authorized_authorities: vec![],
            },
            &[],
            1.0,
        )
        .decision,
        AcceptanceDecision::NotDone
    );
}

#[test]
fn t16_duplicate_verifier_registration_is_deterministic() {
    let accounting = Arc::new(VerificationAccountingAuthority::new(
        AcceptanceBudget::new(10.0, 10, 10.0, 10).unwrap(),
    ));
    let mut registry = VerifierRegistry::default();
    register(
        &mut registry,
        accounting.clone(),
        descriptor("alpha", "1", vec!["analysis"]),
        Behavior::Pass,
        usage("attempt-1", Some(1.0), Some(1), Some(1.0)),
    );
    let err = registry.register(Box::new(TestVerifier {
        descriptor: descriptor("alpha", "1", vec!["analysis"]),
        accounting,
        behavior: Behavior::Pass,
        started_seen: Arc::new(Mutex::new(None)),
        usage: usage("attempt-2", Some(1.0), Some(1), Some(1.0)),
    }));
    assert_eq!(
        err,
        Err(metao_registry::VerifierRegistryError::Duplicate(
            verifier_id("alpha")
        ))
    );
}
