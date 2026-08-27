param(
    [string]$RepoRoot = 'C:\Projetos\metao-gate',
    [string]$WorkRoot = 'C:\Projetos\metao-maint-bench',
    [string]$Output = 'C:\Projetos\metao-benchmark\a-vs-c-maintainability.json'
)

$ErrorActionPreference = 'Stop'

$cases = @(
    [ordered]@{ name='A-task1-identity'; language='rust'; branch='benchmark/maint-a-task1-identity'; base='ce6d2790ac5a5118f144a16788bfc68045602ce9'; subdir='experiments\rust-chassis-a'; testArgs=@('test','-p','metao-contracts','--test','maintenance_identity') },
    [ordered]@{ name='A-task2-rejection'; language='rust'; branch='benchmark/maint-a-task2-rejection'; base='ce6d2790ac5a5118f144a16788bfc68045602ce9'; subdir='experiments\rust-chassis-a'; testArgs=@('test','-p','metao-kernel','--test','maintenance_rejection') },
    [ordered]@{ name='A-task3-adapter-swap'; language='rust'; branch='benchmark/maint-a-task3-adapter-swap'; base='ce6d2790ac5a5118f144a16788bfc68045602ce9'; subdir='experiments\rust-chassis-a'; testArgs=@('test','-p','metao-testkit','--test','maintenance_adapter_swap') },
    [ordered]@{ name='C-task1-identity'; language='csharp'; branch='benchmark/maint-c-task1-identity'; base='ef641e94b1ad1cfb137d69a7a8c0648804f58033'; subdir='experiments\csharp-chassis-c' },
    [ordered]@{ name='C-task2-rejection'; language='csharp'; branch='benchmark/maint-c-task2-rejection'; base='ef641e94b1ad1cfb137d69a7a8c0648804f58033'; subdir='experiments\csharp-chassis-c' },
    [ordered]@{ name='C-task3-adapter-swap'; language='csharp'; branch='benchmark/maint-c-task3-adapter-swap'; base='ef641e94b1ad1cfb137d69a7a8c0648804f58033'; subdir='experiments\csharp-chassis-c' }
)

function Invoke-Checked([scriptblock]$Action, [string]$Label) {
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

function Measure-Checked([scriptblock]$Action, [string]$Label) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Action
    $exit = $LASTEXITCODE
    $sw.Stop()
    if ($exit -ne 0) { throw "$Label failed with exit code $exit" }
    return [int64]$sw.ElapsedMilliseconds
}

New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null
Push-Location $RepoRoot
try {
    Invoke-Checked { git fetch origin } 'git fetch origin'
}
finally { Pop-Location }

$results = @()
foreach ($case in $cases) {
    $worktree = Join-Path $WorkRoot $case.name
    if (Test-Path $worktree) {
        Push-Location $RepoRoot
        try { git worktree remove --force $worktree 2>$null | Out-Null } finally { Pop-Location }
        if (Test-Path $worktree) { Remove-Item -Recurse -Force $worktree }
    }

    Push-Location $RepoRoot
    try {
        Invoke-Checked { git worktree add --detach $worktree ("origin/" + $case.branch) } ("worktree " + $case.name)
    }
    finally { Pop-Location }

    Push-Location $worktree
    try {
        $head = (git rev-parse HEAD).Trim()
        $numstat = @(git diff --numstat $case.base $head)
        $filesChanged = 0
        $additions = 0
        $deletions = 0
        $paths = @()
        foreach ($line in $numstat) {
            if (-not $line) { continue }
            $parts = $line -split "`t"
            if ($parts.Count -lt 3) { continue }
            $filesChanged++
            if ($parts[0] -match '^\d+$') { $additions += [int]$parts[0] }
            if ($parts[1] -match '^\d+$') { $deletions += [int]$parts[1] }
            $paths += $parts[2]
        }

        $kernelTouched = @($paths | Where-Object { $_ -match 'metao-kernel|MetaO\.Kernel' }).Count -gt 0
        $contractTouched = @($paths | Where-Object { $_ -match 'metao-contracts|MetaO\.Contracts' }).Count -gt 0

        $projectDir = Join-Path $worktree $case.subdir
        Push-Location $projectDir
        try {
            if ($case.language -eq 'rust') {
                Invoke-Checked { cargo fetch | Out-Host } ("cargo fetch " + $case.name)
                $cycleMs = Measure-Checked { & cargo @($case.testArgs) | Out-Host } ("cargo focused test " + $case.name)
            }
            else {
                Invoke-Checked { dotnet restore MetaO.ChassisC.sln | Out-Host } ("dotnet restore " + $case.name)
                $cycleMs = Measure-Checked {
                    dotnet build MetaO.ChassisC.sln --no-restore -warnaserror | Out-Host
                    if ($LASTEXITCODE -ne 0) { throw "dotnet build failed with exit code $LASTEXITCODE" }
                    dotnet run --project tests/MetaO.TestKit/MetaO.TestKit.csproj --no-build | Out-Host
                    if ($LASTEXITCODE -ne 0) { throw "dotnet run failed with exit code $LASTEXITCODE" }
                } ("dotnet build+run " + $case.name)
            }
        }
        finally { Pop-Location }

        $results += [ordered]@{
            name = $case.name
            language = $case.language
            branch = $case.branch
            base = $case.base
            head = $head
            files_changed = $filesChanged
            additions = $additions
            deletions = $deletions
            total_changed_lines = $additions + $deletions
            kernel_touched = $kernelTouched
            contract_touched = $contractTouched
            compile_test_cycle_ms = $cycleMs
            paths = $paths
        }
    }
    finally { Pop-Location }
}

$result = [ordered]@{
    schema = 'metao.chassis-maintainability-tiebreak.v1'
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    results = $results
}

$dir = Split-Path -Parent $Output
if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding utf8
$result | ConvertTo-Json -Depth 8
