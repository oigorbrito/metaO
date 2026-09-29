use metao_contracts::runtime_certification::{
    RuntimeCertificationBinding, RuntimeCertificationEvidenceBinding,
};

fn certification(version: &str) -> RuntimeCertificationBinding {
    RuntimeCertificationBinding {
        runtime_id: "runtime-a".into(),
        runtime_version: version.into(),
        config_id: "cfg-a".into(),
        execution_context_id: "exec-context-1".into(),
        verification_context_id: "verify-context-1".into(),
    }
}

fn evidence_binding(version: &str) -> RuntimeCertificationEvidenceBinding {
    RuntimeCertificationEvidenceBinding {
        evidence_id: "evidence-1".into(),
        certification_ref: "runtime-a:1.2.3:probe-1:100.000000".into(),
        certification: certification(version),
    }
}

#[test]
fn exact_certification_identity_applies_to_evidence() {
    let binding = evidence_binding("1.2.3");
    assert!(binding.applies_to(
        "evidence-1",
        "runtime-a:1.2.3:probe-1:100.000000",
        &certification("1.2.3"),
    ));
}

#[test]
fn runtime_version_drift_invalidates_evidence_applicability() {
    let binding = evidence_binding("1.2.3");
    assert!(!binding.applies_to(
        "evidence-1",
        "runtime-a:1.2.3:probe-1:100.000000",
        &certification("1.2.4"),
    ));
}

#[test]
fn certification_generation_drift_invalidates_evidence_applicability() {
    let binding = evidence_binding("1.2.3");
    assert!(!binding.applies_to(
        "evidence-1",
        "runtime-a:1.2.3:probe-1:101.000000",
        &certification("1.2.3"),
    ));
}

#[test]
fn evidence_identity_drift_invalidates_certification_binding() {
    let binding = evidence_binding("1.2.3");
    assert!(!binding.applies_to(
        "evidence-2",
        "runtime-a:1.2.3:probe-1:100.000000",
        &certification("1.2.3"),
    ));
}

#[test]
fn certification_reference_is_not_authority_by_itself() {
    let binding = evidence_binding("1.2.3");
    assert!(!binding.applies_to(
        "evidence-1",
        "runtime-a:1.2.3:probe-1:100.000000",
        &certification("1.2.4"),
    ));
}
