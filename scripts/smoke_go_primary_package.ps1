param(
    [string]$BuildOutputDir = "build/go-runtime",
    [string]$SmokeRoot = "build/go-primary-package-smoke/windows",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

function Resolve-RepoPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
}

function Assert-UnderBuild([string]$PathValue) {
    $buildRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "build"))
    $fullPath = [System.IO.Path]::GetFullPath($PathValue)
    if (-not ($fullPath.StartsWith($buildRoot + [System.IO.Path]::DirectorySeparatorChar) -or $fullPath -eq $buildRoot)) {
        throw "Refusing to clean package smoke path outside repo build/: $fullPath"
    }
}

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
    try {
        $listener.Start()
        return $listener.LocalEndpoint.Port
    }
    finally {
        $listener.Stop()
    }
}

function Wait-ForGoRuntime([string]$BaseUrl, $Process) {
    $deadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "Go package smoke runtime exited before health check. ExitCode=$($Process.ExitCode)"
        }
        try {
            $response = Invoke-WebRequest -Uri "$BaseUrl/healthz" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "Go package smoke runtime did not become healthy at $BaseUrl"
}

function Start-GoArtifact([string]$Artifact, [string[]]$RuntimeArgs, [string]$LogDir) {
    $stdout = Join-Path $LogDir "runtime.stdout.log"
    $stderr = Join-Path $LogDir "runtime.stderr.log"
    $argLine = ($RuntimeArgs | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join " "
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Artifact
    $psi.Arguments = $argLine
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($key in @("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "FLASK_APP")) {
        [void]$psi.Environment.Remove($key)
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    [void]$process.Start()
    return [pscustomobject]@{
        Process = $process
        Stdout = $stdout
        Stderr = $stderr
    }
}

function Stop-GoArtifact($Handle) {
    if ($null -eq $Handle) {
        return
    }
    $process = $Handle.Process
    if (-not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
    }
    $stdoutText = $process.StandardOutput.ReadToEnd()
    $stderrText = $process.StandardError.ReadToEnd()
    Set-Content -Path $Handle.Stdout -Value $stdoutText -Encoding UTF8
    Set-Content -Path $Handle.Stderr -Value $stderrText -Encoding UTF8
}

if (-not $SkipBuild) {
    & (Join-Path $repoRoot "scripts/build_go_runtime.ps1") -OutputDir $BuildOutputDir
}

$outDir = Resolve-RepoPath $BuildOutputDir
$artifact = Join-Path $outDir "prism-go-runtime.exe"
$linuxArm64Artifact = Join-Path $outDir "prism-go-runtime-linux-arm64"
if (-not (Test-Path $artifact)) {
    throw "Missing Windows Go package artifact: $artifact"
}
if (-not (Test-Path $linuxArm64Artifact)) {
    throw "Missing linux/arm64 Go package artifact: $linuxArm64Artifact"
}

$smokeRootPath = Resolve-RepoPath $SmokeRoot
Assert-UnderBuild $smokeRootPath
if (Test-Path $smokeRootPath) {
    Remove-Item -LiteralPath $smokeRootPath -Recurse -Force
}

$dataDir = Join-Path $smokeRootPath "data"
$logsDir = Join-Path $smokeRootPath "logs"
$evidenceDir = Join-Path $smokeRootPath "evidence"
foreach ($dir in @($dataDir, $logsDir, $evidenceDir, (Join-Path $dataDir "fresh"))) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$dbPath = Join-Path $dataDir "fresh/prism_windows_package_smoke_dev.db"
$port = Get-FreeTcpPort
$baseUrl = "http://127.0.0.1:$port"
$workflowEvidencePath = Join-Path $evidenceDir "full-workflow.json"
$runtime = $null
try {
    $runtime = Start-GoArtifact $artifact @(
        "--db", $dbPath,
        "--addr", "127.0.0.1:$port",
        "--data-dir", $dataDir,
        "--enable-notes-write",
        "--enable-upload-write",
        "--enable-thumbnail-write",
        "--enable-upload-url-write",
        "--enable-upload-delete",
        "--enable-media-cleanup",
        "--enable-import-export",
        "--enable-server-system"
    ) $logsDir
    Wait-ForGoRuntime $baseUrl $runtime.Process
    & python (Join-Path $repoRoot "scripts/go_primary_full_workflow_smoke.py") `
        --base-url $baseUrl `
        --label "t039-windows-package" `
        --evidence-out $workflowEvidencePath
    if ($LASTEXITCODE -ne 0) {
        throw "Go primary full workflow package smoke failed with exit code $LASTEXITCODE"
    }
}
finally {
    Stop-GoArtifact $runtime
}

$workflowEvidence = Get-Content -Raw $workflowEvidencePath | ConvertFrom-Json
$packageEvidence = [ordered]@{
    status = "passed"
    task_id = "T039"
    artifact = $artifact
    linux_arm64_artifact = $linuxArm64Artifact
    smoke_root = $smokeRootPath
    data_dir = $dataDir
    db_path = $dbPath
    db_source = "fresh Go-created DB under package smoke data dir"
    runtime_dependency_boundary = @{
        python_venv_required_by_artifact = $false
        flask_required_by_artifact = $false
        pyinstaller_required_by_artifact = $false
        smoke_harness = "scripts/go_primary_full_workflow_smoke.py uses stdlib HTTP only"
        runtime_env_removed = @("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "FLASK_APP")
    }
    workflow_smoke = $workflowEvidence
    release_boundary = @{
        pi_deployed = $false
        caddy_changed = $false
        systemd_changed = $false
        frontend_default_changed = $false
        production_db_mutated = $false
    }
}
$evidencePath = Join-Path $smokeRootPath "evidence.json"
$packageEvidence | ConvertTo-Json -Depth 12 | Set-Content -Path $evidencePath -Encoding UTF8
Write-Host "Go primary Windows package smoke passed. Evidence: $evidencePath"
