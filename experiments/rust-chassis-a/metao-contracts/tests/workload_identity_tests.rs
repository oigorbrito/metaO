use metao_contracts::execution_lease::BoundExecutionRuntimeIdentity;
use metao_contracts::workload_identity::{
    RuntimeIdentityBinding, RuntimeWorkloadIdentity, WorkloadCredentialKind,
    WorkloadIdentityAdmissionError, WorkloadIdentityAssurance, WorkloadIdentityError,
    WorkloadIdentityEvidenceBasis, WorkloadIdentityTrustConfiguration,
    WorkloadIdentityTrustConfigurationBasis,
};
use metao_contracts::{EvidenceEnvelope, ExecutionId, MissionId, RuntimeId};
use std::collections::BTreeSet;

fn binding() -> RuntimeIdentityBinding {
    RuntimeIdentityBinding {
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.2.3".to_string(),
        config_id: "config-7".to_string(),
    }
}

fn trust_configuration() -> WorkloadIdentityTrustConfiguration {
    WorkloadIdentityTrustConfiguration {
        configuration_ref: "trust-config:prod:v4".to_string(),
        trust_domain: "example.org".to_string(),
        trusted_root_refs: BTreeSet::from(["bundle:example.org:v4".to_string()]),
        basis: WorkloadIdentityTrustConfigurationBasis::AuthoritativeConfiguration,
    }
}

fn execution_identity() -> BoundExecutionRuntimeIdentity {
    BoundExecutionRuntimeIdentity {
        producer_id: "canonical-dispatch".to_string(),
        mission_id: "mission-1".to_string(),
        logical_execution_key: "logical-1".to_string(),
        execution_id: "exec-1".to_string(),
        runtime_id: "runtime-a".to_string(),
        runtime_version: "1.2.3".to_string(),
        config_id: "config-7".to_string(),
        lease_generation: 4,
        fencing_token: 9,
        evidence_ref: "dispatch-evidence-1".to_string(),
    }
}

fn evidence() -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "evidence-1".to_string(),
        obligation_id: "obligation-1".to_string(),
        mission_id: MissionId::new("mission-1").expect("mission id"),
        execution_id: ExecutionId::new("exec-1").expect("execution id"),
        orchestrator_id: RuntimeId::new("runtime-a").expect("runtime id"),
        adapter_version: "adapter-v1".to_string(),
        attempt_id: "attempt-1".to_string(),
        subject_id: "subject-1".to_string(),
        subject_state_id: "subject-state-1".to_string(),
        verification_context_id: "verify-context-1".to_string(),
        policy_bundle_id: "policy-1".to_string(),
        verifier_id: "verifier-1".to_string(),
        payload_digest: "sha256:payload".to_string(),
        provenance_root: "provenance-root-1".to_string(),
        authority_id: "authority-1".to_string(),
        passed: true,
        created_at_epoch: 150.0,
        expires_at_epoch: Some(180.0),
        approval_id: None,
        confidence: Some(1.0),
    }
}

fn attested() -> RuntimeWorkloadIdentity {
    RuntimeWorkloadIdentity {
        binding: binding(),
        workload_subject: "spiffe://example.org/runtime/a".to_string(),
        trust_domain: "example.org".to_string(),
        credential_kind: WorkloadCredentialKind::X509Svid,
        assurance: WorkloadIdentityAssurance::Attested,
        evidence_basis: WorkloadIdentityEvidenceBasis::IdentityProviderVerified,
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
fn spiffe_svid_subject_must_match_declared_trust_domain() {
    for credential_kind in [
        WorkloadCredentialKind::X509Svid,
        WorkloadCredentialKind::JwtSvid,
    ] {
        let mut value = attested();
        value.credential_kind = credential_kind;
        value.workload_subject = "spiffe://evil.example/runtime/a".to_string();
        assert_eq!(
            RuntimeWorkloadIdentity::new(value),
            Err(WorkloadIdentityError::SpiffeTrustDomainMismatch)
        );
    }
}

#[test]
fn spiffe_subject_without_path_separator_cannot_match_longer_domain_prefix() {
    let mut value = attested();
    value.workload_subject = "spiffe://example.org.evil/runtime/a".to_string();
    assert_eq!(
        RuntimeWorkloadIdentity::new(value),
        Err(WorkloadIdentityError::SpiffeTrustDomainMismatch)
    );
}

#[test]
fn other_attested_identity_is_not_forced_into_spiffe_uri_shape() {
    let mut value = attested();
    value.credential_kind = WorkloadCredentialKind::OtherAttested;
    value.workload_subject = "provider-neutral-workload-subject".to_string();
    let value = RuntimeWorkloadIdentity::new(value).expect("provider-neutral attested identity");
    assert_eq!(value.credential_kind, WorkloadCredentialKind::OtherAttested);
}

#[test]
fn self_report_or_unknown_basis_cannot_mint_attested_identity() {
    for basis in [
        WorkloadIdentityEvidenceBasis::SelfReported,
        WorkloadIdentityEvidenceBasis::Unknown,
    ] {
        let mut value = attested();
        value.evidence_basis = basis;
        assert_eq!(
            RuntimeWorkloadIdentity::new(value),
            Err(WorkloadIdentityError::InvalidVerificationBasis)
        );
    }
}

#[test]
fn independent_verifier_can_support_attested_identity() {
    let mut value = attested();
    value.evidence_basis = WorkloadIdentityEvidenceBasis::IndependentVerifier;
    let value = RuntimeWorkloadIdentity::new(value).expect("independently verified identity");
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
fn attested_identity_requires_issued_expiry_and_verified_timestamps() {
    let mut missing_issued = attested();
    missing_issued.issued_at_epoch = None;
    assert_eq!(
        RuntimeWorkloadIdentity::new(missing_issued),
        Err(WorkloadIdentityError::MissingIssuedAt)
    );

    let mut missing_expiry = attested();
    missing_expiry.expires_at_epoch = None;
    assert_eq!(
        RuntimeWorkloadIdentity::new(missing_expiry),
        Err(WorkloadIdentityError::MissingExpiresAt)
    );

    let mut missing_verified = attested();
    missing_verified.verified_at_epoch = None;
    assert_eq!(
        RuntimeWorkloadIdentity::new(missing_verified),
        Err(WorkloadIdentityError::MissingVerifiedAt)
    );
}

#[test]
fn verification_time_must_be_inside_credential_validity_window() {
    for verified_at in [99, 200, 201] {
        let mut value = attested();
        value.verified_at_epoch = Some(verified_at);
        assert_eq!(
            RuntimeWorkloadIdentity::new(value),
            Err(WorkloadIdentityError::InvalidValidityWindow)
        );
    }
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
    value.evidence_basis = WorkloadIdentityEvidenceBasis::Unknown;
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
fn invalid_public_struct_cannot_bypass_applicability_validation() {
    let mut value = attested();
    value.verified_at_epoch = None;
    assert!(!value.is_currently_applicable(150));
    assert!(!value.applies_to("runtime-a", "1.2.3", "config-7"));
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
    value.evidence_basis = WorkloadIdentityEvidenceBasis::Unknown;
    value.trust_root_ref = None;
    value.credential_ref = None;
    value.verifier_provenance = Some("adapter:no-identity-support".to_string());
    let value = RuntimeWorkloadIdentity::new(value).expect("unsupported fact");
    assert_eq!(value.assurance, WorkloadIdentityAssurance::Unsupported);
    assert!(!value.is_currently_applicable(150));
}

#[test]
fn authoritative_trust_configuration_admits_matching_attested_identity() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &trust_configuration(), 150),
        Ok(())
    );
}

#[test]
fn caller_declared_trust_configuration_is_never_authoritative() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let mut configuration = trust_configuration();
    configuration.basis = WorkloadIdentityTrustConfigurationBasis::CallerDeclared;

    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &configuration, 150),
        Err(WorkloadIdentityAdmissionError::NonAuthoritativeTrustConfiguration)
    );
}

#[test]
fn caller_presented_root_must_exist_in_authoritative_configuration() {
    let mut value = attested();
    value.trust_root_ref = Some("bundle:attacker:v1".to_string());
    let value = RuntimeWorkloadIdentity::new(value).expect("structurally valid identity");

    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &trust_configuration(), 150),
        Err(WorkloadIdentityAdmissionError::UntrustedTrustRoot)
    );
}

#[test]
fn empty_or_blank_authoritative_root_set_fails_closed() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");

    let mut empty = trust_configuration();
    empty.trusted_root_refs.clear();
    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &empty, 150),
        Err(WorkloadIdentityAdmissionError::EmptyTrustedRootSet)
    );

    let mut blank = trust_configuration();
    blank.trusted_root_refs = BTreeSet::from([" ".to_string()]);
    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &blank, 150),
        Err(WorkloadIdentityAdmissionError::BlankTrustedRootRef)
    );
}

#[test]
fn trust_domain_must_match_authoritative_configuration() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let mut configuration = trust_configuration();
    configuration.trust_domain = "other.example".to_string();

    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &configuration, 150),
        Err(WorkloadIdentityAdmissionError::TrustDomainMismatch)
    );
}

#[test]
fn expired_identity_is_rejected_even_when_root_is_trusted() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &trust_configuration(), 200),
        Err(WorkloadIdentityAdmissionError::IdentityNotCurrentlyApplicable)
    );
}

#[test]
fn development_identity_cannot_enter_attested_trust_admission() {
    let mut value = attested();
    value.credential_kind = WorkloadCredentialKind::Development;
    value.assurance = WorkloadIdentityAssurance::Development;
    value.evidence_basis = WorkloadIdentityEvidenceBasis::Unknown;
    let value = RuntimeWorkloadIdentity::new(value).expect("development identity");

    assert_eq!(
        value.validate_against_trust_configuration(&binding(), &trust_configuration(), 150),
        Err(WorkloadIdentityAdmissionError::IdentityNotAttested)
    );
}

#[test]
fn execution_bound_runtime_mismatch_rejects_identity_evidence() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let mut execution = execution_identity();
    execution.runtime_id = "runtime-b".to_string();

    assert_eq!(
        value.validate_for_execution_runtime(&execution, &trust_configuration(), 150),
        Err(WorkloadIdentityAdmissionError::RuntimeBindingMismatch)
    );
}

#[test]
fn invalid_execution_binding_cannot_be_used_for_identity_admission() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let mut execution = execution_identity();
    execution.lease_generation = 0;

    assert_eq!(
        value.validate_for_execution_runtime(&execution, &trust_configuration(), 150),
        Err(WorkloadIdentityAdmissionError::InvalidExecutionIdentity)
    );
}

#[test]
fn matching_evidence_is_applicable_to_attested_execution_identity() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    assert_eq!(
        value.validate_evidence_applicability(
            &execution_identity(),
            &trust_configuration(),
            &evidence(),
            150,
        ),
        Ok(())
    );
}

#[test]
fn evidence_mission_execution_or_runtime_mismatch_fails_closed() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");

    let mut wrong_mission = evidence();
    wrong_mission.mission_id = MissionId::new("mission-2").expect("mission id");
    assert_eq!(
        value.validate_evidence_applicability(
            &execution_identity(),
            &trust_configuration(),
            &wrong_mission,
            150,
        ),
        Err(WorkloadIdentityAdmissionError::EvidenceBindingMismatch)
    );

    let mut wrong_execution = evidence();
    wrong_execution.execution_id = ExecutionId::new("exec-2").expect("execution id");
    assert_eq!(
        value.validate_evidence_applicability(
            &execution_identity(),
            &trust_configuration(),
            &wrong_execution,
            150,
        ),
        Err(WorkloadIdentityAdmissionError::EvidenceBindingMismatch)
    );

    let mut wrong_runtime = evidence();
    wrong_runtime.orchestrator_id = RuntimeId::new("runtime-b").expect("runtime id");
    assert_eq!(
        value.validate_evidence_applicability(
            &execution_identity(),
            &trust_configuration(),
            &wrong_runtime,
            150,
        ),
        Err(WorkloadIdentityAdmissionError::EvidenceBindingMismatch)
    );
}

#[test]
fn verification_context_remains_separate_from_workload_identity_binding() {
    let value = RuntimeWorkloadIdentity::new(attested()).expect("valid identity");
    let mut evidence = evidence();
    evidence.verification_context_id = "verify-context-b".to_string();

    assert_eq!(
        value.validate_evidence_applicability(
            &execution_identity(),
            &trust_configuration(),
            &evidence,
            150,
        ),
        Ok(())
    );
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
