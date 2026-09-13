use metao_contracts::execution_lease::{
    bind_execution_runtime_identity, ExecutionLease, ExecutionRuntimeBindingBasis,
    ExecutionRuntimeBindingClaim, ExecutionRuntimeBindingError, ExecutionRuntimeBindingProducer,
    LeaseAssurance, LeaseEvidenceBasis, LeaseState,
};

fn lease() -> ExecutionLease {
    ExecutionLease {
        mission_id: "mission-480".into(),
        logical_execution_key: "logical-480".into(),
        execution_id: "execution-480".into(),
        holder_identity: "worker-a".into(),
        generation: 7,
        fencing_token: 11,
        acquired_at_epoch: 100,
        renewed_at_epoch: 110,
        expires_at_epoch: 200,
        state: LeaseState::Active,
        assurance: LeaseAssurance::AuthoritativeStore,
        evidence_basis: LeaseEvidenceBasis::AuthoritativeStoreRead,
        evidence_ref: Some("lease://480/7/11".into()),
    }
}

fn producer() -> ExecutionRuntimeBindingProducer {
    ExecutionRuntimeBindingProducer {
        producer_id: "dispatch-authority-480".into(),
        mission_id: "mission-480".into(),
        logical_execution_key: "logical-480".into(),
        execution_id: "execution-480".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.2.3".into(),
        config_id: "config-a".into(),
        lease_generation: 7,
        fencing_token: 11,
        basis: ExecutionRuntimeBindingBasis::CanonicalDispatch,
        evidence_ref: "dispatch://480/runtime-a".into(),
    }
}

fn claim() -> ExecutionRuntimeBindingClaim {
    ExecutionRuntimeBindingClaim {
        mission_id: "mission-480".into(),
        logical_execution_key: "logical-480".into(),
        execution_id: "execution-480".into(),
        runtime_id: "runtime-a".into(),
        runtime_version: "1.2.3".into(),
        config_id: "config-a".into(),
        lease_generation: 7,
        fencing_token: 11,
    }
}

#[test]
fn canonical_dispatch_producer_binds_exact_runtime_identity() {
    let bound = bind_execution_runtime_identity(&claim(), &producer(), &lease()).unwrap();
    assert_eq!(bound.runtime_id, "runtime-a");
    assert_eq!(bound.runtime_version, "1.2.3");
    assert_eq!(bound.config_id, "config-a");
    assert_eq!(bound.lease_generation, 7);
    assert_eq!(bound.fencing_token, 11);
}

#[test]
fn copied_ids_with_noncanonical_basis_are_not_authority() {
    let mut forged = producer();
    forged.basis = ExecutionRuntimeBindingBasis::AdapterVerified;
    assert_eq!(
        bind_execution_runtime_identity(&claim(), &forged, &lease()),
        Err(ExecutionRuntimeBindingError::InvalidProducer)
    );
}

#[test]
fn runtime_version_or_config_drift_fails_closed() {
    for mutate in [0, 1, 2] {
        let mut forged = claim();
        match mutate {
            0 => forged.runtime_id = "runtime-b".into(),
            1 => forged.runtime_version = "9.9.9".into(),
            _ => forged.config_id = "config-b".into(),
        }
        assert_eq!(
            bind_execution_runtime_identity(&forged, &producer(), &lease()),
            Err(ExecutionRuntimeBindingError::ClaimBindingMismatch)
        );
    }
}

#[test]
fn stale_binding_after_takeover_is_rejected_even_when_ids_match() {
    let mut current = lease();
    current.generation = 8;
    current.fencing_token = 12;
    assert_eq!(
        bind_execution_runtime_identity(&claim(), &producer(), &current),
        Err(ExecutionRuntimeBindingError::StaleGenerationOrFence)
    );
}

#[test]
fn bound_identity_contains_no_health_retry_dispatch_or_acceptance_decision() {
    let bound = bind_execution_runtime_identity(&claim(), &producer(), &lease()).unwrap();
    let encoded = serde_json::to_string(&bound).unwrap();
    for forbidden in ["health_state", "next_attempt", "dispatch_authorized", "AcceptanceDecision"] {
        assert!(!encoded.contains(forbidden));
    }
}
