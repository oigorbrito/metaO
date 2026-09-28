use metao_contracts::credential_lease::{
    CredentialLease, CredentialLeaseAssurance, CredentialLeaseBinding, CredentialLeaseError,
    CredentialLeaseEvidenceBasis, CredentialRevocationStatus,
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
        evidence_basis: CredentialLeaseEvidenceBasis::BrokerVerified,
        revocation_status: CredentialRevocationStatus::Active,
        revocation_evidence_ref: None,
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
fn caller_declared_or_unknown_origin_cannot_mint_brokered_lease() {
    for basis in [
        CredentialLeaseEvidenceBasis::CallerDeclared,
        CredentialLeaseEvidenceBasis::Unknown,
        CredentialLeaseEvidenceBasis::DevelopmentLocal,
    ] {
        let mut value = lease();
        value.evidence_basis = basis;
        assert_eq!(
            value.validate(),
            Err(CredentialLeaseError::InvalidEvidenceBasis)
        );
        assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 150));
    }
}

#[test]
fn confirmed_revocation_requires_broker_verified_origin_and_evidence() {
    let mut value = lease();
    value.revocation_status = CredentialRevocationStatus::Revoked;
    value.revocation_evidence_ref = Some("broker-revoke:receipt-7".to_string());
    assert!(!value.applies_to(&binding("runtime-a", "exec-a"), 150));
    assert!(value.revocation_confirmed());
}

#[test]
fn textual_revocation_receipt_without_broker_origin_is_not_confirmation() {
    for basis in [
        CredentialLeaseEvidenceBasis::CallerDeclared,
        CredentialLeaseEvidenceBasis::Unknown,
        CredentialLeaseEvidenceBasis::DevelopmentLocal,
    ] {
        let mut value = lease();
        value.evidence_basis = basis;
        value.revocation_status = CredentialRevocationStatus::Revoked;
        value.revocation_evidence_ref = Some("broker-revoke:receipt-7".to_string());
        assert_eq!(
            value.validate(),
            Err(CredentialLeaseError::InvalidEvidenceBasis)
        );
        assert!(!value.revocation_confirmed());
    }
}

#[test]
fn revoked_enum_without_confirmation_evidence_fails_closed() {
    for evidence in [None, Some(String::new()), Some("   ".to_string())] {
        let mut value = lease();
        value.revocation_status = CredentialRevocationStatus::Revoked;
        value.revocation_evidence_ref = evidence;
        assert_eq!(
            value.validate(),
            Err(CredentialLeaseError::MissingRevocationEvidence)
        );
        assert!(!value.revocation_confirmed());
    }
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
fn renewable_lease_requires_explicit_future_maximum() {
    let mut missing = lease();
    missing.max_expires_at_epoch = None;
    assert_eq!(
        missing.validate(),
        Err(CredentialLeaseError::InvalidRenewalBound)
    );

    let mut no_extension = lease();
    no_extension.max_expires_at_epoch = Some(no_extension.expires_at_epoch);
    assert_eq!(
        no_extension.validate(),
        Err(CredentialLeaseError::InvalidRenewalBound)
    );
}

#[test]
fn renewal_is_monotonic_and_respects_provider_maximum() {
    let value = lease();
    assert!(!value.can_renew_to(199, 150));
    assert!(!value.can_renew_to(200, 150));
    assert!(value.can_renew_to(250, 150));
    assert!(value.can_renew_to(300, 150));
    assert!(!value.can_renew_to(301, 150));
}

#[test]
fn nonrenewable_lease_has_no_renewal_bound_and_cannot_be_extended() {
    let mut value = lease();
    value.renewable = false;
    value.max_expires_at_epoch = None;
    assert!(value.validate().is_ok());
    assert!(!value.can_renew_to(250, 150));

    value.max_expires_at_epoch = Some(300);
    assert_eq!(
        value.validate(),
        Err(CredentialLeaseError::InvalidRenewalBound)
    );
}

#[test]
fn development_static_mode_is_explicit_lower_assurance() {
    let mut value = lease();
    value.assurance = CredentialLeaseAssurance::DevelopmentStatic;
    value.evidence_basis = CredentialLeaseEvidenceBasis::DevelopmentLocal;
    let encoded = serde_json::to_string(&value).expect("serialize");
    assert!(encoded.contains("DevelopmentStatic"));
    assert!(encoded.contains("DevelopmentLocal"));
    assert!(!encoded.contains("production_attested"));
}

#[test]
fn development_static_requires_local_evidence_basis() {
    let mut value = lease();
    value.assurance = CredentialLeaseAssurance::DevelopmentStatic;
    value.evidence_basis = CredentialLeaseEvidenceBasis::BrokerVerified;
    assert_eq!(
        value.validate(),
        Err(CredentialLeaseError::InvalidEvidenceBasis)
    );
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
