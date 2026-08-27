# C# Chassis Spike C Qualification

Candidate:

- `C = explicit C#/.NET modular chassis`

Objective:

- qualify candidate `C` against the frozen Python golden and the direct semantic harness
- keep the out-of-process contract seam explicit and fail-closed

Environment:

- `.NET SDK = 10.0.400`
- branch = `test/csharp-chassis-spike-c-v1`

Current qualification:

- `L0 = PASS`
- `L1 = PASS`
- `L2 = PASS`
- `L3 = PASS`
- `L4 = PASS`
- `L5 = PARTIAL`

Execution evidence:

- `dotnet restore = PASS`
- `dotnet build --no-restore -warnaserror = PASS`
- `direct semantic harness = 69/69 PASS`
- `dotnet test = BLOCKED_ENV`

Method:

- evidence is collected from `dotnet restore`, `dotnet build`, and the direct executable harness
- `dotnet test` remains blocked because the harness is not a conventional VSTest project in this environment
- metrics are reported only when they were measured in this checkout

Root cause:

- `MetaO.TestKit` is an executable semantic harness rather than a conventional VSTest project.
- The standard test packages are not present in the local cache.
- Standard runner parity remains `NOT_PROVEN`.

Architecture results:

- `KERNEL_FRAMEWORK_LEAK = NO`
- `WHOLE_ORCHESTRATOR_REPLACEMENT = PASS`
- `SUCCEEDED_NOT_ACCEPTED = PASS`
- `HARD_DENY = PASS`
- `EVIDENCE_BINDING = PASS`
- `RUNTIME_SELF_AUTHORITY = PASS`
- `SECOND_ACCEPTANCE_AUTHORITY = NO`
- `SECOND_DURABLE_ENGINE = NO`
- `OUT_OF_PROCESS_CONTRACT_SEAM = PASS`
- `RECONCILIATION_IDEMPOTENCY = PASS`
- `BUDGET_CONCURRENCY = PASS`
- `SETTLEMENT_IDEMPOTENCY = PASS`
- `THREE_RUNTIME_CONTRACT = PASS`
- `UNHEALTHY_NOT_SELECTED = PASS`
- `FAILOVER_ORDER = PASS`
- `REPLAN_AFTER_FAILURE = PASS`
- `ALL_RUNTIMES_FAIL_NOT_ACCEPTED = PASS`
- `RECOVERY_CONVERGENCE = PASS`
- `RECOVERY_IDEMPOTENT = PASS`
- `STALE_RUNTIME_STATE = PASS`
- `FAILOVER_AUTHORITY_BOUNDARY = PASS`

Metrics:

- `projects = 7`
- `C# files = 7`
- `LOC = 1017`
- `production PackageReference = 0`
- `test-only PackageReference = 0`
- `ProjectReference = 14`
- `owned unsafe blocks = 0`
- `owned native interop = 0`
- `artifact footprint bytes = 723122`
- `clean build time median ms = 5185`
- `incremental build time median ms = 4328`
- `direct harness time median ms = 499`

Interpretation:

- `PASS` means the gate was executed and satisfied in this checkout
- `PARTIAL` means the current evidence is incomplete for a stronger claim
- `BLOCKED_ENV` means the gate cannot be completed with the current runner shape in this checkout
- `NOT_PROVEN` is reserved for claims not demonstrated by the present evidence

Known incomplete evidence:

- standard VSTest parity
- full L5 operational/adversarial comparison
- fully comparable Rust execution

ABP classification:

- `DEFER`

Product migration:

- `NOT_AUTHORIZED`
