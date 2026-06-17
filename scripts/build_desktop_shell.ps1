param(
    [string]$OutputDir = "build/desktop-shell",
    [ValidateSet("Debug", "GUI", "Both")]
    [string]$Mode = "Both"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$goShadow = Join-Path $repoRoot "go-shadow"
$embedDist = Join-Path $goShadow "web/dist"
$outRoot = Join-Path $repoRoot $OutputDir
$configSource = Join-Path $repoRoot "static\config"
$iconScript = Join-Path $PSScriptRoot "generate_prism_icon.ps1"
$resourceScript = Join-Path $PSScriptRoot "generate_windows_resource.ps1"
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null

if (!(Test-Path $configSource)) {
    throw "Static config source not found: $configSource"
}
if (!(Test-Path $iconScript)) {
    throw "Icon generator not found: $iconScript"
}
if (!(Test-Path $resourceScript)) {
    throw "Windows resource generator not found: $resourceScript"
}

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

function Build-DesktopShell {
    param(
        [string]$Name,
        [string[]]$LdFlags
    )

    $output = Join-Path $outRoot $Name
    Push-Location $goShadow
    try {
        $args = @("build", "-o", $output)
        if ($LdFlags.Count -gt 0) {
            $args += @("-ldflags", ($LdFlags -join " "))
        }
        $args += @(".")
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

$iconTarget = Join-Path $outRoot "Prism.ico"
& $iconScript -OutputPath $iconTarget

$resourceTarget = Join-Path $goShadow "prism_windows_amd64.syso"
try {
    & $resourceScript -IconPath $iconTarget -OutputPath $resourceTarget -Arch "amd64"
    if ($LASTEXITCODE -ne 0) {
        throw "Windows resource generation failed"
    }

    if ($Mode -eq "Debug" -or $Mode -eq "Both") {
        Build-DesktopShell -Name "PrismDesktop-debug.exe" -LdFlags @("-X", "main.desktopShellDefault=1")
    }

    if ($Mode -eq "GUI" -or $Mode -eq "Both") {
        Build-DesktopShell -Name "Prism.exe" -LdFlags @("-H=windowsgui", "-X", "main.desktopShellDefault=1")
    }
}
finally {
    if (Test-Path -LiteralPath $resourceTarget) {
        Remove-Item -LiteralPath $resourceTarget -Force
    }
}

$configTarget = Join-Path $outRoot "static\config"
New-Item -ItemType Directory -Force -Path $configTarget | Out-Null
Copy-Item -LiteralPath (Join-Path $configSource "prompt_options.json") -Destination $configTarget -Force
Copy-Item -LiteralPath (Join-Path $configSource "wizard_options.json") -Destination $configTarget -Force

Write-Host "Desktop shell build output: $outRoot"
