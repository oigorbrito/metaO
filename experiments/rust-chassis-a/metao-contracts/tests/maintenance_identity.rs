use metao_contracts::{AttemptId, ContractError};

#[test]
fn attempt_id_validates_and_round_trips() {
    let original = AttemptId::new("attempt-1").expect("valid attempt identity");
    let round_trip = AttemptId::new(original.as_str().to_owned()).expect("round trip identity");
    assert_eq!(original, round_trip);
    assert_eq!(round_trip.as_str(), "attempt-1");
}

#[test]
fn attempt_id_rejects_empty_identity() {
    assert_eq!(
        AttemptId::new("   "),
        Err(ContractError::EmptyIdentity("attempt_id"))
    );
}
