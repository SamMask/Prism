param(
    [string]$OutputDir = "build/desktop-shell",
    [ValidateSet("Debug", "GUI", "Both")]
    [string]$Mode = "Both"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$goShadow = Join-Path $repoRoot "go-shadow"
$outRoot = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null

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
    }
    finally {
        Pop-Location
    }
}

if ($Mode -eq "Debug" -or $Mode -eq "Both") {
    Build-DesktopShell -Name "PrismDesktop-debug.exe" -LdFlags @("-X", "main.desktopShellDefault=1")
}

if ($Mode -eq "GUI" -or $Mode -eq "Both") {
    Build-DesktopShell -Name "Prism.exe" -LdFlags @("-H=windowsgui", "-X", "main.desktopShellDefault=1")
}

Write-Host "Desktop shell build output: $outRoot"
