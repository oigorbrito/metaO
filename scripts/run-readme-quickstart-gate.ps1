param(
    [string]$VenvPath = (Join-Path $env:LOCALAPPDATA "metaO\readme-quickstart-venv"),
    [string]$EvidenceRoot = (Join-Path $env:LOCALAPPDATA "metaO\readme-quickstart-evidence"),
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$StartedAt = (Get-Date).ToUniversalTime().ToString("o")
$EvidencePath = Join-Path $EvidenceRoot "readme-quickstart-$Timestamp.json"
$Results = New-Object System.Collections.Generic.List[object]
$FatalError = $null
$Overall = "BOOTSTRAP_FAIL"
$Branch = $null
$Commit = $null
$IsClean = $false
$PythonVersion = $null

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $RepoRoot
    )

    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location $WorkingDirectory
    try {
        $outputLines = @(& $FilePath @ArgumentList 2>&1)
        $code = $LASTEXITCODE
    }
    finally {
        Pop-Location
        $watch.Stop()
    }

    $output = ($outputLines | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    $status = if ($code -eq 0) { "PASS" } else { "FAIL" }
    $Results.Add([pscustomobject]@{
        name = $Name
        command = "$FilePath $($ArgumentList -join ' ')"
        status = $status
        exit_code = $code
        duration_seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
        output = $output.Trim()
    })
    Write-Host "${status}: $Name (exit $code)"
    return $code
}

function Write-Evidence {
    New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
    $failureCount = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    $summary = [ordered]@{
        schema_version = 1
        gate = "README_QUICKSTART_CANONICAL"
        repository = "oigorbrito/metaO"
        branch = $Branch
        commit = $Commit
        clean_worktree = $IsClean
        diagnostic_override = [bool]$AllowDirty
        python = $PythonVersion
        started_at_utc = $StartedAt
        completed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        overall = $Overall
        result_count = $Results.Count
        failure_count = $failureCount
        canonical_test = "tests/integration/test_readme_quickstart_e2e.py"
        canonical_factory = "metao.runtime_factory:create_operator"
        runtime_catalog = "examples/runtime-catalog-quickstart.json"
        accepted_mission = "examples/mission-quickstart-accepted.json"
        results = @($Results)
        fatal_error = $FatalError
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $EvidencePath -Encoding UTF8
}

try {
    Set-Location $RepoRoot

    $Branch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git branch." }

    $Commit = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git commit." }

    $DirtyLines = @(& git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git worktree." }
    $IsClean = $DirtyLines.Count -eq 0

    if (-not $IsClean -and -not $AllowDirty) {
        throw "Worktree is dirty. Use -AllowDirty only for diagnostic evidence; dirty runs cannot produce PASS."
    }

    $versionOutput = @(& py -3.12 --version 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 is required and was not found via 'py -3.12'." }
    $PythonVersion = (($versionOutput | ForEach-Object { $_.ToString() }) -join " ").Trim()

    if (Test-Path $VenvPath) {
        Remove-Item -Recurse -Force $VenvPath
    }
    New-Item -ItemType Directory -Path (Split-Path $VenvPath -Parent) -Force | Out-Null

    $code = Invoke-Native -Name "create_venv" -FilePath "py" -ArgumentList @("-3.12", "-m", "venv", $VenvPath)
    if ($code -ne 0) { throw "Virtual environment creation failed." }

    $VenvPython = Join-Path $VenvPath "Scripts\python.exe"
    $MetaOExe = Join-Path $VenvPath "Scripts\metao.exe"
    if (-not (Test-Path $VenvPython)) { throw "Virtual environment python.exe was not created." }

    $code = Invoke-Native -Name "install_package_editable" -FilePath $VenvPython -ArgumentList @("-m", "pip", "install", "-e", ".")
    if ($code -ne 0) { throw "Package installation failed." }

    if (-not (Test-Path $MetaOExe)) { throw "Installed metao console script was not found." }

    $code = Invoke-Native -Name "metao_help" -FilePath $MetaOExe -ArgumentList @("--help")
    if ($code -ne 0) { throw "Installed metao --help failed." }

    $code = Invoke-Native -Name "canonical_readme_quickstart_e2e" -FilePath $VenvPython -ArgumentList @("tests/integration/test_readme_quickstart_e2e.py")

    $failureCount = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    if ($failureCount -gt 0 -or $code -ne 0) {
        $Overall = "FAIL"
    }
    elseif ($IsClean) {
        $Overall = "PASS"
    }
    else {
        $Overall = "DIAGNOSTIC_PASS"
    }
}
catch {
    $FatalError = $_.Exception.Message
    if ($Overall -ne "FAIL") {
        $Overall = "BOOTSTRAP_FAIL"
    }
}
finally {
    Write-Evidence
}

Write-Host "`n========================================"
Write-Host "README_QUICKSTART_GATE = $Overall"
Write-Host "BRANCH = $Branch"
Write-Host "COMMIT = $Commit"
Write-Host "CLEAN_WORKTREE = $IsClean"
Write-Host "PYTHON = $PythonVersion"
Write-Host "RESULTS = $($Results.Count)"
Write-Host "FAILURES = $(@($Results | Where-Object { $_.status -eq 'FAIL' }).Count)"
Write-Host "EVIDENCE = $EvidencePath"
if ($FatalError) {
    Write-Host "FATAL_ERROR = $FatalError"
}
Write-Host "========================================"

if ($Overall -eq "PASS") { exit 0 }
if ($Overall -eq "FAIL") { exit 1 }
exit 2
