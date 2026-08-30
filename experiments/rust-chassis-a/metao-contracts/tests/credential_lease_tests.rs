use metao_contracts::credential_lease::{
    CredentialLease, CredentialLeaseAssurance, CredentialLeaseBinding, CredentialRevocationStatus,
};

fn binding(runtime: &str, execution: &str) -> CredentialLeaseBinding {
    CredentialLeaseBinding {
        runtime_id: runtime.to_string(),
        workload_identity: format!("spiffe://example.org/{runtime}"),
        runtime_config_id: "cfg-1".to_string(),
        mission_id: "mission-1".to_string(),
        execution_id: execution.to_string(),
    }
}

fn lease() -> CredentialLease {
    CredentialLease {
        lease_ref: "broker:lease:opaque-1".to_string(),
        binding: binding("runtime-a", "exec-a"),
        credential_class: "database-readonly".to_string(),
        target_service: "orders-db".to_string(),
        policy_authority_ref: "policy-bundle-7".to_string(),
        issued_at_epoch: 100,
        expires_at_epoch: 200,
        renewable: true,
        max_expires_at_epoch: Some(300),
        assurance: CredentialLeaseAssurance::Brokered,
        revocation_status: CredentialRevocationStatus::Active,
    }
}

#[test]
fn active_brokered_lease_applies_only_with_exact_binding_and_time() {
    let value = lease();
    assert!(value.applies_to(&binding("runtime-a", "exec-a"), 150));
    assert!(!value.applies_to(&binding("runtime-b", "exec-b"), 150));
    assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 200));
}

#[test]
fn failover_runtime_must_obtain_its_own_lease() {
    let value = lease();
    let failover = binding("runtime-b", "exec-b");
    assert!(!value.applies_to(&failover, 150));
}

#[test]
fn confirmed_revocation_invalidates_future_use() {
    let mut value = lease();
    value.revocation_status = CredentialRevocationStatus::Revoked;
    assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 150));
    assert!(value.revocation_confirmed());
}

#[test]
fn unknown_revocation_is_not_revoked_success_and_not_usable() {
    let mut value = lease();
    value.revocation_status = CredentialRevocationStatus::RevocationUnknown;
    assert!(!value.revocation_confirmed());
    assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 150));
}

#[test]
fn expired_status_is_not_usable_even_before_timestamp_expiry() {
    let mut value = lease();
    value.revocation_status = CredentialRevocationStatus::Expired;
    assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 150));
}

#[test]
fn renewal_respects_provider_maximum() {
    let value = lease();
    assert!(value.can_renew_to(250, 150));
    assert!(value.can_renew_to(300, 150));
    assert!(!value.can_renew_to(301, 150));
}

#[test]
fn nonrenewable_lease_cannot_be_extended() {
    let mut value = lease();
    value.renewable = false;
    assert!(!value.can_renew_to(250, 150));
}

#[test]
fn development_static_mode_is_explicit_lower_assurance() {
    let mut value = lease();
    value.assurance = CredentialLeaseAssurance::DevelopmentStatic;
    let encoded = serde_json::to_string(&value).expect("serialize");
    assert!(encoded.contains("DevelopmentStatic"));
    assert!(!encoded.contains("production_attested"));
}

#[test]
fn canonical_fact_contains_no_secret_material_fields_or_policy_authority() {
    let value = lease();
    let encoded = serde_json::to_string(&value).expect("serialize");
    let decoded: CredentialLease = serde_json::from_str(&encoded).expect("deserialize");
    assert_eq!(decoded, value);
    for forbidden in [
        "password",
        "private_key",
        "client_secret",
        "bearer_token",
        "secret_value",
        "AcceptanceDecision",
        "PolicyEffect",
        "dispatch",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
