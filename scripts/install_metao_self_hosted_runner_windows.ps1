$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Repo = if ($env:METAO_GITHUB_REPOSITORY) { $env:METAO_GITHUB_REPOSITORY } else { 'oigorbrito/metaO' }
$RunnerLabel = 'metao-project-pilot'
$RunnerName = if ($env:METAO_RUNNER_NAME) { $env:METAO_RUNNER_NAME } else { "metao-project-pilot-$env:COMPUTERNAME" }
$InstallDir = if ($env:METAO_RUNNER_INSTALL_DIR) { $env:METAO_RUNNER_INSTALL_DIR } else { Join-Path $env:ProgramData 'metaO\actions-runner-metao-project-pilot' }
$RunnerVersion = if ($env:METAO_ACTIONS_RUNNER_VERSION) { $env:METAO_ACTIONS_RUNNER_VERSION } else { 'v2.337.0' }

function Fail([string]$Message) {
    throw $Message
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "required command not found: $Name"
    }
}

function Get-RemoteRunner {
    $raw = & gh api --paginate --slurp "repos/$Repo/actions/runners?per_page=100" 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($raw -join "`n"))) { return $null }
    $pages = ($raw -join "`n") | ConvertFrom-Json
    $runners = @()
    foreach ($page in @($pages)) { $runners += @($page.runners) }
    return $runners | Where-Object { $_.name -eq $RunnerName } | Select-Object -First 1
}

if ($Repo -ne 'oigorbrito/metaO') { Fail 'METAO_GITHUB_REPOSITORY must be exactly oigorbrito/metaO' }
if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) { Fail 'runner host and PowerShell process must be Windows x64' }
if ($env:PROCESSOR_ARCHITECTURE -notmatch '^(AMD64|x86_64)$') { Fail 'runner host must be Windows x64' }
if ($RunnerName -notmatch '^[A-Za-z0-9._-]+$') { Fail 'METAO_RUNNER_NAME contains unsupported characters' }
if (-not [System.IO.Path]::IsPathRooted($InstallDir)) { Fail 'METAO_RUNNER_INSTALL_DIR must be absolute' }
if ($RunnerVersion -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { Fail 'METAO_ACTIONS_RUNNER_VERSION must be an exact version such as v2.337.0' }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Fail 'run PowerShell as Administrator so the runner service can be installed'
}

foreach ($command in @('gh','git','ssh','scp')) { Require-Command $command }
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { Fail 'GitHub CLI is not authenticated; run gh auth login first' }

$remoteRunner = Get-RemoteRunner
$runnerMarker = Join-Path $InstallDir '.runner'
$configCmd = Join-Path $InstallDir 'config.cmd'
$runCmd = Join-Path $InstallDir 'run.cmd'

if (Test-Path $runnerMarker) {
    if ($null -eq $remoteRunner) { Fail 'local runner is configured but no matching GitHub runner registration exists' }
    if (-not (Test-Path $configCmd) -or -not (Test-Path $runCmd)) { Fail 'local runner configuration is incomplete' }
    $labels = @($remoteRunner.labels | ForEach-Object { $_.name.ToLowerInvariant() })
    foreach ($required in @('self-hosted','windows','x64',$RunnerLabel)) {
        if ($labels -notcontains $required.ToLowerInvariant()) { Fail "registered runner is missing required label: $required" }
    }
    [ordered]@{
        installer='PASS'; repository=$Repo; runner_name=$RunnerName; runner_label=$RunnerLabel;
        already_configured=$true; runner_version='existing'; registration_token_emitted=$false;
        credentials_emitted=$false; pilot_operational_pass=$false
    } | ConvertTo-Json -Compress
    exit 0
}

if ($null -ne $remoteRunner) { Fail "a GitHub runner named $RunnerName already exists but this install directory is not configured" }

if (Test-Path $InstallDir) {
    if (@(Get-ChildItem -Force -LiteralPath $InstallDir).Count -ne 0) { Fail 'install directory must be empty for first installation' }
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$release = (& gh api "repos/actions/runner/releases/tags/$RunnerVersion") | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { Fail "unable to resolve actions/runner release $RunnerVersion" }
$versionNoV = $RunnerVersion.Substring(1)
$expectedName = "actions-runner-win-x64-$versionNoV.zip"
$asset = @($release.assets | Where-Object { $_.name -eq $expectedName })
if ($asset.Count -ne 1) { Fail "expected exactly one official asset named $expectedName" }
$asset = $asset[0]
if (-not $asset.digest -or -not $asset.digest.StartsWith('sha256:')) { Fail 'runner release asset does not expose a sha256 digest' }
$expectedSha = $asset.digest.Substring(7).ToLowerInvariant()
if ($expectedSha -notmatch '^[0-9a-f]{64}$') { Fail 'runner release asset sha256 digest is invalid' }

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("metao-actions-runner-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir | Out-Null
$archive = Join-Path $tempDir $expectedName
$registrationToken = $null
try {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive -UseBasicParsing
    $actualSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
    if ($actualSha -ne $expectedSha) { Fail 'GitHub Actions runner archive checksum verification failed' }
    Expand-Archive -LiteralPath $archive -DestinationPath $InstallDir -Force

    $registrationToken = (& gh api --method POST "repos/$Repo/actions/runners/registration-token" --jq .token).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($registrationToken)) { Fail 'GitHub did not return a runner registration token' }

    Push-Location $InstallDir
    try {
        & .\config.cmd --unattended --url "https://github.com/$Repo" --token $registrationToken --name $RunnerName --labels $RunnerLabel --work _work --runasservice
        if ($LASTEXITCODE -ne 0) { Fail 'runner config.cmd failed' }
    } finally {
        Pop-Location
    }
    $registrationToken = $null

    if (-not (Test-Path $runnerMarker)) { Fail 'runner configuration did not create .runner' }
    $remoteRunner = Get-RemoteRunner
    if ($null -eq $remoteRunner) { Fail 'runner configuration completed but GitHub registry does not show the runner' }
    $labels = @($remoteRunner.labels | ForEach-Object { $_.name.ToLowerInvariant() })
    foreach ($required in @('self-hosted','windows','x64',$RunnerLabel)) {
        if ($labels -notcontains $required.ToLowerInvariant()) { Fail "new runner registration is missing required label: $required" }
    }

    [ordered]@{
        installer='PASS'; repository=$Repo; runner_name=$RunnerName; runner_label=$RunnerLabel;
        already_configured=$false; runner_version=$RunnerVersion; runner_asset_sha256=$expectedSha;
        registration_token_persisted=$false; credentials_emitted=$false; pilot_operational_pass=$false
    } | ConvertTo-Json -Compress
} finally {
    $registrationToken = $null
    if (Test-Path $tempDir) { Remove-Item -Recurse -Force -LiteralPath $tempDir }
}
