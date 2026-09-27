use metao_contracts::{AcceptanceBudget, ContractError};
use metao_kernel::AcceptanceBudgetAuthority;
use std::sync::{Arc, Barrier, Mutex};
use std::thread;

fn authority() -> AcceptanceBudgetAuthority {
    AcceptanceBudgetAuthority::new(
        AcceptanceBudget::new(10.0, 10_000, 60.0, 10).expect("valid budget"),
    )
}

#[test]
fn shared_budget_no_oversubscription() {
    let authority = Arc::new(authority());
    let barrier = Arc::new(Barrier::new(2));
    let accepted = Arc::new(Mutex::new(Vec::new()));
    let rejected = Arc::new(Mutex::new(Vec::new()));

    let handles: Vec<_> = ["r1", "r2"]
        .into_iter()
        .map(|reservation_id| {
            let authority = Arc::clone(&authority);
            let barrier = Arc::clone(&barrier);
            let accepted = Arc::clone(&accepted);
            let rejected = Arc::clone(&rejected);
            thread::spawn(move || {
                barrier.wait();
                match authority.reserve(reservation_id, 6.0, 0, 0.0, 0) {
                    Ok(_) => accepted.lock().unwrap().push(reservation_id.to_string()),
                    Err(ContractError::BudgetExhausted) => {
                        rejected.lock().unwrap().push(reservation_id.to_string())
                    }
                    other => panic!("unexpected reserve result: {other:?}"),
                }
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }

    assert_eq!(accepted.lock().unwrap().len(), 1);
    assert_eq!(rejected.lock().unwrap().len(), 1);
    assert_eq!(authority.snapshot().money_used, 0.0);
}

#[test]
fn exact_capacity_admission() {
    let authority = Arc::new(authority());
    let barrier = Arc::new(Barrier::new(2));
    let failures = Arc::new(Mutex::new(Vec::new()));

    let handles: Vec<_> = ["r1", "r2"]
        .into_iter()
        .map(|reservation_id| {
            let authority = Arc::clone(&authority);
            let barrier = Arc::clone(&barrier);
            let failures = Arc::clone(&failures);
            thread::spawn(move || {
                barrier.wait();
                if let Err(error) = authority.reserve(reservation_id, 5.0, 0, 0.0, 0) {
                    failures.lock().unwrap().push(error);
                }
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }

    assert!(failures.lock().unwrap().is_empty());
    assert_eq!(authority.reservation("r1").unwrap().money, 5.0);
    assert_eq!(authority.reservation("r2").unwrap().money, 5.0);
}

#[test]
fn failed_reservation_no_mutation() {
    let authority = authority();
    authority.reserve("winner", 8.0, 0, 0.0, 0).unwrap();

    assert_eq!(
        authority.reserve("loser", 3.0, 0, 0.0, 0),
        Err(ContractError::BudgetExhausted)
    );
    assert!(authority.reservation("loser").is_none());
    assert_eq!(authority.snapshot().money_used, 0.0);
    assert_eq!(authority.settle("winner").unwrap().money_used, 8.0);
}

#[test]
fn duplicate_reservation_replay_idempotent() {
    let authority = authority();
    let first = authority.reserve("reservation-1", 4.0, 10, 0.0, 0).unwrap();
    let retry = authority.reserve("reservation-1", 4.0, 10, 0.0, 0).unwrap();

    assert_eq!(first, retry);
    assert_eq!(authority.snapshot().money_used, 0.0);
}

#[test]
fn conflicting_reservation_replay_fails_closed() {
    let authority = authority();
    authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();

    assert_eq!(
        authority.reserve("reservation-1", 5.0, 0, 0.0, 0),
        Err(ContractError::ReplayConflict)
    );
    assert_eq!(authority.reservation("reservation-1").unwrap().money, 4.0);
}

#[test]
fn settlement_retry_idempotent() {
    let authority = authority();
    authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();

    let first = authority.settle("reservation-1").unwrap();
    let retry = authority.settle("reservation-1").unwrap();

    assert_eq!(first.money_used, 4.0);
    assert_eq!(retry.money_used, 4.0);
    assert!(authority.reservation("reservation-1").unwrap().settled);
}

#[test]
fn concurrent_same_settlement_single_effect() {
    let authority = Arc::new(authority());
    authority.reserve("reservation-1", 4.0, 0, 0.0, 0).unwrap();
    let barrier = Arc::new(Barrier::new(2));
    let results = Arc::new(Mutex::new(Vec::new()));

    let handles: Vec<_> = (0..2)
        .map(|_| {
            let authority = Arc::clone(&authority);
            let barrier = Arc::clone(&barrier);
            let results = Arc::clone(&results);
            thread::spawn(move || {
                barrier.wait();
                let snapshot = authority.settle("reservation-1").unwrap();
                results.lock().unwrap().push(snapshot.money_used);
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }

    assert_eq!(results.lock().unwrap().as_slice(), &[4.0, 4.0]);
    assert_eq!(authority.snapshot().money_used, 4.0);
}

#[test]
fn unknown_settlement_id_fails_closed() {
    let authority = authority();

    assert_eq!(
        authority.settle("missing-reservation"),
        Err(ContractError::UnknownReservation(
            "missing-reservation".into()
        ))
    );
    assert_eq!(authority.snapshot().money_used, 0.0);
}
