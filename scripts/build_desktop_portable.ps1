param(
    [string]$OutputDir = "build/desktop-portable",
    [string]$PackageName = "PrismDesktopPortable",
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$goShadow = Join-Path $repoRoot "go-shadow"
$outRoot = Join-Path $repoRoot $OutputDir
$packageDir = Join-Path $outRoot $PackageName
$readmeSource = Join-Path $repoRoot "docs\desktop\README-PORTABLE.md"

if (!(Test-Path $readmeSource)) {
    throw "Portable README not found: $readmeSource"
}

$resolvedRepo = [System.IO.Path]::GetFullPath($repoRoot)
$resolvedOut = [System.IO.Path]::GetFullPath($outRoot)
if (!$resolvedOut.StartsWith($resolvedRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDir must resolve inside the repository: $resolvedOut"
}

New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
if (Test-Path $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

function Build-DesktopArtifact {
    param(
        [string]$Name,
        [string[]]$LdFlags
    )

    $output = Join-Path $packageDir $Name
    Push-Location $goShadow
    try {
        $args = @("build", "-o", $output, "-ldflags", ($LdFlags -join " "), ".")
        & go @args
        if ($LASTEXITCODE -ne 0) {
            throw "go build failed for $Name"
        }
    }
    finally {
        Pop-Location
    }
}

Build-DesktopArtifact -Name "Prism.exe" -LdFlags @("-H=windowsgui", "-X", "main.desktopShellDefault=1")
Build-DesktopArtifact -Name "PrismDesktop-debug.exe" -LdFlags @("-X", "main.desktopShellDefault=1")
Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $packageDir "README-PORTABLE.md")

$forbiddenData = Get-ChildItem -LiteralPath $packageDir -Recurse -File -Include "*.db", "*.db-wal", "*.db-shm" -ErrorAction SilentlyContinue
if ($forbiddenData) {
    throw "Portable package contains database files: $($forbiddenData.FullName -join ', ')"
}

if (!$NoZip) {
    $zipPath = Join-Path $outRoot "$PackageName.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -Force
    Write-Host "Portable package zip: $zipPath"
}

Write-Host "Portable package folder: $packageDir"
