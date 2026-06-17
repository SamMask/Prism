param(
    [string]$SmokeRoot = "build/desktop-portable-smoke"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedRepo = [System.IO.Path]::GetFullPath($repoRoot)
$resolvedSmoke = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $SmokeRoot))
if (!$resolvedSmoke.StartsWith($resolvedRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "SmokeRoot must resolve inside the repository: $resolvedSmoke"
}

function Get-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
    $listener.Start()
    try {
        return $listener.LocalEndpoint.Port
    }
    finally {
        $listener.Stop()
    }
}

$runRoot = Join-Path $resolvedSmoke ("run-" + [System.Guid]::NewGuid().ToString("N"))
$buildRoot = Join-Path $runRoot "package-build"
$extractRoot = Join-Path $runRoot "clean-unzip"
$dataDir = Join-Path $runRoot "external-data"
New-Item -ItemType Directory -Force -Path $buildRoot, $extractRoot, $dataDir | Out-Null

$packageName = "PrismPortableSmoke"
& (Join-Path $repoRoot "scripts\build_desktop_portable.ps1") -OutputDir ([System.IO.Path]::GetRelativePath($repoRoot, $buildRoot)) -PackageName $packageName
if ($LASTEXITCODE -ne 0) {
    throw "portable build failed"
}

$zipPath = Join-Path $buildRoot "$packageName.zip"
if (!(Test-Path $zipPath)) {
    throw "portable zip missing: $zipPath"
}
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot -Force

$packageDir = Join-Path $extractRoot $packageName
$guiExe = Join-Path $packageDir "Prism.exe"
$debugExe = Join-Path $packageDir "PrismDesktop-debug.exe"
foreach ($required in @($guiExe, $debugExe, (Join-Path $packageDir "README-PORTABLE.md"))) {
    if (!(Test-Path $required)) {
        throw "portable artifact missing: $required"
    }
}

$packageData = Get-ChildItem -LiteralPath $packageDir -Recurse -File -Include "*.db", "*.db-wal", "*.db-shm" -ErrorAction SilentlyContinue
if ($packageData) {
    throw "portable package contains database files: $($packageData.FullName -join ', ')"
}

$port = Get-FreePort
& $debugExe --desktop-shell-smoke --data-dir $dataDir --addr "127.0.0.1:$port"
if ($LASTEXITCODE -ne 0) {
    throw "portable desktop smoke failed"
}

$dbPath = Join-Path $dataDir "prism_desktop_dev.db"
$logPath = Join-Path $dataDir "logs\desktop-shell.log"
foreach ($required in @($dbPath, $logPath)) {
    if (!(Test-Path $required)) {
        throw "desktop smoke output missing: $required"
    }
}

$evidence = [ordered]@{
    package_dir = $packageDir
    zip_path = $zipPath
    data_dir = $dataDir
    db_path = $dbPath
    log_path = $logPath
    package_has_database_files = $false
    smoke_addr = "127.0.0.1:$port"
}
$evidencePath = Join-Path $runRoot "evidence.json"
$evidence | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $evidencePath -Encoding UTF8

Write-Host "Portable smoke evidence: $evidencePath"
