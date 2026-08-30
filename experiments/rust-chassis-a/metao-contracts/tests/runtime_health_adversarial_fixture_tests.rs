use serde_json::Value;
use std::collections::BTreeSet;

const FIXTURE: &str = include_str!("fixtures/runtime_health_adversarial_cases.v1.json");

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("runtime health adversarial fixture must be valid JSON")
}

#[test]
fn schema_and_envoy_pin_are_explicit() {
    let value = fixture();
    assert_eq!(value["schema_version"], 1);
    assert_eq!(value["fixture_family"], "runtime-health-adversarial");

    let source = value["sources"]
        .as_array()
        .and_then(|sources| sources.first())
        .expect("one source pin is required");
    assert_eq!(source["reference"], "envoyproxy/envoy");
    assert_eq!(source["version"], "v1.39.1");
    assert_eq!(
        source["pinned_revision"],
        "b579d07d3ad7ee11d32b105e91a5a39ad24718d7"
    );
}

#[test]
fn scenario_order_and_ids_are_deterministic() {
    let value = fixture();
    let scenarios = value["scenarios"].as_array().expect("scenarios must be array");
    let ids: Vec<&str> = scenarios
        .iter()
        .map(|scenario| scenario["fixture_id"].as_str().expect("fixture id"))
        .collect();
    let unique: BTreeSet<&str> = ids.iter().copied().collect();

    assert_eq!(ids.len(), 10);
    assert_eq!(ids.len(), unique.len());
    for (index, scenario) in scenarios.iter().enumerate() {
        assert_eq!(scenario["sequence"], (index + 1) as u64);
    }
}

#[test]
fn observation_counters_are_factual_and_consistent() {
    let value = fixture();
    for scenario in value["scenarios"].as_array().expect("scenarios") {
        let observation = &scenario["observation"];
        let attempts = observation["attempts"].as_u64().expect("attempts");
        let successes = observation["successes"].as_u64().expect("successes");
        let failures = observation["failures"].as_u64().expect("failures");
        let consecutive = observation["consecutive_failures"]
            .as_u64()
            .expect("consecutive failures");
        let timeouts = observation["timeouts"].as_u64().expect("timeouts");
        let transport = observation["transport_failures"]
            .as_u64()
            .expect("transport failures");

        assert_eq!(successes + failures, attempts);
        assert!(consecutive <= failures);
        assert!(timeouts <= failures);
        assert!(transport <= failures);
    }
}

#[test]
fn caller_policy_is_explicit_and_envoy_defaults_are_not_authority() {
    let value = fixture();
    for scenario in value["scenarios"].as_array().expect("scenarios") {
        let policy = &scenario["policy"];
        assert!(policy["quarantine_consecutive_failures"].as_u64().is_some());
        assert!(policy["unhealthy_failure_percent"].as_u64().is_some());
        assert!(policy["recovery_successes_required"].as_u64().is_some());
        assert!(policy["retry_pressure_limit"].as_u64().is_some());
    }

    let strict_zero = value["scenarios"]
        .as_array()
        .expect("scenarios")
        .iter()
        .find(|scenario| scenario["fixture_id"] == "zero-retry-pressure-limit-is-strict-valid-policy")
        .expect("strict zero fixture");
    assert_eq!(strict_zero["policy"]["retry_pressure_limit"], 0);
    assert_eq!(strict_zero["expected_retry_pressure_exceeded"], true);
}

#[test]
fn self_report_never_becomes_health_authority() {
    let value = fixture();
    assert_eq!(value["authority_boundary"]["self_report_is_health_authority"], false);

    let lying = value["scenarios"]
        .as_array()
        .expect("scenarios")
        .iter()
        .find(|scenario| scenario["fixture_id"] == "lying-self-report-cannot-override-failures")
        .expect("lying self-report fixture");
    assert_eq!(lying["observation"]["self_reported_healthy"], true);
    assert_eq!(lying["expected_state"], "UNHEALTHY");

    let empty = value["scenarios"]
        .as_array()
        .expect("scenarios")
        .iter()
        .find(|scenario| scenario["fixture_id"] == "empty-window-remains-unknown")
        .expect("empty window fixture");
    assert_eq!(empty["observation"]["self_reported_healthy"], true);
    assert_eq!(empty["expected_state"], "UNKNOWN");
}

#[test]
fn failover_and_config_change_do_not_conflate_history_scopes() {
    let value = fixture();
    let scenarios = value["scenarios"].as_array().expect("scenarios");

    let failover = scenarios
        .iter()
        .find(|scenario| scenario["fixture_id"] == "failover-b-does-not-reset-a-history")
        .expect("failover fixture");
    assert_ne!(failover["runtime"], failover["failover_target"]);
    assert_eq!(failover["expected_state"], "QUARANTINED");

    let mutation = scenarios
        .iter()
        .find(|scenario| scenario["fixture_id"] == "config-mutation-creates-distinct-health-scope")
        .expect("config mutation fixture");
    assert_ne!(mutation["runtime"]["config_id"], mutation["previous_scope"]["config_id"]);
}

#[test]
fn fixture_has_no_dispatch_failover_or_acceptance_authority() {
    let value = fixture();
    let authority = &value["authority_boundary"];
    assert_eq!(authority["fixture_is_health_implementation"], false);
    assert_eq!(authority["retry_pressure_fact_dispatches_retry"], false);
    assert_eq!(authority["fixture_expectation_is_product_acceptance"], false);

    let serialized = serde_json::to_string(&value).expect("serialize fixture");
    for forbidden in [
        "AcceptanceDecision",
        "PROJECT_ACCEPTED",
        "MVP_ACCEPTED",
        "dispatch_authority",
        "failover_authority",
        "provider_sdk",
    ] {
        assert!(!serialized.contains(forbidden), "forbidden authority marker: {forbidden}");
    }
}
