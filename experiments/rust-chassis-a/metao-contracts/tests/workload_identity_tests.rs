use metao_contracts::workload_identity::{
    RuntimeIdentityBinding, RuntimeWorkloadIdentity, WorkloadCredentialKind,
    WorkloadIdentityAssurance, WorkloadIdentityError,
};

fn binding() -> RuntimeIdentityBinding {
    RuntimeIdentityBinding {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.2.3".to_string(),
        config_id: "config-7".to_string(),
    }
}

fn attested() -> RuntimeWorkloadIdentity {
    RuntimeWorkloadIdentity {
        binding: binding(),
        workload_subject: "spiffe://example.org/runtime/a".to_string(),
        trust_domain: "example.org".to_string(),
        credential_kind: WorkloadCredentialKind::X509Svid,
        assurance: WorkloadIdentityAssurance::Attested,
        trust_root_ref: Some("bundle:example.org:v4".to_string()),
        credential_ref: Some("sha256:credential-fingerprint".to_string()),
        verifier_provenance: Some("spire-agent:v1.15.3".to_string()),
        issued_at_epoch: Some(100),
        expires_at_epoch: Some(200),
        verified_at_epoch: Some(120),
    }
}

#[test]
fn valid_attested_identity_requires_explicit_verification_facts() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid attested identity");
    assert_eq!(value.assurance, WorkloadIdentityAssurance::Attested);
    assert!(value.is_currently_applicable(150));
}

#[test]
fn missing_trust_root_rejects_attested_identity() {
    let mut value = attested();
    value.trust_root_ref = None;
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::BlankTrustRootRef)
    );
}

#[test]
fn missing_credential_reference_rejects_attested_identity() {
    let mut value = attested();
    value.credential_ref = Some(" ".to_string());
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::BlankCredentialRef)
    );
}

#[test]
fn missing_verifier_provenance_rejects_attested_identity() {
    let mut value = attested();
    value.verifier_provenance = None;
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::BlankVerifierProvenance)
    );
}

#[test]
fn development_identity_cannot_claim_attested_assurance() {
    let mut value = attested();
    value.credential_kind = WorkloadCredentialKind::Development;
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::InvalidAttestedCredential)
    );
}

#[test]
fn development_fallback_is_explicitly_lower_assurance() {
    let mut value = attested();
    value.credential_kind = WorkloadCredentialKind::Development;
    value.assurance = WorkloadIdentityAssurance::Development;
    value.trust_root_ref = None;
    value.credential_ref = None;
    value.verifier_provenance = Some("local-development".to_string());
    let value = RuntimeWorkloadIdentity::new(value).expect("development identity");
    assert!(!value.is_currently_applicable(150));
}

#[test]
fn expired_attested_identity_is_not_applicable() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert!(!value.is_currently_applicable(200));
    assert!(!value.is_currently_applicable(201));
}

#[test]
fn not_yet_valid_attested_identity_is_not_applicable() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert!(!value.is_currently_applicable(99));
}

#[test]
fn runtime_version_or_config_mismatch_prevents_applicability() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert!(value.applies_to("runtime-a", "1.2.3", "config-7"));
    assert!(!value.applies_to("runtime-b", "1.2.3", "config-7"));
    assert!(!value.applies_to("runtime-a", "1.2.4", "config-7"));
    assert!(!value.applies_to("runtime-a", "1.2.3", "config-8"));
}

#[test]
fn invalid_validity_window_fails_closed() {
    let mut value = attested();
    value.expires_at_epoch = Some(100);
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::InvalidValidityWindow)
    );
}

#[test]
fn unsupported_identity_remains_explicit() {
    let mut value = attested();
    value.credential_kind = WorkloadCredentialKind::Unsupported;
    value.assurance = WorkloadIdentityAssurance::Unsupported;
    value.trust_root_ref = None;
    value.credential_ref = None;
    value.verifier_provenance = Some("adapter:no-identity-support".to_string());
    let value = RuntimeWorkloadIdentity::new(value).expect("unsupported fact");
    assert_eq!(value.assurance, WorkloadIdentityAssurance::Unsupported);
    assert!(!value.is_currently_applicable(150));
}

#[test]
fn serialization_contains_identity_facts_but_no_authorization_authority() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let encoded = serde_json::to_string(&value).expect("serialize");
    let decoded: RuntimeWorkloadIdentity = serde_json::from_str(&encoded).expect("deserialize");
    assert_eq!(decoded, value);

    for forbidden in [
        "private_key",
        "bearer_token",
        "secret",
        "AcceptanceDecision",
        "PolicyEffect",
        "approval",
        "capability_grant",
        "dispatch",
    ] {
        assert!(!encoded.contains(forbidden));
    }
}
