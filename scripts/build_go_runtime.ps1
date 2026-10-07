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
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed (exit $LASTEXITCODE)" }
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
    if ($LASTEXITCODE -ne 0) { throw "go test failed (exit $LASTEXITCODE)" }
    go build -o (Join-Path $outDir "prism-go-runtime.exe") .
    if ($LASTEXITCODE -ne 0) { throw "go build (windows) failed (exit $LASTEXITCODE)" }

    $env:GOOS = "linux"
    $env:GOARCH = "arm64"
    $env:CGO_ENABLED = "0"
    go build -o (Join-Path $outDir "prism-go-runtime-linux-arm64") .
    if ($LASTEXITCODE -ne 0) { throw "go build (linux-arm64) failed (exit $LASTEXITCODE)" }
}
finally {
    Remove-Item Env:GOOS -ErrorAction SilentlyContinue
    Remove-Item Env:GOARCH -ErrorAction SilentlyContinue
    Remove-Item Env:CGO_ENABLED -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host "Built Go runtime artifacts in $outDir"
