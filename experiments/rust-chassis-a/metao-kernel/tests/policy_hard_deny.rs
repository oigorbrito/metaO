use metao_contracts::PolicyEffect;
use metao_kernel::evaluate_policy;

#[test]
fn deny_when_not_allowed() {
    let decision = evaluate_policy("pb-1", false, false, "");
    assert_eq!(decision.effect, PolicyEffect::Deny);
}

#[test]
fn deny_overrides_require_human() {
    let decision = evaluate_policy("pb-1", false, true, "");
    assert_eq!(decision.effect, PolicyEffect::Deny);
}

#[test]
fn require_human_when_allowed_and_required() {
    let decision = evaluate_policy("pb-1", true, true, "");
    assert_eq!(decision.effect, PolicyEffect::RequireHuman);
}

#[test]
fn allow_when_allowed_and_no_human_required() {
    let decision = evaluate_policy("pb-1", true, false, "");
    assert_eq!(decision.effect, PolicyEffect::Allow);
}

#[test]
fn default_reasons_are_preserved() {
    let deny = evaluate_policy("pb-1", false, false, "");
    assert_eq!(deny.reason, "policy_denied");

    let human = evaluate_policy("pb-1", true, true, "");
    assert_eq!(human.reason, "human_approval_required");

    let allow = evaluate_policy("pb-1", true, false, "");
    assert_eq!(allow.reason, "");
}

#[test]
fn explicit_reason_is_preserved() {
    let deny = evaluate_policy("pb-1", false, false, "blocked by policy");
    assert_eq!(deny.reason, "blocked by policy");

    let human = evaluate_policy("pb-1", true, true, "needs human");
    assert_eq!(human.reason, "needs human");

    let allow = evaluate_policy("pb-1", true, false, "policy note");
    assert_eq!(allow.reason, "policy note");
}

#[test]
fn policy_bundle_id_is_preserved() {
    let decision = evaluate_policy("bundle-42", true, false, "");
    assert_eq!(decision.policy_bundle_id, "bundle-42");
}
