use metao_contracts::{
    AcceptanceContext, AcceptanceDecision, AuthoritativeAuthorityDecision,
    AuthoritativePolicyBundle, AuthoritativeSubjectState, AuthorityRegistryPort, EvidenceEnvelope,
    MissionId, PolicyDecision, PolicyEffect, PolicyRegistryPort, RuntimeId, SubjectStatePort,
    TerminalClaims,
};
use metao_kernel::{
    canonical_acceptance, resolve_authoritative_terminal_sources, TerminalSourceDecision,
};

fn evidence(
    created_at_epoch: f64,
    subject_state_id: &str,
    authority_id: &str,
    policy_bundle_id: &str,
    policy_root: &str,
) -> EvidenceEnvelope {
    EvidenceEnvelope {
        evidence_id: "evidence-1".into(),
        obligation_id: "obligation-1".into(),
        mission_id: MissionId::new("mission-1").unwrap(),
        execution_id: metao_contracts::ExecutionId::new("execution-1").unwrap(),
        orchestrator_id: RuntimeId::new("runtime-1").unwrap(),
        adapter_version: "adapter-1".into(),
        attempt_id: "attempt-1".into(),
        subject_id: "subject-1".into(),
        subject_state_id: subject_state_id.into(),
        verification_context_id: "verification-1".into(),
        policy_bundle_id: policy_bundle_id.into(),
        verifier_id: "verifier-1".into(),
        payload_digest: "payload-digest-1".into(),
        provenance_root: policy_root.into(),
        authority_id: authority_id.into(),
        passed: true,
        created_at_epoch,
        expires_at_epoch: Some(created_at_epoch + 10.0),
        approval_id: None,
        confidence: None,
    }
}

fn context(policy_bundle_id: &str) -> AcceptanceContext {
    AcceptanceContext {
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        verification_context_id: "verification-1".into(),
        policy_bundle_id: policy_bundle_id.into(),
        required_obligations: vec!["obligation-1".into()],
        trusted_verifiers: vec!["verifier-1".into()],
        trusted_provenance_roots: vec!["prov-root-1".into()],
        authorized_authorities: vec!["authority-1".into()],
    }
}

fn claims(policy_bundle_root: &str) -> TerminalClaims {
    TerminalClaims {
        subject_id: "subject-1".into(),
        subject_state_id: "state-1".into(),
        authority_context_id: "authority-context-1".into(),
        authority_id: "authority-1".into(),
        policy_bundle_id: "policy-1".into(),
        policy_bundle_root: policy_bundle_root.into(),
    }
}

#[derive(Clone)]
struct SubjectPort {
    current: Option<AuthoritativeSubjectState>,
}

impl SubjectStatePort for SubjectPort {
    fn current(&self, subject_id: &str) -> Option<AuthoritativeSubjectState> {
        self.current
            .clone()
            .filter(|state| state.subject_id == subject_id)
    }
}

#[derive(Clone)]
struct AuthorityPort {
    current: Option<AuthoritativeAuthorityDecision>,
}

impl AuthorityRegistryPort for AuthorityPort {
    fn resolve(
        &self,
        authority_context_id: &str,
        _request: &TerminalClaims,
    ) -> Option<AuthoritativeAuthorityDecision> {
        self.current
            .clone()
            .filter(|decision| decision.authority_context_id == authority_context_id)
    }
}

#[derive(Clone)]
struct PolicyPort {
    current: Option<AuthoritativePolicyBundle>,
}

impl PolicyRegistryPort for PolicyPort {
    fn get(&self, policy_bundle_id: &str) -> Option<AuthoritativePolicyBundle> {
        self.current
            .clone()
            .filter(|bundle| bundle.policy_bundle_id == policy_bundle_id)
    }
}

fn exact_subject_port(epoch: i64) -> SubjectPort {
    SubjectPort {
        current: Some(AuthoritativeSubjectState {
            subject_id: "subject-1".into(),
            subject_state_id: "state-1".into(),
            state_epoch: epoch,
        }),
    }
}

fn exact_authority_port(epoch: i64, evidence_root: &str, authority_id: &str) -> AuthorityPort {
    AuthorityPort {
        current: Some(AuthoritativeAuthorityDecision {
            authority_context_id: "authority-context-1".into(),
            authority_id: authority_id.into(),
            authority_epoch: epoch,
            capability_id: Some("capability-1".into()),
            reason: "ok".into(),
            evidence_root: evidence_root.into(),
        }),
    }
}

fn exact_policy_port(epoch: i64, policy_bundle_root: &str, effect: PolicyEffect) -> PolicyPort {
    PolicyPort {
        current: Some(AuthoritativePolicyBundle {
            policy_bundle_id: "policy-1".into(),
            policy_bundle_root: policy_bundle_root.into(),
            bundle_epoch: epoch,
            decision: PolicyDecision {
                effect,
                policy_bundle_id: "policy-1".into(),
                reason: String::new(),
            },
        }),
    }
}

#[test]
fn exact_authoritative_match_continues() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let claims = claims("prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims,
        std::slice::from_ref(&evidence),
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Continue);
    assert_eq!(
        canonical_acceptance(&context("policy-1"), &[evidence], 10.0).decision,
        AcceptanceDecision::Accept
    );
}

#[test]
fn caller_subject_state_cannot_override_authoritative_state() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let claims = claims("prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims,
        &[evidence],
        &SubjectPort {
            current: Some(AuthoritativeSubjectState {
                subject_id: "subject-1".into(),
                subject_state_id: "state-2".into(),
                state_epoch: 20,
            }),
        },
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Stale);
    assert!(assessment
        .reasons
        .contains(&"subject_state_mismatch".into()));
}

#[test]
fn caller_authority_cannot_override_registry() {
    let evidence = evidence(
        10.0,
        "state-1",
        "authority-claimed",
        "policy-1",
        "prov-root-1",
    );
    let claims = TerminalClaims {
        authority_id: "authority-claimed".into(),
        ..claims("prov-root-1")
    };
    let assessment = resolve_authoritative_terminal_sources(
        &claims,
        &[evidence],
        &exact_subject_port(10),
        &AuthorityPort {
            current: Some(AuthoritativeAuthorityDecision {
                authority_context_id: "authority-context-1".into(),
                authority_id: "authority-real".into(),
                authority_epoch: 5,
                capability_id: Some("capability-1".into()),
                reason: "ok".into(),
                evidence_root: "prov-root-1".into(),
            }),
        },
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment.reasons.contains(&"authority_mismatch".into()));
}

#[test]
fn caller_policy_root_cannot_override_registry() {
    let evidence = evidence(
        10.0,
        "state-1",
        "authority-1",
        "policy-1",
        "prov-root-claimed",
    );
    let claims = claims("prov-root-claimed");
    let assessment = resolve_authoritative_terminal_sources(
        &claims,
        &[evidence],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-claimed", "authority-1"),
        &PolicyPort {
            current: Some(AuthoritativePolicyBundle {
                policy_bundle_id: "policy-1".into(),
                policy_bundle_root: "prov-root-real".into(),
                bundle_epoch: 5,
                decision: PolicyDecision {
                    effect: PolicyEffect::Allow,
                    policy_bundle_id: "policy-1".into(),
                    reason: String::new(),
                },
            }),
        },
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment
        .reasons
        .contains(&"policy_bundle_mismatch".into()));
}

#[test]
fn legitimate_forward_subject_mutation_is_stale() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence],
        &SubjectPort {
            current: Some(AuthoritativeSubjectState {
                subject_id: "subject-1".into(),
                subject_state_id: "state-2".into(),
                state_epoch: 20,
            }),
        },
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Stale);
}

#[test]
fn legitimate_forward_policy_mutation_is_stale() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &PolicyPort {
            current: Some(AuthoritativePolicyBundle {
                policy_bundle_id: "policy-1".into(),
                policy_bundle_root: "prov-root-2".into(),
                bundle_epoch: 20,
                decision: PolicyDecision {
                    effect: PolicyEffect::Allow,
                    policy_bundle_id: "policy-1".into(),
                    reason: String::new(),
                },
            }),
        },
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Stale);
}

#[test]
fn rollback_regression_is_blocked() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence],
        &SubjectPort {
            current: Some(AuthoritativeSubjectState {
                subject_id: "subject-1".into(),
                subject_state_id: "state-0".into(),
                state_epoch: 5,
            }),
        },
        &exact_authority_port(5, "prov-root-1", "authority-1"),
        &exact_policy_port(5, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
}

#[test]
fn fabricated_policy_root_is_blocked() {
    let evidence = evidence(
        10.0,
        "state-1",
        "authority-1",
        "policy-1",
        "prov-root-fabricated",
    );
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-fabricated"),
        &[evidence],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-fabricated", "authority-1"),
        &PolicyPort {
            current: Some(AuthoritativePolicyBundle {
                policy_bundle_id: "policy-1".into(),
                policy_bundle_root: "prov-root-real".into(),
                bundle_epoch: 5,
                decision: PolicyDecision {
                    effect: PolicyEffect::Allow,
                    policy_bundle_id: "policy-1".into(),
                    reason: String::new(),
                },
            }),
        },
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
}

#[test]
fn integrity_mismatch_is_blocked() {
    let evidence = evidence(10.0, "state-1", "authority-1", "policy-1", "prov-root-1");
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[EvidenceEnvelope {
            payload_digest: "other-digest".into(),
            ..evidence
        }],
        &exact_subject_port(10),
        &exact_authority_port(5, "prov-root-1", "authority-2"),
        &exact_policy_port(5, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
}

#[test]
fn missing_subject_source_fails_closed() {
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence(
            10.0,
            "state-1",
            "authority-1",
            "policy-1",
            "prov-root-1",
        )],
        &SubjectPort { current: None },
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment
        .reasons
        .contains(&"missing_subject_source".into()));
}

#[test]
fn missing_authority_source_fails_closed() {
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence(
            10.0,
            "state-1",
            "authority-1",
            "policy-1",
            "prov-root-1",
        )],
        &exact_subject_port(10),
        &AuthorityPort { current: None },
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment
        .reasons
        .contains(&"missing_authority_source".into()));
}

#[test]
fn missing_policy_source_fails_closed() {
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence(
            10.0,
            "state-1",
            "authority-1",
            "policy-1",
            "prov-root-1",
        )],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &PolicyPort { current: None },
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment.reasons.contains(&"missing_policy_source".into()));
}

#[test]
fn authoritative_hard_deny_cannot_be_overridden() {
    let assessment = resolve_authoritative_terminal_sources(
        &claims("prov-root-1"),
        &[evidence(
            10.0,
            "state-1",
            "authority-1",
            "policy-1",
            "prov-root-1",
        )],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-1", "authority-1"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Deny),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment
        .reasons
        .contains(&"authoritative_policy_deny".into()));
}

#[test]
fn runtime_verifier_self_report_cannot_mint_authority() {
    let assessment = resolve_authoritative_terminal_sources(
        &TerminalClaims {
            authority_id: "authority-self-report".into(),
            ..claims("prov-root-1")
        },
        &[evidence(
            10.0,
            "state-1",
            "authority-self-report",
            "policy-1",
            "prov-root-1",
        )],
        &exact_subject_port(10),
        &exact_authority_port(10, "prov-root-1", "authority-real"),
        &exact_policy_port(10, "prov-root-1", PolicyEffect::Allow),
    );
    assert_eq!(assessment.decision, TerminalSourceDecision::Block);
    assert!(assessment.reasons.contains(&"authority_mismatch".into()));
}
