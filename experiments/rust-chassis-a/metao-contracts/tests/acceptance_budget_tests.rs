use metao_contracts::{AcceptanceBudget, ContractError};

#[test]
fn non_finite_limits_and_usage_fail_closed() {
    let cases = [
        (f64::NAN, 10.0, 0.0, 0.0),
        (f64::INFINITY, 10.0, 0.0, 0.0),
        (10.0, f64::NAN, 0.0, 0.0),
        (10.0, f64::INFINITY, 0.0, 0.0),
        (10.0, 10.0, f64::NAN, 0.0),
        (10.0, 10.0, f64::INFINITY, 0.0),
    ];

    for (money_limit, money_used, wall_time_limit_s, wall_time_used_s) in cases {
        let result = AcceptanceBudget::with_usage(
            (money_limit, 1, wall_time_limit_s, 1),
            (money_used, 0, wall_time_used_s, 0),
        );
        assert_eq!(result, Err(ContractError::NegativeBudget));
    }

    let result = AcceptanceBudget::with_usage((10.0, 1, 10.0, 1), (0.0, 0, f64::NAN, 0));
    assert_eq!(result, Err(ContractError::NegativeBudget));
}

#[test]
fn exact_limit_passes_and_one_over_fails() {
    let budget = AcceptanceBudget::new(10.0, 10, 5.0, 5).unwrap();
    let budget = budget.apply_usage(10.0, 10, 5.0, 5).unwrap();

    assert_eq!(budget.money_used, 10.0);
    assert_eq!(budget.tokens_used, 10);
    assert_eq!(budget.wall_time_used_s, 5.0);
    assert_eq!(budget.verifier_attempts_used, 5);

    let result = budget.apply_usage(0.0001, 0, 0.0, 0);
    assert_eq!(result, Err(ContractError::BudgetExhausted));
}

#[test]
fn overflow_in_usage_accumulation_fails_closed() {
    let budget = AcceptanceBudget::with_usage(
        (f64::MAX, u64::MAX, f64::MAX, u64::MAX),
        (f64::MAX, u64::MAX, f64::MAX, u64::MAX),
    )
    .unwrap();

    assert_eq!(
        budget.clone().apply_usage(f64::MAX, 0, 0.0, 0),
        Err(ContractError::BudgetExhausted)
    );
    assert_eq!(
        budget.clone().apply_usage(0.0, 1, 0.0, 0),
        Err(ContractError::BudgetExhausted)
    );
    assert_eq!(
        budget.clone().apply_usage(0.0, 0, f64::MAX, 0),
        Err(ContractError::BudgetExhausted)
    );
    assert_eq!(
        budget.apply_usage(0.0, 0, 0.0, 1),
        Err(ContractError::BudgetExhausted)
    );
}
