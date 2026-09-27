#[test]
fn core_runtime_sdk_dependencies_are_zero() {
    let manifests = [
        include_str!("../../metao-contracts/Cargo.toml").to_lowercase(),
        include_str!("../../metao-kernel/Cargo.toml").to_lowercase(),
    ];
    for forbidden in [
        "langgraph",
        "crewai",
        "openai agents",
        "openai",
        "microsoft agent framework",
        "autogen",
        "semantic kernel",
    ] {
        assert!(
            !manifests
                .iter()
                .any(|manifest| manifest.contains(forbidden)),
            "forbidden sdk dependency leaked into core: {forbidden}"
        );
    }
}
