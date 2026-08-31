use metao_contracts::{AcceptanceBudget, ContractError};

#[test]
fn non_finite_limits_and_initial_usage_fail_closed() {
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        assert_eq!(AcceptanceBudget::new(value, 1, 1.0, 1), Err(ContractError::NegativeBudget));
        assert_eq!(AcceptanceBudget::new(1.0, 1, value, 1), Err(ContractError::NegativeBudget));
        assert_eq!(AcceptanceBudget::with_usage((10.0, 10, 10.0, 10), (value, 0, 0.0, 0)), Err(ContractError::NegativeBudget));
        assert_eq!(AcceptanceBudget::with_usage((10.0, 10, 10.0, 10), (0.0, 0, value, 0)), Err(ContractError::NegativeBudget));
    }
}

#[test]
fn non_finite_applied_usage_fails_closed_without_mutating_source_budget() {
    let original = AcceptanceBudget::new(10.0, 10, 10.0, 10).expect("valid budget");
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        assert_eq!(original.clone().apply_usage(value, 0, 0.0, 0), Err(ContractError::NegativeBudget));
        assert_eq!(original.clone().apply_usage(0.0, 0, value, 0), Err(ContractError::NegativeBudget));
    }
    assert_eq!(original.money_used, 0.0);
    assert_eq!(original.tokens_used, 0);
    assert_eq!(original.wall_time_used_s, 0.0);
    assert_eq!(original.verifier_attempts_used, 0);
}

#[test]
fn token_checked_add_overflow_is_budget_exhausted_not_wrap_or_panic() {
    let original = AcceptanceBudget::with_usage((0.0, u64::MAX, 0.0, 0), (0.0, u64::MAX, 0.0, 0)).expect("u64::MAX token state is valid at its exact limit");
    assert_eq!(original.clone().apply_usage(0.0, 1, 0.0, 0), Err(ContractError::BudgetExhausted));
    assert_eq!(original.tokens_used, u64::MAX);
    assert_eq!(original.token_limit, u64::MAX);
}

#[test]
fn verifier_attempt_checked_add_overflow_is_budget_exhausted_not_wrap_or_panic() {
    let original = AcceptanceBudget::with_usage((0.0, 0, 0.0, u64::MAX), (0.0, 0, 0.0, u64::MAX)).expect("u64::MAX attempt state is valid at its exact limit");
    assert_eq!(original.clone().apply_usage(0.0, 0, 0.0, 1), Err(ContractError::BudgetExhausted));
    assert_eq!(original.verifier_attempts_used, u64::MAX);
    assert_eq!(original.verifier_attempt_limit, u64::MAX);
}

#[test]
fn exact_u64_max_boundary_can_be_consumed_from_zero() {
    let token_budget = AcceptanceBudget::new(0.0, u64::MAX, 0.0, 0).expect("valid token budget").apply_usage(0.0, u64::MAX, 0.0, 0).expect("exact token limit must remain valid");
    assert_eq!(token_budget.tokens_used, u64::MAX);
    let attempt_budget = AcceptanceBudget::new(0.0, 0, 0.0, u64::MAX).expect("valid attempt budget").apply_usage(0.0, 0, 0.0, u64::MAX).expect("exact attempt limit must remain valid");
    assert_eq!(attempt_budget.verifier_attempts_used, u64::MAX);
}

#[test]
fn exact_finite_boundary_passes_and_one_over_fails() {
    let exact = AcceptanceBudget::new(10.0, 0, 20.0, 0).expect("valid budget").apply_usage(10.0, 0, 20.0, 0).expect("exact finite boundary must pass");
    assert_eq!(exact.money_used, 10.0);
    assert_eq!(exact.wall_time_used_s, 20.0);
    assert_eq!(AcceptanceBudget::new(10.0, 0, 20.0, 0).expect("valid budget").apply_usage(10.000_001, 0, 0.0, 0), Err(ContractError::BudgetExhausted));
    assert_eq!(AcceptanceBudget::new(10.0, 0, 20.0, 0).expect("valid budget").apply_usage(0.0, 0, 20.000_001, 0), Err(ContractError::BudgetExhausted));
}

#[test]
fn finite_accumulation_overflow_fails_as_budget_exhausted() {
    let near_max = f64::MAX;
    let original = AcceptanceBudget::with_usage((f64::MAX, 0, f64::MAX, 0), (f64::MAX, 0, f64::MAX, 0)).expect("finite maximum state is structurally valid");
    assert_eq!(original.clone().apply_usage(near_max, 0, 0.0, 0), Err(ContractError::BudgetExhausted));
    assert_eq!(original.clone().apply_usage(0.0, 0, near_max, 0), Err(ContractError::BudgetExhausted));
    assert!(original.money_used.is_finite());
    assert!(original.wall_time_used_s.is_finite());
}
