param(
    [string]$OutputDir = "build/desktop-portable",
    [string]$PackageName = "PrismDesktopPortable",
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$goShadow = Join-Path $repoRoot "go-shadow"
$embedDist = Join-Path $goShadow "web/dist"
$outRoot = Join-Path $repoRoot $OutputDir
$packageDir = Join-Path $outRoot $PackageName
$readmeSource = Join-Path $repoRoot "docs\desktop\README-PORTABLE.md"
$configSource = Join-Path $repoRoot "static\config"
$iconScript = Join-Path $PSScriptRoot "generate_prism_icon.ps1"
$resourceScript = Join-Path $PSScriptRoot "generate_windows_resource.ps1"

if (!(Test-Path $readmeSource)) {
    throw "Portable README not found: $readmeSource"
}
if (!(Test-Path $configSource)) {
    throw "Static config source not found: $configSource"
}
if (!(Test-Path $iconScript)) {
    throw "Icon generator not found: $iconScript"
}
if (!(Test-Path $resourceScript)) {
    throw "Windows resource generator not found: $resourceScript"
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

function Sync-EmbeddedFrontend {
    Push-Location $frontendDir
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "frontend build failed"
        }
    }
    finally {
        Pop-Location
    }

    if (Test-Path $embedDist) {
        Remove-Item -LiteralPath $embedDist -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $embedDist | Out-Null
    Copy-Item -Path (Join-Path $frontendDir "dist/*") -Destination $embedDist -Recurse -Force
}

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

Sync-EmbeddedFrontend

$iconTarget = Join-Path $packageDir "Prism.ico"
& $iconScript -OutputPath $iconTarget

$resourceTarget = Join-Path $goShadow "prism_windows_amd64.syso"
try {
    & $resourceScript -IconPath $iconTarget -OutputPath $resourceTarget -Arch "amd64"
    if ($LASTEXITCODE -ne 0) {
        throw "Windows resource generation failed"
    }

    Build-DesktopArtifact -Name "Prism.exe" -LdFlags @("-H=windowsgui", "-X", "main.desktopShellDefault=1")
    Build-DesktopArtifact -Name "PrismDesktop-debug.exe" -LdFlags @("-X", "main.desktopShellDefault=1")
}
finally {
    if (Test-Path -LiteralPath $resourceTarget) {
        Remove-Item -LiteralPath $resourceTarget -Force
    }
}

Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $packageDir "README-PORTABLE.md")
$configTarget = Join-Path $packageDir "static\config"
New-Item -ItemType Directory -Force -Path $configTarget | Out-Null
Copy-Item -LiteralPath (Join-Path $configSource "prompt_options.json") -Destination $configTarget -Force
Copy-Item -LiteralPath (Join-Path $configSource "wizard_options.json") -Destination $configTarget -Force

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
