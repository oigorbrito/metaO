param(
    [string]$RustRoot = 'C:\Projetos\metao-rust-a\experiments\rust-chassis-a',
    [string]$CSharpRoot = 'C:\Projetos\metao-csharp-c\experiments\csharp-chassis-c',
    [string]$Output = "$PSScriptRoot\..\artifacts\a-vs-c-tiebreak.json",
    [int]$Samples = 5
)

$ErrorActionPreference = 'Stop'

function Measure-Milliseconds([scriptblock]$Action) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Action
    $sw.Stop()
    return [int64]$sw.ElapsedMilliseconds
}

function Median([long[]]$Values) {
    $sorted = @($Values | Sort-Object)
    $count = $sorted.Count
    if ($count -eq 0) { return $null }
    if ($count % 2 -eq 1) { return [int64]$sorted[[int]($count / 2)] }
    return [int64](($sorted[$count / 2 - 1] + $sorted[$count / 2]) / 2)
}

function Directory-Bytes([string]$Path) {
    if (-not (Test-Path $Path)) { return 0 }
    return [int64]((Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)
}

function Unique-Line-Count([string[]]$Lines) {
    return @($Lines | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() } | Sort-Object -Unique).Count
}

if (-not (Test-Path (Join-Path $RustRoot 'Cargo.toml'))) {
    throw "RustRoot does not contain Cargo.toml: $RustRoot"
}
if (-not (Test-Path (Join-Path $CSharpRoot 'MetaO.ChassisC.sln'))) {
    throw "CSharpRoot does not contain MetaO.ChassisC.sln: $CSharpRoot"
}

$rustClean = @()
$rustIncremental = @()
$csharpClean = @()
$csharpIncremental = @()

Push-Location $RustRoot
try {
    for ($i = 1; $i -le $Samples; $i++) {
        cargo clean | Out-Null
        $rustClean += Measure-Milliseconds { cargo build --workspace --all-targets | Out-Host }
    }
    for ($i = 1; $i -le $Samples; $i++) {
        $rustIncremental += Measure-Milliseconds { cargo build --workspace --all-targets | Out-Host }
    }
    $rustWorkspaceTree = @(cargo tree 2>&1)
    $rustKernelTree = @(cargo tree -p metao-kernel 2>&1)
    $rustTargetBytes = Directory-Bytes (Join-Path $RustRoot 'target')
}
finally { Pop-Location }

Push-Location $CSharpRoot
try {
    dotnet restore MetaO.ChassisC.sln | Out-Host
    for ($i = 1; $i -le $Samples; $i++) {
        dotnet clean MetaO.ChassisC.sln | Out-Null
        $csharpClean += Measure-Milliseconds { dotnet build MetaO.ChassisC.sln --no-restore -warnaserror | Out-Host }
    }
    for ($i = 1; $i -le $Samples; $i++) {
        $csharpIncremental += Measure-Milliseconds { dotnet build MetaO.ChassisC.sln --no-restore -warnaserror | Out-Host }
    }
    $csharpArtifactBytes = [int64]((Get-ChildItem -LiteralPath $CSharpRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\(bin|obj)\\' } |
        Measure-Object Length -Sum).Sum)

    $csprojFiles = @(Get-ChildItem -LiteralPath $CSharpRoot -Recurse -Filter *.csproj -File)
    $packageReferences = 0
    $projectReferences = 0
    foreach ($file in $csprojFiles) {
        [xml]$xml = Get-Content -LiteralPath $file.FullName
        $packageReferences += @($xml.Project.ItemGroup.PackageReference).Count
        $projectReferences += @($xml.Project.ItemGroup.ProjectReference).Count
    }
}
finally { Pop-Location }

$result = [ordered]@{
    schema = 'metao.chassis-tiebreak.v1'
    samples = $Samples
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    rust = [ordered]@{
        clean_build_ms = $rustClean
        clean_build_median_ms = Median $rustClean
        incremental_build_ms = $rustIncremental
        incremental_build_median_ms = Median $rustIncremental
        artifact_bytes = $rustTargetBytes
        workspace_dependency_unique_lines = Unique-Line-Count $rustWorkspaceTree
        kernel_dependency_unique_lines = Unique-Line-Count $rustKernelTree
    }
    csharp = [ordered]@{
        clean_build_ms = $csharpClean
        clean_build_median_ms = Median $csharpClean
        incremental_build_ms = $csharpIncremental
        incremental_build_median_ms = Median $csharpIncremental
        artifact_bytes = $csharpArtifactBytes
        package_reference_count = $packageReferences
        project_reference_count = $projectReferences
    }
}

$dir = Split-Path -Parent $Output
if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Output -Encoding utf8
$result | ConvertTo-Json -Depth 6
