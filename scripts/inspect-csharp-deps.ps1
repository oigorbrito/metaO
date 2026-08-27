param(
    [string]$CSharpRoot = 'C:\Projetos\metao-csharp-c\experiments\csharp-chassis-c'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path (Join-Path $CSharpRoot 'MetaO.ChassisC.sln'))) {
    throw "CSharpRoot does not contain MetaO.ChassisC.sln: $CSharpRoot"
}

$projects = @()
$totalPackages = 0
$totalProjects = 0

foreach ($file in @(Get-ChildItem -LiteralPath $CSharpRoot -Recurse -Filter *.csproj -File | Sort-Object FullName)) {
    [xml]$xml = Get-Content -LiteralPath $file.FullName -Raw
    $packageNodes = @($xml.SelectNodes('//PackageReference'))
    $projectNodes = @($xml.SelectNodes('//ProjectReference'))

    $packages = @($packageNodes | ForEach-Object {
        if ($_.Include) { [string]$_.Include } elseif ($_.Update) { [string]$_.Update } else { '<unnamed>' }
    })
    $refs = @($projectNodes | ForEach-Object { [string]$_.Include })

    $totalPackages += $packages.Count
    $totalProjects += $refs.Count

    $projects += [ordered]@{
        project = $file.FullName.Substring($CSharpRoot.Length).TrimStart('\')
        package_references = $packages
        project_references = $refs
    }
}

[ordered]@{
    schema = 'metao.csharp-dependency-inventory.v1'
    project_count = $projects.Count
    package_reference_count = $totalPackages
    project_reference_count = $totalProjects
    projects = $projects
} | ConvertTo-Json -Depth 8
