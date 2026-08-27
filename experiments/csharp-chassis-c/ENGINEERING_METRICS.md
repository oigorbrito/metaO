# Engineering Metrics

Measured on `2026-08-27` in `experiments/csharp-chassis-c`.

Scope:

- candidate `C`
- current branch `test/csharp-chassis-spike-c-v1`
- direct semantic harness only
- VSTest remains `BLOCKED_ENV`
- runtime host = `Microsoft Windows NT 10.0.26200.0`
- visible logical processors = `8`
- PowerShell version = `7.6.4`

Method:

- inventory metrics were derived from the checked-in source tree only
- build and harness timings were measured on this checkout after the current code state was in place
- each timing metric uses 3 samples and reports the median sample
- artifact footprint is the sum of the build outputs under `bin/Debug/net10.0`

Inventory:

- `PROJECT_COUNT = 7`
- `CSHARP_FILES = 7`
- `LOC = 1017`
- `PRODUCTION_PACKAGE_REFERENCES = 0`
- `TEST_ONLY_PACKAGE_REFERENCES = 0`
- `PROJECT_REFERENCES = 14`
- `OWNED_UNSAFE_BLOCKS = 0`
- `OWNED_NATIVE_INTEROP = 0`
- `ARTIFACT_FOOTPRINT_BYTES = 723122`

Timing methodology:

- `clean build` sample = `dotnet clean MetaO.ChassisC.sln --nologo`, then `dotnet build MetaO.ChassisC.sln --no-restore -warnaserror`
- `incremental build` sample = repeated `dotnet build MetaO.ChassisC.sln --no-restore -warnaserror`
- `direct harness` sample = `tests/MetaO.TestKit/bin/Debug/net10.0/MetaO.TestKit.exe`
- median = middle of 3 measured samples

Samples:

- `CLEAN_BUILD_TIME_SAMPLES_MS = 4464, 5185, 4657`
- `CLEAN_BUILD_TIME_MEDIAN_MS = 5185`
- `INCREMENTAL_BUILD_TIME_SAMPLES_MS = 4328, 3277, 3138`
- `INCREMENTAL_BUILD_TIME_MEDIAN_MS = 4328`
- `DIRECT_HARNESS_TIME_SAMPLES_MS = 376, 319, 499`
- `DIRECT_HARNESS_TIME_MEDIAN_MS = 499`

Notes:

- artifact footprint is the sum of `dll`, `exe`, `pdb`, `deps.json`, and `runtimeconfig.json` under `bin/Debug/net10.0`
- build timings were taken after the code and test changes in this turn

Definitions:

- `PROJECT_COUNT` counts `.csproj` files in the spike
- `CSHARP_FILES` counts non-generated `.cs` files in the spike
- `LOC` counts lines across tracked `.cs` and `.md` files in the spike
- `PRODUCTION_PACKAGE_REFERENCES` counts package references in production projects
- `TEST_ONLY_PACKAGE_REFERENCES` counts package references in test projects
- `PROJECT_REFERENCES` counts project-to-project references across the spike
- `OWNED_UNSAFE_BLOCKS` counts explicit `unsafe` usages in owned source
- `OWNED_NATIVE_INTEROP` counts P/Invoke or equivalent native interop markers in owned source

Reading:

- these values are descriptive evidence, not acceptance criteria by themselves
- timing medians are representative samples, not guarantees of future runtime
- the visible host facts above are the minimum environment details confirmed locally for these measurements
