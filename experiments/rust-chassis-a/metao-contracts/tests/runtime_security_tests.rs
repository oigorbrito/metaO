use std::collections::BTreeSet;

use metao_contracts::runtime_security::{
    evaluate_runtime_security, IsolationAssurance, RuntimeSecurityAdmission, RuntimeSecurityBinding,
    RuntimeSecurityError, RuntimeSecurityEvidenceBasis, RuntimeSecurityFacts, RuntimeSecurityProfile,
};

fn binding(runtime: &str) -> RuntimeSecurityBinding {
    RuntimeSecurityBinding {
        runtime_id: runtime.to_string(),
        runtime_version: "1.0.0".to_string(),
        config_id: "cfg-a".to_string(),
    }
}

fn facts(runtime: &str) -> RuntimeSecurityFacts {
    RuntimeSecurityFacts {
        binding: binding(runtime),
        isolation: IsolationAssurance::ContainerOrEquivalent,
        effective_permissions: BTreeSet::from(["network:egress:api.example".to_string()]),
        secret_redaction_enforced: Some(true),
        untrusted_content_isolated_from_governance: Some(true),
        enforcement_capabilities: BTreeSet::from([
            "tool-permission-boundary".to_string(),
            "workspace-isolation".to_string(),
        ]),
        evidence_basis: RuntimeSecurityEvidenceBasis::AdapterVerified,
        evidence_ref: "security-evidence:runtime-a:1".to_string(),
    }
}

fn profile() -> RuntimeSecurityProfile {
    RuntimeSecurityProfile {
        minimum_isolation: IsolationAssurance::Process,
        allowed_permissions: BTreeSet::from(["network:egress:api.example".to_string()]),
        require_secret_redaction: true,
        require_untrusted_content_isolation: true,
        required_capabilities: BTreeSet::from(["tool-permission-boundary".to_string()]),
    }
}

#[test]
fn sufficient_verified_evidence_satisfies_generic_security_profile() {
    let result = evaluate_runtime_security(&facts("runtime-a"), &profile(), &binding("runtime-a"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Satisfied);
}

#[test]
fn unknown_cannot_be_used_as_policy_minimum() {
    let mut invalid = profile();
    invalid.minimum_isolation = IsolationAssurance::Unknown;
    assert_eq!(
        invalid.validate(),
        Err(RuntimeSecurityError::InvalidMinimumIsolation)
    );
}

#[test]
fn none_is_explicit_no_isolation_minimum_when_other_requirements_exist() {
    let mut explicit_none = profile();
    explicit_none.minimum_isolation = IsolationAssurance::None;
    assert!(explicit_none.validate().is_ok());
    let result = evaluate_runtime_security(
        &facts("runtime-a"),
        &explicit_none,
        &binding("runtime-a"),
    )
    .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Satisfied);
}

#[test]
fn empty_profile_with_no_isolation_minimum_fails_closed() {
    let empty = RuntimeSecurityProfile {
        minimum_isolation: IsolationAssurance::None,
        allowed_permissions: BTreeSet::new(),
        require_secret_redaction: false,
        require_untrusted_content_isolation: false,
        required_capabilities: BTreeSet::new(),
    };
    assert_eq!(empty.validate(), Err(RuntimeSecurityError::EmptyProfile));
}

#[test]
fn runtime_self_report_cannot_prove_enforcement() {
    for basis in [
        RuntimeSecurityEvidenceBasis::SelfReported,
        RuntimeSecurityEvidenceBasis::Unknown,
    ] {
        let mut value = facts("runtime-a");
        value.evidence_basis = basis;
        let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
            .expect("projection");
        assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
        assert!(result
            .reasons
            .iter()
            .any(|reason| reason.contains("not backed by independent or adapter-verified evidence")));
    }
}

#[test]
fn independent_observation_can_support_same_generic_contract() {
    let mut value = facts("runtime-a");
    value.evidence_basis = RuntimeSecurityEvidenceBasis::IndependentObservation;
    let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Satisfied);
}

#[test]
fn unknown_or_insufficient_isolation_fails_closed() {
    for isolation in [IsolationAssurance::Unknown, IsolationAssurance::None] {
        let mut value = facts("runtime-a");
        value.isolation = isolation;
        let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
            .expect("projection");
        assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
    }
}

#[test]
fn permission_escalation_is_rejected() {
    let mut value = facts("runtime-a");
    value.effective_permissions.insert("filesystem:root".to_string());
    let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
}

#[test]
fn blank_permission_or_capability_entries_fail_validation() {
    let mut blank_permission = facts("runtime-a");
    blank_permission.effective_permissions.insert("   ".to_string());
    assert!(evaluate_runtime_security(
        &blank_permission,
        &profile(),
        &binding("runtime-a")
    )
    .is_err());

    let mut blank_capability = facts("runtime-a");
    blank_capability
        .enforcement_capabilities
        .insert("   ".to_string());
    assert!(evaluate_runtime_security(
        &blank_capability,
        &profile(),
        &binding("runtime-a")
    )
    .is_err());

    let mut invalid_profile = profile();
    invalid_profile.allowed_permissions.insert("   ".to_string());
    assert!(evaluate_runtime_security(
        &facts("runtime-a"),
        &invalid_profile,
        &binding("runtime-a")
    )
    .is_err());
}

#[test]
fn missing_secret_redaction_proof_is_rejected() {
    let mut value = facts("runtime-a");
    value.secret_redaction_enforced = None;
    let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
}

#[test]
fn untrusted_content_must_be_isolated_from_governance_authority() {
    let mut value = facts("runtime-a");
    value.untrusted_content_isolated_from_governance = Some(false);
    let result = evaluate_runtime_security(&value, &profile(), &binding("runtime-a"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
}

#[test]
fn missing_evidence_reference_fails_validation() {
    let mut value = facts("runtime-a");
    value.evidence_ref = " ".to_string();
    assert!(evaluate_runtime_security(&value, &profile(), &binding("runtime-a")).is_err());
}

#[test]
fn stale_runtime_binding_is_rejected() {
    let result = evaluate_runtime_security(&facts("runtime-a"), &profile(), &binding("runtime-b"))
        .expect("projection");
    assert_eq!(result.admission, RuntimeSecurityAdmission::Rejected);
}

#[test]
fn two_runtimes_use_same_generic_security_shape() {
    let first = evaluate_runtime_security(&facts("runtime-a"), &profile(), &binding("runtime-a"))
        .expect("first");
    let mut second_facts = facts("runtime-b");
    second_facts.evidence_ref = "security-evidence:runtime-b:1".to_string();
    let second = evaluate_runtime_security(&second_facts, &profile(), &binding("runtime-b"))
        .expect("second");
    assert_eq!(first.admission, RuntimeSecurityAdmission::Satisfied);
    assert_eq!(second.admission, RuntimeSecurityAdmission::Satisfied);
    assert_ne!(first.binding.runtime_id, second.binding.runtime_id);
}

#[test]
fn serialization_contains_no_plugin_paths_or_authority_grants() {
    let projection = evaluate_runtime_security(&facts("runtime-a"), &profile(), &binding("runtime-a"))
        .expect("projection");
    let encoded = serde_json::to_string(&projection).expect("serialize");
    for forbidden in [
        "AcceptanceDecision",
        "PolicyEffect",
        "approval",
        "dispatch",
        "git_path",
        "worktree",
        "capability_grant",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
