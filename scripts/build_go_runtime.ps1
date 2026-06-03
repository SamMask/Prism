param(
    [string]$OutputDir = "build/go-runtime"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $repoRoot "frontend"
$goDir = Join-Path $repoRoot "go-shadow"
$embedDist = Join-Path $goDir "web/dist"
$outDir = Join-Path $repoRoot $OutputDir

Push-Location $frontendDir
try {
    npm run build
}
finally {
    Pop-Location
}

if (Test-Path $embedDist) {
    Remove-Item -LiteralPath $embedDist -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $embedDist | Out-Null
Copy-Item -Path (Join-Path $frontendDir "dist/*") -Destination $embedDist -Recurse -Force

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Push-Location $goDir
try {
    go test ./...
    go build -o (Join-Path $outDir "prism-go-runtime.exe") .

    $env:GOOS = "linux"
    $env:GOARCH = "arm64"
    $env:CGO_ENABLED = "0"
    go build -o (Join-Path $outDir "prism-go-runtime-linux-arm64") .
}
finally {
    Remove-Item Env:GOOS -ErrorAction SilentlyContinue
    Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
    Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host "Built Go runtime artifacts in $outDir"
