# C# Chassis Spike C Qualification

Candidate:

- `C = explicit C#/.NET modular chassis`

Environment used for the last local execution:

- `.NET SDK = 10.0.400`
- branch = `test/csharp-chassis-spike-c-v1`

## Evidence discipline

Current branch HEAD adds the remaining targeted L5 checkpoint/resume and runtime-revocation fixtures after the last executed 69-case baseline.

Therefore the current qualification is:

- `L0 = PASS`
- `L1 = PASS`
- `L2 = PASS`
- `L3 = PASS`
- `L4 = PASS`
- `L5 = PARTIAL_PENDING_EXECUTION`

Executed evidence preserved from the prior validated head:

- `dotnet restore = PASS`
- `dotnet build --no-restore -warnaserror = PASS`
- `direct semantic harness = 69/69 PASS`
- frozen Python golden = `4/4`
- `dotnet test = BLOCKED_ENV / standard-runner parity NOT_PROVEN`

Current-head L5 additions are implemented but must not be promoted to executed PASS until rerun:

- serialized checkpoint round-trip
- restart/resume using reconstructed state and a fresh registry
- policy revalidation after resume
- subject-state revalidation after resume
- runtime authorization modeled separately from runtime health
- newer `REVOKED` authorization overriding older `ACTIVE`
- healthy runtime not selectable when revoked
- successful runtime execution unable to become accepted after revocation
- restart against newly revoked runtime requiring replan

The current direct harness target is:

```text
DIRECT_COUNT = 79
DIRECT_FAILURES = 0 required
```

On a .NET 10 environment, the narrow current-head validation is:

```powershell
cd experiments/csharp-chassis-c
dotnet restore MetaO.ChassisC.sln
dotnet build MetaO.ChassisC.sln --no-restore -warnaserror
dotnet run --project tests/MetaO.TestKit/MetaO.TestKit.csproj --no-build
```

Do not infer current-head PASS from the earlier 69/69 run. Hosted GitHub Actions has failed before configured workflow steps and the repository workflow is Python-oriented, so that failure is infrastructure evidence rather than C# semantic evidence.

## Architecture results already executed/code-backed before the current L5 delta

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

## Measured engineering snapshot

- `projects = 7`
- `C# files = 7`
- `LOC = 1017`
- `production PackageReference = 0`
- `test-only PackageReference = 0`
- `ProjectReference = 14`
- `owned unsafe blocks = 0`
- `owned native interop = 0`
- `artifact footprint bytes = 723122`
- clean build samples ms = `4464, 5185, 4657`
- incremental build samples ms = `4328, 3277, 3138`
- direct harness samples ms = `376, 319, 499`
- `clean build time median ms = 4657`
- `incremental build time median ms = 3277`
- `direct harness time median ms = 376`

The median corrections are arithmetic-only; the original measured samples are unchanged.

## Remaining evidence gaps

- execute the current 79-case direct harness on a .NET 10 environment
- fully comparable Rust executable evidence remains blocked in the recorded Windows host by missing MSVC `link.exe`
- standard VSTest parity is not required to claim the direct harness result and remains separately `NOT_PROVEN/BLOCKED_ENV`

ABP classification:

- `DEFER` as a host/productivity donor; it is not a second Core or acceptance authority.

Product migration:

- `NOT_AUTHORIZED`

```text
#199_SCORECARD = FROZEN
```