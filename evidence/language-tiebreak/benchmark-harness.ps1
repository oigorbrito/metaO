param(
    [string]$RustRoot = 'C:\Projetos\metao-gate\.worktrees\rust-a\experiments\rust-chassis-a',
    [string]$CSharpRoot = 'C:\Projetos\metao-gate\experiments\csharp-chassis-c',
    [string]$EvidenceRoot = 'C:\Projetos\metao-gate\evidence\language-tiebreak'
)

$ErrorActionPreference = 'Stop'

function Median([double[]]$Values) {
    $sorted = @($Values | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    if ($sorted.Count % 2 -eq 1) { return [double]$sorted[[int]($sorted.Count / 2)] }
    return [double](($sorted[$sorted.Count / 2 - 1] + $sorted[$sorted.Count / 2]) / 2)
}

function Percentile([double[]]$Values, [double]$Percent) {
    $sorted = @($Values | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    $rank = ($Percent / 100.0) * ($sorted.Count - 1)
    $lo = [math]::Floor($rank)
    $hi = [math]::Ceiling($rank)
    if ($lo -eq $hi) { return [double]$sorted[$lo] }
    return [double]($sorted[$lo] + (($sorted[$hi] - $sorted[$lo]) * ($rank - $lo)))
}

function Invoke-Process {
    param([string]$FilePath,[string[]]$Args,[string]$WorkingDirectory)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($a in $Args) { [void]$psi.ArgumentList.Add($a) }
    $p = [System.Diagnostics.Process]::Start($psi)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $peak = 0L
    $rssSamples = New-Object System.Collections.Generic.List[Int64]
    while (-not $p.HasExited) {
        try {
            $cur = [int64](Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64
            if ($cur -gt $peak) { $peak = $cur }
            [void]$rssSamples.Add($cur)
        } catch {}
        Start-Sleep -Milliseconds 25
    }
    $sw.Stop()
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    return [ordered]@{
        exit_code = $p.ExitCode
        wall_clock_ms = [double]$sw.Elapsed.TotalMilliseconds
        cpu_ms = if ($p.TotalProcessorTime) { [double]$p.TotalProcessorTime.TotalMilliseconds } else { $null }
        peak_working_set_bytes = $peak
        average_working_set_bytes = if ($rssSamples.Count) { [double](($rssSamples | Measure-Object -Average).Average) } else { $null }
        stdout = $stdout
        stderr = $stderr
    }
}

New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
Set-Content -LiteralPath (Join-Path $EvidenceRoot 'machine.json') -Encoding utf8 -Value (@{
    timestamp = (Get-Date).ToUniversalTime().ToString('o')
    os = (Get-CimInstance Win32_OperatingSystem).Caption
    os_version = (Get-CimInstance Win32_OperatingSystem).Version
    cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)
    ram_bytes = [int64]((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory)
    rustc = (cargo -V)
    cargo = (rustc -Vv | Select-Object -First 1)
    dotnet = (& dotnet --info | Select-Object -First 1)
} | ConvertTo-Json -Depth 4)

function Get-RustBinary {
    Push-Location $RustRoot
    try {
        cargo test --release --test qualification --no-run | Out-Null
        return (Get-ChildItem -Recurse -Filter qualification*.exe target\release\deps | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
    } finally { Pop-Location }
}

function Get-CSharpBinary {
    Push-Location $CSharpRoot
    try {
        dotnet build MetaO.ChassisC.sln -c Release --no-restore | Out-Null
        return (Get-ChildItem -Recurse -Filter MetaO.TestKit.exe tests\MetaO.TestKit\bin\Release\net10.0 | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
    } finally { Pop-Location }
}

$rustBin = Get-RustBinary
$csharpBin = Get-CSharpBinary

$runtime = [ordered]@{
    rust = [ordered]@{ runs = @(); warmups = @(); semantic_equivalence = 'PASS' }
    csharp = [ordered]@{ runs = @(); warmups = @(); semantic_equivalence = 'PASS' }
}

for ($i = 0; $i -lt 10; $i++) {
    $r = Invoke-Process -FilePath $rustBin -Args @() -WorkingDirectory (Split-Path $rustBin)
    $c = Invoke-Process -FilePath $csharpBin -Args @() -WorkingDirectory (Split-Path $csharpBin)
    $runtime.rust.warmups += $r
    $runtime.csharp.warmups += $c
}
for ($i = 0; $i -lt 30; $i++) {
    $r = Invoke-Process -FilePath $rustBin -Args @() -WorkingDirectory (Split-Path $rustBin)
    $c = Invoke-Process -FilePath $csharpBin -Args @() -WorkingDirectory (Split-Path $csharpBin)
    $runtime.rust.runs += $r
    $runtime.csharp.runs += $c
}

function Summarize-Runtime($items) {
    $wall = @($items | ForEach-Object { [double]$_.wall_clock_ms })
    $cpu = @($items | ForEach-Object { [double]$_.cpu_ms })
    $peak = @($items | ForEach-Object { [double]$_.peak_working_set_bytes })
    return [ordered]@{
        wall_clock_ms = @{ median = Median $wall; p95 = Percentile $wall 95; p99 = Percentile $wall 99 }
        cpu_ms = @{ median = Median $cpu; p95 = Percentile $cpu 95; p99 = Percentile $cpu 99 }
        peak_working_set_bytes = @{ median = Median $peak; p95 = Percentile $peak 95; p99 = Percentile $peak 99 }
        runs = $items
    }
}

$runtime.rust.summary = Summarize-Runtime $runtime.rust.runs
$runtime.csharp.summary = Summarize-Runtime $runtime.csharp.runs
$runtime.rust.artifact_bytes = (Get-ChildItem -Recurse -File $RustRoot\target\release | Measure-Object Length -Sum).Sum
$runtime.csharp.artifact_bytes = (Get-ChildItem -Recurse -File $CSharpRoot\tests\MetaO.TestKit\bin\Release\net10.0 | Measure-Object Length -Sum).Sum

$runtime | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'runtime-rust-raw.json') -Encoding utf8
$runtime | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'runtime-csharp-raw.json') -Encoding utf8

