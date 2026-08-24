param(
    [string]$VenvPath = (Join-Path $env:LOCALAPPDATA "metaO\release-gate-venv"),
    [switch]$SkipInstall,
    [switch]$AllowDirty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ArtifactRoot = Join-Path $RepoRoot "artifacts\local-release-gate"

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @()
    )

    & $FilePath @ArgumentList
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "Command failed with exit code $code: $FilePath $($ArgumentList -join ' ')"
    }
}

function Resolve-Python312 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        & $py.Source -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{
                FilePath = $py.Source
                Prefix = @("-3.12")
            }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        & $python.Source -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{
                FilePath = $python.Source
                Prefix = @()
            }
        }
    }

    throw "Python 3.12 is required. Install Python 3.12 or make 'py -3.12' available."
}

$Results = [System.Collections.Generic.List[object]]::new()

function Add-GateResult {
    param(
        [string]$Name,
        [string]$Status,
        [int]$ExitCode,
        [double]$DurationSeconds,
        [string]$Detail = ""
    )

    $Results.Add([pscustomobject]@{
        name = $Name
        status = $Status
        exit_code = $ExitCode
        duration_seconds = [math]::Round($DurationSeconds, 3)
        detail = $Detail
    })
}

function Invoke-PythonGate {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList
    )

    Write-Host "`n=== $Name ==="
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    & $script:PythonExe @ArgumentList
    $code = $LASTEXITCODE
    $watch.Stop()

    if ($code -eq 0) {
        Add-GateResult -Name $Name -Status "PASS" -ExitCode 0 -DurationSeconds $watch.Elapsed.TotalSeconds
        Write-Host "PASS: $Name"
    }
    else {
        Add-GateResult -Name $Name -Status "FAIL" -ExitCode $code -DurationSeconds $watch.Elapsed.TotalSeconds
        Write-Host "FAIL: $Name (exit $code)"
    }
}

function Invoke-ExecutableGate {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @()
    )

    Write-Host "`n=== $Name ==="
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    & $FilePath @ArgumentList
    $code = $LASTEXITCODE
    $watch.Stop()

    if ($code -eq 0) {
        Add-GateResult -Name $Name -Status "PASS" -ExitCode 0 -DurationSeconds $watch.Elapsed.TotalSeconds
        Write-Host "PASS: $Name"
    }
    else {
        Add-GateResult -Name $Name -Status "FAIL" -ExitCode $code -DurationSeconds $watch.Elapsed.TotalSeconds
        Write-Host "FAIL: $Name (exit $code)"
    }
}

function Invoke-SdkBoundaryGate {
    Write-Host "`n=== SDK-neutral Core/control-plane boundary ==="
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $pattern = '^\s*(from|import)\s+(langgraph|crewai|agents|openai)(\s|\.|$)'
    $files = Get-ChildItem (Join-Path $RepoRoot "src\metao") -Filter "*.py" -File -Recurse |
        Where-Object { $_.FullName -notmatch '[\\/]adapters[\\/]' }
    $matches = @($files | Select-String -Pattern $pattern)
    $watch.Stop()

    if ($matches.Count -gt 0) {
        $detail = ($matches | ForEach-Object { "$($_.Path):$($_.LineNumber):$($_.Line.Trim())" }) -join " | "
        Add-GateResult -Name "sdk_neutral_boundary" -Status "FAIL" -ExitCode 1 -DurationSeconds $watch.Elapsed.TotalSeconds -Detail $detail
        Write-Host "FAIL: SDK-neutral boundary"
        $matches | ForEach-Object { Write-Host $_ }
    }
    else {
        Add-GateResult -Name "sdk_neutral_boundary" -Status "PASS" -ExitCode 0 -DurationSeconds $watch.Elapsed.TotalSeconds
        Write-Host "PASS: SDK-neutral boundary"
    }
}

Push-Location $RepoRoot
try {
    Invoke-NativeChecked -FilePath "git" -ArgumentList @("rev-parse", "--is-inside-work-tree")
    $Branch = (& git rev-parse --abbrev-ref HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git branch" }
    $Commit = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git commit" }
    $DirtyLines = @(& git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git worktree" }
    $IsClean = $DirtyLines.Count -eq 0

    if (-not $IsClean -and -not $AllowDirty) {
        throw "Worktree is dirty. Commit/stash changes or rerun with -AllowDirty (evidence will record clean_worktree=false)."
    }

    $Bootstrap = Resolve-Python312
    $VenvPython = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating isolated Python 3.12 environment at $VenvPath"
        $venvArgs = @($Bootstrap.Prefix) + @("-m", "venv", $VenvPath)
        Invoke-NativeChecked -FilePath $Bootstrap.FilePath -ArgumentList $venvArgs
    }

    $script:PythonExe = $VenvPython
    & $script:PythonExe -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "Existing gate venv is not Python 3.12. Remove '$VenvPath' or pass another -VenvPath."
    }

    $PythonVersion = (& $script:PythonExe -c "import platform; print(platform.python_version())").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to read gate Python version" }

    $env:OPENAI_API_KEY = ""
    $env:CREWAI_DISABLE_TELEMETRY = "true"
    $env:CREWAI_TRACING_ENABLED = "false"
    $env:OTEL_SDK_DISABLED = "true"

    if (-not $SkipInstall) {
        Write-Host "Installing metaO and exact runtime pins into isolated gate venv"
        Invoke-NativeChecked -FilePath $script:PythonExe -ArgumentList @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-NativeChecked -FilePath $script:PythonExe -ArgumentList @("-m", "pip", "install", "-e", ".")
        Invoke-NativeChecked -FilePath $script:PythonExe -ArgumentList @(
            "-m", "pip", "install",
            "openai-agents==0.21.1",
            "crewai==1.15.16",
            "langgraph==1.2.11"
        )
    }

    Invoke-PythonGate -Name "exact_runtime_versions" -ArgumentList @(
        "-c",
        "from importlib.metadata import version; assert version('openai-agents') == '0.21.1'; assert version('crewai') == '1.15.16'; assert version('langgraph') == '1.2.11'; print('OpenAI Agents', version('openai-agents')); print('CrewAI', version('crewai')); print('LangGraph', version('langgraph'))"
    )

    $MetaOExe = Join-Path $VenvPath "Scripts\metao.exe"
    Invoke-ExecutableGate -Name "installed_cli_help" -FilePath $MetaOExe -ArgumentList @("--help")
    Invoke-PythonGate -Name "installed_import_smoke" -ArgumentList @(
        "-c",
        "import metao; import metao.runtime_factory; import metao.runtime_certification; import metao.runtime_certification_revocation"
    )

    Invoke-PythonGate -Name "r2_wu05_feedback" -ArgumentList @("-m", "unittest", "tests.unit.test_roadmap_2_work_unit_05", "-v")
    Invoke-PythonGate -Name "r7_wu01_failure_aware_replan" -ArgumentList @("tests/unit/test_roadmap_7_work_unit_01.py")
    Invoke-PythonGate -Name "r7_wu02_durable_escalation" -ArgumentList @("tests/unit/test_roadmap_7_work_unit_02.py")
    Invoke-PythonGate -Name "full_unit_suite" -ArgumentList @("-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_*.py", "-v")

    Invoke-PythonGate -Name "r2_real_runtime_sandbox" -ArgumentList @("tests/integration/test_r2_wu01_second_real_runtime.py")
    Invoke-PythonGate -Name "r3_real_runtime_certification" -ArgumentList @("tests/integration/test_r3_wu04_real_runtime_certification.py")
    Invoke-PythonGate -Name "r4_real_declarative_certified_runtimes" -ArgumentList @("tests/integration/test_r4_wu03_real_declarative_certified_runtimes.py")
    Invoke-PythonGate -Name "r5_real_certificate_lifecycle" -ArgumentList @("tests/integration/test_r5_wu04_real_certificate_lifecycle.py")

    Invoke-PythonGate -Name "r6_wu04_openai_adapter_unit" -ArgumentList @("tests/unit/test_roadmap_6_work_unit_04.py")
    Invoke-PythonGate -Name "r6_wu04_openai_real_conformance" -ArgumentList @("tests/integration/test_r6_wu04_openai_agents_real.py")
    Invoke-PythonGate -Name "r6_wu05_three_real_runtimes" -ArgumentList @("tests/integration/test_r6_wu05_three_real_runtimes.py")
    Invoke-PythonGate -Name "r7_wu03_three_runtime_recovery" -ArgumentList @("tests/integration/test_r7_wu03_three_runtime_recovery.py")

    Invoke-PythonGate -Name "block_o1_langgraph_real" -ArgumentList @("tests/integration/test_o1_langgraph_real.py")
    Invoke-PythonGate -Name "block_o2_e2e_sandbox" -ArgumentList @("tests/integration/test_o2_e2e_sandbox.py")
    Invoke-PythonGate -Name "block_o3_failover_sandbox" -ArgumentList @("tests/integration/test_o3_failover_sandbox.py")
    Invoke-PythonGate -Name "block_o4_governance_gates" -ArgumentList @("tests/integration/test_o4_governance_gates.py")
    Invoke-PythonGate -Name "block_o5_runtime_swap" -ArgumentList @("tests/integration/test_o5_runtime_swap.py")

    Invoke-SdkBoundaryGate

    $FailureCount = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    $Overall = if ($FailureCount -eq 0) { "PASS" } else { "FAIL" }
    New-Item -ItemType Directory -Path $ArtifactRoot -Force | Out-Null
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $SummaryPath = Join-Path $ArtifactRoot "gate-$Timestamp.json"

    $Summary = [ordered]@{
        schema_version = 1
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        branch = $Branch
        commit = $Commit
        clean_worktree = $IsClean
        python_version = $PythonVersion
        runtime_pins = [ordered]@{
            openai_agents = "0.21.1"
            crewai = "1.15.16"
            langgraph = "1.2.11"
        }
        hosted_runner_blocker = "external_pre_step"
        results = $Results
        failure_count = $FailureCount
        overall = $Overall
    }

    $Summary | ConvertTo-Json -Depth 8 | Set-Content -Path $SummaryPath -Encoding utf8

    Write-Host "`n========================================"
    Write-Host "LOCAL_RELEASE_GATE = $Overall"
    Write-Host "BRANCH = $Branch"
    Write-Host "COMMIT = $Commit"
    Write-Host "CLEAN_WORKTREE = $IsClean"
    Write-Host "RESULTS = $($Results.Count)"
    Write-Host "FAILURES = $FailureCount"
    Write-Host "EVIDENCE = $SummaryPath"
    Write-Host "========================================"

    if ($Overall -ne "PASS") {
        exit 1
    }
    exit 0
}
finally {
    Pop-Location
}
