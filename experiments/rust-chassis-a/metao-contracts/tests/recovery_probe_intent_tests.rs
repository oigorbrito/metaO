use metao_contracts::runtime_health::{
    bind_recovery_probe_intent, RecoveryProbeIntentAuthority, RecoveryProbeIntentClaim,
    RecoveryProbeIntentError,
};
use metao_contracts::{ExecutionId, MissionId};

fn authority() -> RecoveryProbeIntentAuthority {
    RecoveryProbeIntentAuthority {
        intent_id: "probe-intent-477".into(),
        mission_id: MissionId::new("m477").unwrap(),
        execution_id: ExecutionId::new("probe-exec-477").unwrap(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.0.0".into(),
        config_id: "config-a".into(),
        authority_generation: 7,
        fencing_token: 77,
        evidence_ref: "authority://probe-intent/477".into(),
    }
}
fn claim() -> RecoveryProbeIntentClaim {
    let a = authority();
    RecoveryProbeIntentClaim {
        intent_id: a.intent_id,
        mission_id: a.mission_id,
        execution_id: a.execution_id,
        runtime_id: a.runtime_id,
        runtime_version: a.runtime_version,
        config_id: a.config_id,
        authority_generation: a.authority_generation,
        fencing_token: a.fencing_token,
    }
}

#[test]
fn exact_canonical_intent_binds_probe_target() {
    let b = bind_recovery_probe_intent(&claim(), &authority(), 7, 77).unwrap();
    assert_eq!(b.runtime_id, "runtime-a");
    assert_eq!(b.execution_id.as_str(), "probe-exec-477");
}
#[test]
fn caller_only_target_mutation_is_rejected() {
    let mut c = claim();
    c.runtime_version = "2.0.0".into();
    assert_eq!(
        bind_recovery_probe_intent(&c, &authority(), 7, 77),
        Err(RecoveryProbeIntentError::BindingMismatch)
    );
}
#[test]
fn stale_generation_cannot_reuse_probe_intent() {
    assert_eq!(
        bind_recovery_probe_intent(&claim(), &authority(), 8, 77),
        Err(RecoveryProbeIntentError::StaleAuthority)
    );
}
#[test]
fn stale_fence_cannot_reuse_probe_intent() {
    assert_eq!(
        bind_recovery_probe_intent(&claim(), &authority(), 7, 78),
        Err(RecoveryProbeIntentError::StaleAuthority)
    );
}
#[test]
fn wrong_execution_cannot_relabel_ordinary_execution_as_probe() {
    let mut c = claim();
    c.execution_id = ExecutionId::new("ordinary-exec").unwrap();
    assert_eq!(
        bind_recovery_probe_intent(&c, &authority(), 7, 77),
        Err(RecoveryProbeIntentError::BindingMismatch)
    );
}
#[test]
fn blank_authority_evidence_fails_closed() {
    let mut a = authority();
    a.evidence_ref = "  ".into();
    assert_eq!(
        bind_recovery_probe_intent(&claim(), &a, 7, 77),
        Err(RecoveryProbeIntentError::InvalidAuthority)
    );
}
#[test]
fn bound_intent_contains_no_dispatch_or_acceptance_authority() {
    let b = bind_recovery_probe_intent(&claim(), &authority(), 7, 77).unwrap();
    let s = serde_json::to_string(&b).unwrap();
    for forbidden in ["dispatch", "AcceptanceDecision", "retry_eligible"] {
        assert!(!s.contains(forbidden));
    }
}
