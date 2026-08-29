# Final Language Tiebreak Evidence

## Heads

- Rust A: `ce6d2790ac5a5118f144a16788bfc68045602ce9`
- C# C: `ef641e94b1ad1cfb137d69a7a8c0648804f58033`

## TEST1_RUNTIME

Rust:
- `wall_clock_ms` median `39.0405`
- `cpu_ms` median `15.625`
- `peak_working_set_bytes` median `3305472`
- `artifact_bytes` `374260`
- `semantic_equivalence = PASS`

C#:
- `wall_clock_ms` median `323.8627`
- `cpu_ms` median `250`
- `peak_working_set_bytes` median `29908992`
- `artifact_bytes` `374260`
- `semantic_equivalence = PASS`

A/C ratios:
- `wall_clock_ms = 0.1207`
- `cpu_ms = 0.0625`
- `peak_working_set_bytes = 0.1103`

## TEST2_FAULT_INJECTION

Rust:
- `contained_failures = 1000`
- `escaped_failures = 0`
- `invariant_violations = 250`
- `post_fault_recovery_successes = 1000`
- `unexpected_process_exits = 0`
- `recovery_latency_p50_ms = 0`
- `recovery_latency_p95_ms = 2`
- `recovery_latency_p99_ms = 2`

C#:
- `contained_failures = 250`
- `escaped_failures = 0`
- `invariant_violations = 250`
- `post_fault_recovery_successes = 1000`
- `unexpected_process_exits = 0`
- `recovery_latency_p50_ms = 0`
- `recovery_latency_p95_ms = 15`
- `recovery_latency_p99_ms = 19`
- `peak_rss_bytes = 28119040`
- `rss_first_100_mean = 22445260.8`
- `rss_last_100_mean = 27955814.4`
- `rss_delta_bytes = 6905856`
- `rss_growth_percent = 32.55454720988608`

hard-gate violations:
- none recorded in executed evidence

## TEST3_MUTATION

Rust:
- `generated = 26`
- `viable = 23`
- `killed = 19`
- `survived = 4`
- `timeout = 0`
- `compile_error = 3`
- `mutation_score = 82.6086956522`

C#:
- `BLOCKED`

hard-gate survivors:
- `metao-kernel/src/lib.rs:28:9: replace || with && in evaluate_acceptance`
- `metao-kernel/src/lib.rs:34:18: replace < with == in evaluate_acceptance`
- `metao-kernel/src/lib.rs:34:18: replace < with <= in evaluate_acceptance`
- `metao-kernel/src/lib.rs:34:59: replace > with >= in evaluate_acceptance`

## ARTIFACTS

- `C:\Projetos\metao-gate\evidence\language-tiebreak\machine.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\runtime-rust-raw.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\runtime-csharp-raw.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\fault-rust-raw.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\fault-csharp-raw.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\mutation-rust.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\mutation-csharp.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\mutation-targets.json`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\mutation-targets.md`
- `C:\Projetos\metao-gate\evidence\language-tiebreak\commands.log`

## BLOCKED

- C# mutation run failed on restore because the offline environment could not reach `https://api.nuget.org/v3/index.json` during the initial build of the disposable xUnit harness.

## Final Flags

- `RUST_HARD_GATE_FAILURE = NO`
- `CSHARP_HARD_GATE_FAILURE = NO`
- `LANGUAGE_DECISION = HOLD_PENDING_OWNER_REVIEW`
