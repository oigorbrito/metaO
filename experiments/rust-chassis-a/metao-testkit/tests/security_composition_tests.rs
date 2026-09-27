use metao_contracts::credential_lease::{
    CredentialLease, CredentialLeaseAssurance, CredentialLeaseBinding,
    CredentialLeaseEvidenceBasis, CredentialRevocationStatus,
};
use metao_contracts::runtime_certification::{
    CertificationCategoryResult, CertificationCategoryStatus, RuntimeCertificationBinding,
    RuntimeCertificationDecision, RuntimeCertificationEvidenceBasis, RuntimeCertificationReport,
};
use metao_contracts::runtime_security::{
    evaluate_runtime_security, IsolationAssurance, RuntimeSecurityAdmission,
    RuntimeSecurityBinding, RuntimeSecurityEvidenceBasis, RuntimeSecurityFacts,
    RuntimeSecurityProfile,
};
use metao_contracts::workload_identity::{
    RuntimeIdentityBinding, RuntimeWorkloadIdentity, WorkloadCredentialKind,
    WorkloadIdentityAssurance, WorkloadIdentityEvidenceBasis,
};
use std::collections::BTreeSet;

fn identity_binding() -> RuntimeIdentityBinding {
    RuntimeIdentityBinding {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "config-a".into(),
    }
}

fn security_binding() -> RuntimeSecurityBinding {
    RuntimeSecurityBinding {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "config-a".into(),
    }
}

fn lease_binding() -> CredentialLeaseBinding {
    CredentialLeaseBinding {
        runtime_id: "runtime-a".into(),
        workload_identity: "spiffe://example.org/runtime-a".into(),
        runtime_config_id: "config-a".into(),
        mission_id: "mission-1".into(),
        execution_id: "exec-1".into(),
    }
}

fn certification_binding() -> RuntimeCertificationBinding {
    RuntimeCertificationBinding {
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0".into(),
        config_id: "config-a".into(),
        execution_context_id: "exec-ctx-1".into(),
        verification_context_id: "verify-ctx-1".into(),
    }
}

#[test]
fn security_composition_enforces_identity_lease_and_certification_boundaries() {
    let development_identity = RuntimeWorkloadIdentity::new(RuntimeWorkloadIdentity {
        binding: identity_binding(),
        workload_subject: "runtime-a".into(),
        trust_domain: "example.org".into(),
        credential_kind: WorkloadCredentialKind::Development,
        assurance: WorkloadIdentityAssurance::Development,
        evidence_basis: WorkloadIdentityEvidenceBasis::SelfReported,
        trust_root_ref: None,
        credential_ref: None,
        verifier_provenance: None,
        issued_at_epoch: None,
        expires_at_epoch: None,
        verified_at_epoch: None,
    })
    .expect("development identity");
    assert_eq!(
        development_identity.assurance,
        WorkloadIdentityAssurance::Development
    );

    let attested_identity = RuntimeWorkloadIdentity::new(RuntimeWorkloadIdentity {
        binding: identity_binding(),
        workload_subject: "spiffe://example.org/runtime-a".into(),
        trust_domain: "example.org".into(),
        credential_kind: WorkloadCredentialKind::X509Svid,
        assurance: WorkloadIdentityAssurance::Attested,
        evidence_basis: WorkloadIdentityEvidenceBasis::IndependentVerifier,
        trust_root_ref: Some("trust-root-1".into()),
        credential_ref: Some("cred-1".into()),
        verifier_provenance: Some("verifier-1".into()),
        issued_at_epoch: Some(10),
        expires_at_epoch: Some(20),
        verified_at_epoch: Some(12),
    })
    .expect("attested identity");
    assert!(attested_identity.is_currently_applicable(15));
    assert!(!attested_identity.applies_to("runtime-b", "1.0", "config-a"));

    let facts = RuntimeSecurityFacts {
        binding: security_binding(),
        isolation: IsolationAssurance::Process,
        effective_permissions: BTreeSet::from(["read".into()]),
        secret_redaction_enforced: Some(true),
        untrusted_content_isolated_from_governance: Some(true),
        enforcement_capabilities: BTreeSet::from(["deny-by-default".into()]),
        evidence_basis: RuntimeSecurityEvidenceBasis::IndependentObservation,
        evidence_ref: "security-evidence-1".into(),
    };
    let profile = RuntimeSecurityProfile {
        minimum_isolation: IsolationAssurance::Process,
        allowed_permissions: BTreeSet::from(["read".into()]),
        require_secret_redaction: true,
        require_untrusted_content_isolation: true,
        required_capabilities: BTreeSet::from(["deny-by-default".into()]),
    };
    let projection = evaluate_runtime_security(&facts, &profile, &security_binding())
        .expect("security projection");
    assert_eq!(projection.admission, RuntimeSecurityAdmission::Satisfied);

    let rejected = evaluate_runtime_security(
        &RuntimeSecurityFacts {
            evidence_basis: RuntimeSecurityEvidenceBasis::SelfReported,
            secret_redaction_enforced: Some(false),
            untrusted_content_isolated_from_governance: Some(false),
            ..facts.clone()
        },
        &profile,
        &security_binding(),
    )
    .expect("security rejection");
    assert_eq!(rejected.admission, RuntimeSecurityAdmission::Rejected);
    assert!(rejected
        .reasons
        .iter()
        .any(|reason| reason.contains("independent or adapter-verified")));

    let lease = CredentialLease {
        lease_ref: "lease-1".into(),
        binding: lease_binding(),
        credential_class: "brokered-access-token".into(),
        target_service: "service-a".into(),
        policy_authority_ref: "policy-1".into(),
        issued_at_epoch: 10,
        expires_at_epoch: 20,
        renewable: true,
        max_expires_at_epoch: Some(30),
        assurance: CredentialLeaseAssurance::Brokered,
        evidence_basis: CredentialLeaseEvidenceBasis::BrokerVerified,
        revocation_status: CredentialRevocationStatus::Active,
        revocation_evidence_ref: None,
    };
    assert!(lease.applies_to(&lease_binding(), 15));
    assert!(!lease.applies_to(
        &CredentialLeaseBinding {
            runtime_id: "runtime-b".into(),
            ..lease_binding()
        },
        15
    ));

    let revoked = CredentialLease {
        revocation_status: CredentialRevocationStatus::Revoked,
        revocation_evidence_ref: Some("revocation-1".into()),
        ..lease.clone()
    };
    assert!(revoked.revocation_confirmed());

    let development_static = CredentialLease {
        assurance: CredentialLeaseAssurance::DevelopmentStatic,
        evidence_basis: CredentialLeaseEvidenceBasis::DevelopmentLocal,
        ..lease.clone()
    };
    assert!(development_static.applies_to(&lease_binding(), 15));
    assert_eq!(
        development_static.assurance,
        CredentialLeaseAssurance::DevelopmentStatic
    );

    let report = RuntimeCertificationReport {
        binding: certification_binding(),
        evaluator_id: "evaluator-1".into(),
        evaluator_version: "1.0".into(),
        evaluator_evidence_basis: RuntimeCertificationEvidenceBasis::IndependentEvaluator,
        evaluator_evidence_ref: "cert-evidence-1".into(),
        evaluated_at_epoch: 100,
        expires_at_epoch: Some(200),
        required_categories: BTreeSet::from(["safety".into(), "adversarial".into()]),
        category_results: vec![
            CertificationCategoryResult {
                category_id: "safety".into(),
                status: CertificationCategoryStatus::Pass,
                benign_utility_passed: Some(true),
                forbidden_action_observed: Some(false),
                evidence_ref: Some("safety-evidence".into()),
                reason: "safe".into(),
            },
            CertificationCategoryResult {
                category_id: "adversarial".into(),
                status: CertificationCategoryStatus::Fail,
                benign_utility_passed: Some(true),
                forbidden_action_observed: Some(true),
                evidence_ref: Some("adversarial-evidence".into()),
                reason: "adversarial failure".into(),
            },
        ],
    };
    let projection = report
        .project(&certification_binding(), 150)
        .expect("certification projection");
    assert_eq!(
        projection.decision,
        RuntimeCertificationDecision::NotCertified
    );
    assert!(projection.failed_categories.contains(&"adversarial".into()));

    let stale = report
        .project(
            &RuntimeCertificationBinding {
                runtime_version: "2.0".into(),
                ..certification_binding()
            },
            150,
        )
        .expect("stale certification projection");
    assert_eq!(stale.decision, RuntimeCertificationDecision::Stale);

    let encoded = serde_json::to_string(&serde_json::json!({
        "identity": attested_identity,
        "security": facts,
        "lease": lease,
    }))
    .expect("serialize security evidence");
    for forbidden in ["bearer", "password", "private key", "token_value"] {
        assert!(!encoded.contains(forbidden));
    }
}
