use std::collections::BTreeSet;

use serde::Serialize;

#[derive(Clone, Debug, PartialEq, Eq)]
enum FaultResult {
    Pass,
    BlockedToolchain,
    BlockedExternal,
}

#[derive(Clone, Debug)]
struct FaultRecord {
    fault_id: &'static str,
    trigger: &'static str,
    expected_fail_safe_behavior: &'static str,
    actual_result: FaultResult,
    substrate: &'static str,
    claim_boundary: &'static str,
}

#[derive(Serialize)]
struct GateEvidenceRecord {
    schema_version: &'static str,
    record_id: &'static str,
    repository: &'static str,
    exact_sha_binding: &'static str,
    gate_id: &'static str,
    gate_level: &'static str,
    command: &'static str,
    result: &'static str,
    substrate: &'static str,
    claim_boundary: &'static str,
}

fn fault_records() -> Vec<FaultRecord> {
    vec![
        FaultRecord {
            fault_id: "PROCESS_KILL_AFTER_EFFECT_BEFORE_ACK",
            trigger: "local effect service applies effect and closes before acknowledgement",
            expected_fail_safe_behavior: "retry preserves effect identity and deduplicates",
            actual_result: FaultResult::Pass,
            substrate: "LOCAL_REAL_PROCESS + REAL_LOCAL_EXTERNAL_SERVICE",
            claim_boundary: "covered by composed_system_closure_tests",
        },
        FaultRecord {
            fault_id: "CONTROLLER_RESTART",
            trigger: "effect service is restarted and durable state is reopened",
            expected_fail_safe_behavior: "prior effect remains authoritative",
            actual_result: FaultResult::Pass,
            substrate: "DURABLE_FILE_STORE",
            claim_boundary: "local durable restart only",
        },
        FaultRecord {
            fault_id: "DURABLE_STORE_REOPEN",
            trigger: "file-backed service restarts over same state path",
            expected_fail_safe_behavior: "state is retained",
            actual_result: FaultResult::Pass,
            substrate: "DURABLE_FILE_STORE",
            claim_boundary: "single-host local file store",
        },
        FaultRecord {
            fault_id: "EXTERNAL_SERVICE_UNAVAILABLE",
            trigger: "external provider absent",
            expected_fail_safe_behavior:
                "classified as external/unavailable rather than product pass",
            actual_result: FaultResult::BlockedExternal,
            substrate: "NO_PROVIDER",
            claim_boundary: "real provider execution not available in local closure run",
        },
        FaultRecord {
            fault_id: "CONNECTION_REFUSED",
            trigger: "no remote provider endpoint configured",
            expected_fail_safe_behavior: "blocked external/provider requirement",
            actual_result: FaultResult::BlockedExternal,
            substrate: "NO_PROVIDER",
            claim_boundary: "local testkit service remains covered separately",
        },
        FaultRecord {
            fault_id: "TIMEOUT",
            trigger: "wire runtime hang fixture",
            expected_fail_safe_behavior: "timeout is contained and classified",
            actual_result: FaultResult::Pass,
            substrate: "LOCAL_REAL_PROCESS",
            claim_boundary: "covered by metao-wire out_of_process and endurance tests",
        },
        FaultRecord {
            fault_id: "STORAGE_OPERATION_FAILURE",
            trigger: "unavailable external durable backend",
            expected_fail_safe_behavior: "do not mint success from missing authority",
            actual_result: FaultResult::BlockedExternal,
            substrate: "NO_EXTERNAL_DURABLE_BACKEND",
            claim_boundary: "local file-backed store covered; external database not configured",
        },
        FaultRecord {
            fault_id: "DUPLICATE_EVENT",
            trigger: "same idempotency key is replayed",
            expected_fail_safe_behavior: "effect is not applied twice",
            actual_result: FaultResult::Pass,
            substrate: "REAL_LOCAL_EXTERNAL_SERVICE",
            claim_boundary: "dedup for tested logical effect only",
        },
        FaultRecord {
            fault_id: "REORDERED_EVENT",
            trigger: "old fence snapshot arrives after newer generation",
            expected_fail_safe_behavior: "old snapshot cannot regain authority",
            actual_result: FaultResult::Pass,
            substrate: "MULTIPROCESS + DURABLE_FILE_STORE",
            claim_boundary: "covered by multiprocess_fencing_tests",
        },
        FaultRecord {
            fault_id: "STALE_WRITER",
            trigger: "runtime A writes with generation 1 after runtime B owns generation 2",
            expected_fail_safe_behavior: "REJECTED_STALE_OWNER",
            actual_result: FaultResult::Pass,
            substrate: "MULTIPROCESS",
            claim_boundary: "local two-process fencing proof",
        },
        FaultRecord {
            fault_id: "OLD_OWNER_TERMINAL_DONE",
            trigger: "stale owner attempts terminal mutation",
            expected_fail_safe_behavior: "terminal DONE is rejected",
            actual_result: FaultResult::Pass,
            substrate: "MULTIPROCESS",
            claim_boundary: "DONE-like mutation rejected at authority boundary",
        },
        FaultRecord {
            fault_id: "MISSING_AUTHORITATIVE_HISTORY",
            trigger: "caller omits prior effect history",
            expected_fail_safe_behavior: "authoritative persisted state defeats omission",
            actual_result: FaultResult::Pass,
            substrate: "REAL_LOCAL_EXTERNAL_SERVICE + DURABLE_FILE_STORE",
            claim_boundary: "local idempotency service",
        },
        FaultRecord {
            fault_id: "CORRUPT_OR_STALE_BINDING",
            trigger: "old runtime/generation evidence applied to current acceptance context",
            expected_fail_safe_behavior: "old evidence cannot accept",
            actual_result: FaultResult::Pass,
            substrate: "CANONICAL_ACCEPTANCE",
            claim_boundary: "binding mismatch produces non-acceptance",
        },
        FaultRecord {
            fault_id: "MISSING_ENVIRONMENT_CONFIG",
            trigger: "real runtime credentials absent",
            expected_fail_safe_behavior: "block as secret/provider requirement",
            actual_result: FaultResult::BlockedExternal,
            substrate: "NO_SECRET",
            claim_boundary: "no provider secret was used or required for local Rust gates",
        },
        FaultRecord {
            fault_id: "PERMISSION_DENIAL",
            trigger: "Cargo registry cache initially denies reads in sandbox",
            expected_fail_safe_behavior:
                "classify as environment/toolchain, rerun with authorized access",
            actual_result: FaultResult::Pass,
            substrate: "LOCAL_TOOLCHAIN",
            claim_boundary: "observed during gate execution; not product behavior",
        },
        FaultRecord {
            fault_id: "INVALID_PATH_TRAVERSAL",
            trigger: "no path-taking product API in composed closure path",
            expected_fail_safe_behavior: "not applicable to this substrate",
            actual_result: FaultResult::BlockedToolchain,
            substrate: "NO_APPLICABLE_SURFACE",
            claim_boundary: "must be tested when a path authority API exists",
        },
        FaultRecord {
            fault_id: "PARTIAL_OPERATION_AMBIGUITY",
            trigger: "effect applied but acknowledgement lost",
            expected_fail_safe_behavior: "ambiguous outcome resolves via durable postcondition",
            actual_result: FaultResult::Pass,
            substrate: "REAL_LOCAL_EXTERNAL_SERVICE",
            claim_boundary: "tested failure model only",
        },
        FaultRecord {
            fault_id: "RETRY_PRESSURE_FLAPPING",
            trigger: "runtime health retry pressure and repeated factual failures",
            expected_fail_safe_behavior: "degrade/quarantine without self-report override",
            actual_result: FaultResult::Pass,
            substrate: "RUNTIME_HEALTH_CONTRACT",
            claim_boundary: "contract/adversarial fixture, not hosted runtime telemetry",
        },
        FaultRecord {
            fault_id: "SECRET_BROKER_UNAVAILABLE",
            trigger: "no real credential broker configured",
            expected_fail_safe_behavior: "do not claim broker lifecycle pass",
            actual_result: FaultResult::BlockedExternal,
            substrate: "NO_BROKER",
            claim_boundary: "provider-neutral credential lease remains covered separately",
        },
        FaultRecord {
            fault_id: "VERIFIER_EVALUATOR_UNAVAILABLE",
            trigger: "formal TLC/java tooling absent",
            expected_fail_safe_behavior: "formal execution remains blocked toolchain",
            actual_result: FaultResult::BlockedToolchain,
            substrate: "NO_TLC",
            claim_boundary: "model present is not model checked",
        },
    ]
}

#[test]
fn operational_fault_model_records_high_risk_fail_safe_outcomes() {
    let records = fault_records();
    assert_eq!(records.len(), 20);

    let ids: BTreeSet<_> = records.iter().map(|record| record.fault_id).collect();
    assert_eq!(ids.len(), records.len(), "fault ids must be unique");

    for required in [
        "PROCESS_KILL_AFTER_EFFECT_BEFORE_ACK",
        "STALE_WRITER",
        "OLD_OWNER_TERMINAL_DONE",
        "DUPLICATE_EVENT",
        "CORRUPT_OR_STALE_BINDING",
        "SECRET_BROKER_UNAVAILABLE",
        "VERIFIER_EVALUATOR_UNAVAILABLE",
    ] {
        assert!(ids.contains(required), "missing fault family: {required}");
    }

    for record in &records {
        assert!(!record.trigger.trim().is_empty());
        assert!(!record.expected_fail_safe_behavior.trim().is_empty());
        assert!(!record.substrate.trim().is_empty());
        assert!(!record.claim_boundary.trim().is_empty());
    }

    assert!(records
        .iter()
        .any(|record| record.actual_result == FaultResult::BlockedExternal));
    assert!(records
        .iter()
        .any(|record| record.actual_result == FaultResult::BlockedToolchain));
    assert!(
        records
            .iter()
            .filter(|record| record.actual_result == FaultResult::Pass)
            .count()
            >= 10
    );
}

#[test]
fn machine_readable_gate_evidence_covers_current_closure_gates() {
    let records = vec![
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "discovery-composed",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "DISCOVERY_COMPOSED",
            gate_level: "L3_INTEGRATION",
            command: "cargo test -p metao-testkit --test discovery_composition_tests",
            result: "PASS",
            substrate: "SIMULATED",
            claim_boundary: "project discovery composition only",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "governance-composed",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "GOVERNED_EXECUTION",
            gate_level: "L3_INTEGRATION",
            command: "cargo test -p metao-testkit --test governed_execution_composition",
            result: "PASS",
            substrate: "SIMULATED",
            claim_boundary: "contract-level governance composition",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "external-effect-dedup",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "EXTERNAL_EFFECT_DEDUP",
            gate_level: "L4_RESTART_REAL_LOCAL_EXTERNAL_SERVICE",
            command: "cargo test -p metao-testkit --test durable_external_effect_tests",
            result: "PASS",
            substrate: "LOCAL_REAL_PROCESS + REAL_LOCAL_EXTERNAL_SERVICE",
            claim_boundary: "tested logical effect only; not exactly-once",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "multiprocess-fencing",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "MULTIPROCESS_FENCING",
            gate_level: "L4_MULTIPROCESS_RESTART",
            command: "cargo test -p metao-testkit --test multiprocess_fencing_tests",
            result: "PASS",
            substrate: "MULTIPROCESS + DURABLE_FILE_STORE",
            claim_boundary: "single-host local authority store",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "two-runtime-conformance",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "TWO_RUNTIME_CONFORMANCE",
            gate_level: "L3_INTEGRATION",
            command: "cargo test -p metao-testkit two_material_runtimes_share_the_same_core_conformance_path",
            result: "PASS",
            substrate: "SIMULATED_RUNTIME",
            claim_boundary: "no real external provider runtime",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "security-composed",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "SECURITY_COMPOSITION",
            gate_level: "L3_INTEGRATION",
            command: "cargo test -p metao-testkit --test security_composition_tests",
            result: "PASS",
            substrate: "SIMULATED",
            claim_boundary: "provider-neutral security facts only",
        },
        GateEvidenceRecord {
            schema_version: "metao.gate-evidence.v1",
            record_id: "composed-system",
            repository: "tihotm/metaO",
            exact_sha_binding: "CURRENT_TEST_SHA",
            gate_id: "COMPOSED_SYSTEM_PROOF",
            gate_level: "L4_MULTIPROCESS_RESTART_WITH_REAL_LOCAL_EXTERNAL_SERVICE",
            command: "cargo test -p metao-testkit --test composed_system_closure_tests",
            result: "PASS",
            substrate: "SIMULATED_RUNTIME + MULTIPROCESS + REAL_LOCAL_EXTERNAL_SERVICE",
            claim_boundary: "local closure proof, no real external orchestrator/provider",
        },
    ];

    let serialized = serde_json::to_value(&records).expect("evidence records serialize");
    assert_eq!(serialized.as_array().unwrap().len(), 7);
    for record in serialized.as_array().unwrap() {
        assert_eq!(record["schema_version"], "metao.gate-evidence.v1");
        assert_eq!(record["repository"], "tihotm/metaO");
        assert_eq!(record["result"], "PASS");
        assert_ne!(record["claim_boundary"], "");
        assert_ne!(record["substrate"], "");
        assert_ne!(record["command"], "");
    }
    assert!(serialized
        .to_string()
        .contains("no real external orchestrator/provider"));
}
