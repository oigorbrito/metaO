param(
    [string]$VenvPath = (Join-Path $env:LOCALAPPDATA "metaO\readme-quickstart-venv"),
    [string]$EvidenceRoot = (Join-Path $env:LOCALAPPDATA "metaO\readme-quickstart-evidence"),
    [switch]$AllowDirty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidencePath = Join-Path $EvidenceRoot "readme-quickstart-$Timestamp.json"
$Results = [System.Collections.Generic.List[object]]::new()
$Branch = $null
$Commit = $null
$IsClean = $null
$PythonVersion = $null
$Overall = "BOOTSTRAP_FAIL"
$FatalError = $null
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "metao-readme-quickstart-$Timestamp"

function ConvertTo-CommandLineArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '\\(?=\\*")|"$', '$0$0' -replace '"', '\"') + '"'
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @(),
        [Parameter()][string]$WorkingDirectory = $RepoRoot,
        [Parameter()][hashtable]$Environment = @{}
    )

    Write-Host "`n=== $Name ==="
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo.FileName = $FilePath
    $process.StartInfo.Arguments = (($ArgumentList | ForEach-Object { ConvertTo-CommandLineArgument $_ }) -join " ")
    $process.StartInfo.WorkingDirectory = $WorkingDirectory
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    foreach ($key in $Environment.Keys) {
        $process.StartInfo.Environment[$key] = [string]$Environment[$key]
    }
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $watch.Stop()
    $code = $process.ExitCode
    $output = (($stdout, $stderr) -join "").Trim()

    $status = if ($code -eq 0) { "PASS" } else { "FAIL" }
    $Results.Add([pscustomobject]@{
        name = $Name
        command = "$FilePath $($ArgumentList -join ' ')"
        status = $status
        exit_code = $code
        duration_seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
        output = $output
    })
    Write-Host "${status}: $Name (exit $code)"
}

function Resolve-Python312 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        & $py.Source @("-3.12", "-c", "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)")
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ FilePath = $py.Source; Prefix = @("-3.12") }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        & $python.Source @("-c", "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)")
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ FilePath = $python.Source; Prefix = @() }
        }
    }

    throw "Python 3.12 is required."
}

function Write-Evidence {
    New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
    $failureCount = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    $summary = [ordered]@{
        schema_version = 1
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        branch = $Branch
        commit = $Commit
        clean_worktree = $IsClean
        python_version = $PythonVersion
        temp_root = $TempRoot
        venv_path = $VenvPath
        fatal_error = $FatalError
        results = @($Results)
        failure_count = $failureCount
        overall = $Overall
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $EvidencePath -Encoding utf8
}

try {
    New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

    Push-Location $RepoRoot
    try {
        $Branch = (& git rev-parse --abbrev-ref HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git branch." }
        $Commit = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw "Unable to resolve Git commit." }
        $DirtyLines = @(& git status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git worktree." }
        $IsClean = $DirtyLines.Count -eq 0
    }
    finally {
        Pop-Location
    }

    if (-not $IsClean -and -not $AllowDirty) {
        throw "Worktree is dirty. Rerun with -AllowDirty only for diagnostic evidence."
    }

    $bootstrap = Resolve-Python312
    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        & $bootstrap.FilePath @($bootstrap.Prefix + @("-m", "venv", $VenvPath))
        if ($LASTEXITCODE -ne 0) { throw "Unable to create Python 3.12 virtual environment." }
    }
    $venvScripts = Split-Path -Parent $venvPython
    $env:PATH = "$venvScripts;$env:PATH"
    $PythonVersion = (& $venvPython -c "import platform; print(platform.python_version())").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to read Python version." }

    $missionPath = Join-Path $RepoRoot "examples\readme_mission.json"

    $dbPath = Join-Path $TempRoot "metao.db"
    $metaoExe = Join-Path $venvScripts "metao.exe"
    $envForCommands = @{
        "METAO_OPERATOR_FACTORY" = "metao.examples.readme_factory:create_operator"
    }

    Invoke-Native -Name "install_package_editable" -FilePath $venvPython -ArgumentList @("-m", "pip", "install", "-e", ".")
    Invoke-Native -Name "metao_help" -FilePath $metaoExe -ArgumentList @("--help")
    Invoke-Native -Name "doctor" -FilePath $metaoExe -ArgumentList @("--db", $dbPath, "doctor") -Environment $envForCommands
    Invoke-Native -Name "runtimes" -FilePath $metaoExe -ArgumentList @("--db", $dbPath, "runtimes") -Environment $envForCommands
    Invoke-Native -Name "first_mission" -FilePath $metaoExe -ArgumentList @("--db", $dbPath, "run", $missionPath) -Environment $envForCommands
    Invoke-Native -Name "status" -FilePath $metaoExe -ArgumentList @("--db", $dbPath, "status", "readme-first-mission") -Environment $envForCommands
    Invoke-Native -Name "inspect_new_process" -FilePath $metaoExe -ArgumentList @("--db", $dbPath, "inspect", "readme-first-mission") -Environment $envForCommands

    $failureCount = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    $Overall = if ($failureCount -eq 0) { "PASS" } else { "FAIL" }
}
catch {
    $FatalError = $_.Exception.Message
    if ($Results.Count -gt 0) {
        $Overall = "HARNESS_FAIL"
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
Write-Host "FAILURES = $(@($Results | Where-Object { $_.status -eq "FAIL" }).Count)"
Write-Host "EVIDENCE = $EvidencePath"
if ($FatalError) {
    Write-Host "FATAL_ERROR = $FatalError"
}
Write-Host "========================================"

if ($Overall -eq "PASS") {
    exit 0
}
if ($Overall -eq "FAIL") {
    exit 1
}
exit 2
