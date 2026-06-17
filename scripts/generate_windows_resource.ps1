param(
    [Parameter(Mandatory=$true)]
    [string]$IconPath,
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    [ValidateSet("386", "amd64", "arm", "arm64")]
    [string]$Arch = "amd64"
)

$ErrorActionPreference = "Stop"

$resolvedIcon = [System.IO.Path]::GetFullPath($IconPath)
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)

if (!(Test-Path -LiteralPath $resolvedIcon)) {
    throw "Icon file not found: $resolvedIcon"
}

$outputDir = [System.IO.Path]::GetDirectoryName($resolvedOutput)
if ($outputDir) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

& go run github.com/akavel/rsrc@v0.10.2 -arch $Arch -ico $resolvedIcon -o $resolvedOutput
if ($LASTEXITCODE -ne 0) {
    throw "Windows resource generation failed"
}

Write-Host "Generated Windows resource: $resolvedOutput"
