param(
    [string]$BuildOutputDir = "build/go-runtime",
    [string]$Addr = "127.0.0.1:5004",
    [string]$DataDir = "",
    [string]$DbPath = "knowledge.db",
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = $repoRoot
}

function Resolve-RepoPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
}

function Resolve-DataPath([string]$DataRoot, [string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $DataRoot $PathValue))
}

$outDir = Resolve-RepoPath $BuildOutputDir
$artifact = Join-Path $outDir "prism-go-runtime.exe"
if ($Build -or -not (Test-Path $artifact)) {
    & (Join-Path $repoRoot "scripts/build_go_runtime.ps1") -OutputDir $BuildOutputDir
}
if (-not (Test-Path $artifact)) {
    throw "Missing Go primary runtime artifact: $artifact"
}

$dataRoot = Resolve-RepoPath $DataDir
$dbFullPath = Resolve-DataPath $dataRoot $DbPath
if (-not (Test-Path $dataRoot)) {
    New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
}

foreach ($key in @("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "FLASK_APP")) {
    Remove-Item "Env:$key" -ErrorAction SilentlyContinue
}

$env:PRISM_GO_ALLOW_PROD_DB = "1"
$env:PRISM_GO_ALLOW_PROD_UPLOADS = "1"
$env:PRISM_GO_ALLOW_PROD_IMPORT_EXPORT = "1"
$env:PRISM_GO_ALLOW_PROD_SERVER_SYSTEM = "1"

$runtimeArgs = @(
    "--db", $dbFullPath,
    "--data-dir", $dataRoot,
    "--addr", $Addr,
    "--enable-tag-write",
    "--enable-category-write",
    "--enable-notes-write",
    "--enable-attachment-text-read",
    "--enable-attachment-raw-read",
    "--enable-attachment-write",
    "--enable-upload-write",
    "--enable-thumbnail-write",
    "--enable-upload-url-write",
    "--enable-upload-delete",
    "--enable-media-cleanup",
    "--enable-import-export",
    "--enable-server-system"
)

Write-Host "Starting Prism Go primary runtime at http://$Addr"
Write-Host "Data dir: $dataRoot"
Write-Host "Database: $dbFullPath"
& $artifact @runtimeArgs
