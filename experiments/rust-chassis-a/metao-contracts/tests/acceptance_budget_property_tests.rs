use metao_contracts::{AcceptanceBudget, ContractError};
use proptest::prelude::*;

fn replay(
    mut budget: AcceptanceBudget,
    operations: &[(u8, u16, u8, u8)],
) -> Result<AcceptanceBudget, ContractError> {
    for (money, tokens, wall_time, attempts) in operations {
        budget = budget.apply_usage(
            f64::from(*money),
            u64::from(*tokens),
            f64::from(*wall_time),
            u64::from(*attempts),
        )?;
    }
    Ok(budget)
}

proptest! {
    #[test]
    fn successful_usage_preserves_limits_and_is_monotonic(
        money_limit in 1u16..1000,
        token_limit in 1u16..10_000,
        wall_time_limit in 1u16..1000,
        attempt_limit in 1u16..100,
        seed_money_used in any::<u16>(),
        seed_tokens_used in any::<u16>(),
        seed_wall_used in any::<u16>(),
        seed_attempts_used in any::<u16>(),
        seed_money_delta in any::<u16>(),
        seed_tokens_delta in any::<u16>(),
        seed_wall_delta in any::<u16>(),
        seed_attempts_delta in any::<u16>(),
    ) {
        let money_used = seed_money_used % (money_limit + 1);
        let tokens_used = seed_tokens_used % (token_limit + 1);
        let wall_used = seed_wall_used % (wall_time_limit + 1);
        let attempts_used = seed_attempts_used % (attempt_limit + 1);

        let money_remaining = money_limit - money_used;
        let tokens_remaining = token_limit - tokens_used;
        let wall_remaining = wall_time_limit - wall_used;
        let attempts_remaining = attempt_limit - attempts_used;

        let money_delta = seed_money_delta % (money_remaining + 1);
        let tokens_delta = seed_tokens_delta % (tokens_remaining + 1);
        let wall_delta = seed_wall_delta % (wall_remaining + 1);
        let attempts_delta = seed_attempts_delta % (attempts_remaining + 1);

        let before = AcceptanceBudget::with_usage(
            (
                f64::from(money_limit),
                u64::from(token_limit),
                f64::from(wall_time_limit),
                u64::from(attempt_limit),
            ),
            (
                f64::from(money_used),
                u64::from(tokens_used),
                f64::from(wall_used),
                u64::from(attempts_used),
            ),
        )
        .expect("generated initial budget is within limits");

        let after = before
            .clone()
            .apply_usage(
                f64::from(money_delta),
                u64::from(tokens_delta),
                f64::from(wall_delta),
                u64::from(attempts_delta),
            )
            .expect("generated delta is within remaining budget");

        prop_assert_eq!(after.money_limit, before.money_limit);
        prop_assert_eq!(after.token_limit, before.token_limit);
        prop_assert_eq!(after.wall_time_limit_s, before.wall_time_limit_s);
        prop_assert_eq!(after.verifier_attempt_limit, before.verifier_attempt_limit);

        prop_assert!(after.money_used >= before.money_used);
        prop_assert!(after.tokens_used >= before.tokens_used);
        prop_assert!(after.wall_time_used_s >= before.wall_time_used_s);
        prop_assert!(after.verifier_attempts_used >= before.verifier_attempts_used);
    }

    #[test]
    fn exceeding_any_generated_dimension_fails_closed(
        money_limit in 0u16..1000,
        token_limit in 0u16..10_000,
        wall_time_limit in 0u16..1000,
        attempt_limit in 0u16..100,
        dimension in 0u8..4,
    ) {
        let budget = AcceptanceBudget::new(
            f64::from(money_limit),
            u64::from(token_limit),
            f64::from(wall_time_limit),
            u64::from(attempt_limit),
        )
        .expect("generated limits are valid");

        let result = match dimension {
            0 => budget.apply_usage(f64::from(money_limit) + 1.0, 0, 0.0, 0),
            1 => budget.apply_usage(0.0, u64::from(token_limit) + 1, 0.0, 0),
            2 => budget.apply_usage(0.0, 0, f64::from(wall_time_limit) + 1.0, 0),
            _ => budget.apply_usage(0.0, 0, 0.0, u64::from(attempt_limit) + 1),
        };

        prop_assert_eq!(result, Err(ContractError::BudgetExhausted));
    }

    #[test]
    fn replaying_the_same_generated_sequence_is_deterministic(
        operations in prop::collection::vec((0u8..20, 0u16..200, 0u8..20, 0u8..4), 0..64),
    ) {
        let initial = AcceptanceBudget::new(250.0, 2_500, 250.0, 64)
            .expect("fixed property-test budget is valid");

        let left = replay(initial.clone(), &operations);
        let right = replay(initial, &operations);

        prop_assert_eq!(left, right);
    }
}
