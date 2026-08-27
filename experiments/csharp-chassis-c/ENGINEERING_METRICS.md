# Engineering Metrics

Measured on `2026-08-27` in `experiments/csharp-chassis-c`.

Scope:

- candidate `C`
- current branch `test/csharp-chassis-spike-c-v1`
- direct semantic harness only
- VSTest remains `BLOCKED_ENV`

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
