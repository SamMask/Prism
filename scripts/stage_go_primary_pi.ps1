param(
    [string]$HostAlias = "PI5Mask24",
    [string]$RemoteRoot = "/home/mask070924/prism",
    [string]$StageName = "go-primary-staging",
    [string]$RemoteUser = "mask070924",
    [int]$Port = 5003,
    [string]$BuildOutputDir = "build/go-runtime",
    [string]$LocalEvidenceRoot = "build/go-primary-staging/pi",
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
        throw "Refusing to clean staging evidence path outside repo build/: $fullPath"
    }
}

function Quote-RemoteArg([string]$Value) {
    if ($Value.Contains("'")) {
        throw "Remote argument contains a single quote and cannot be safely quoted: $Value"
    }
    return "'" + $Value + "'"
}

function Invoke-RemoteBash([string]$Description, [string]$Script, [string[]]$RemoteArgs) {
    $scriptName = "prism-go-primary-stage-" + ([System.Guid]::NewGuid().ToString("N")) + ".sh"
    $localTemp = Join-Path ([System.IO.Path]::GetTempPath()) $scriptName
    $remoteTemp = "/tmp/$scriptName"
    [System.IO.File]::WriteAllText($localTemp, $Script, [System.Text.UTF8Encoding]::new($false))
    try {
        & scp $localTemp "${HostAlias}:$remoteTemp"
        if ($LASTEXITCODE -ne 0) {
            throw "$Description could not copy remote script to $HostAlias"
        }
        $quotedArgs = ($RemoteArgs | ForEach-Object { Quote-RemoteArg $_ }) -join " "
        & ssh $HostAlias "chmod +x '$remoteTemp' && '$remoteTemp' $quotedArgs"
        if ($LASTEXITCODE -ne 0) {
            throw "$Description failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Remove-Item -LiteralPath $localTemp -Force -ErrorAction SilentlyContinue
        & ssh $HostAlias "rm -f '$remoteTemp'" | Out-Null
    }
}

if (-not $SkipBuild) {
    & (Join-Path $repoRoot "scripts/build_go_runtime.ps1") -OutputDir $BuildOutputDir
}

$outDir = Resolve-RepoPath $BuildOutputDir
$linuxArm64Artifact = Join-Path $outDir "prism-go-runtime-linux-arm64"
if (-not (Test-Path $linuxArm64Artifact)) {
    throw "Missing linux/arm64 Go package artifact: $linuxArm64Artifact"
}

$localEvidencePath = Resolve-RepoPath $LocalEvidenceRoot
Assert-UnderBuild $localEvidencePath
if (Test-Path $localEvidencePath) {
    Remove-Item -LiteralPath $localEvidencePath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $localEvidencePath | Out-Null

$remoteStage = "$RemoteRoot/$StageName"
& ssh $HostAlias "mkdir -p '$remoteStage/bin' '$remoteStage/scripts' '$remoteStage/evidence'"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create remote staging directories on $HostAlias"
}
& scp $linuxArm64Artifact "${HostAlias}:$remoteStage/bin/prism-go-runtime-linux-arm64"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to copy linux/arm64 Go artifact to $HostAlias"
}
& scp (Join-Path $repoRoot "scripts/go_primary_full_workflow_smoke.py") "${HostAlias}:$remoteStage/scripts/go_primary_full_workflow_smoke.py"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to copy full workflow smoke harness to $HostAlias"
}

$prepareScript = @'
set -euo pipefail

REMOTE_ROOT="$1"
STAGE="$2"
PORT="$3"
REMOTE_USER="$4"
SERVICE_NAME="prism-go-primary-staging.service"
LIVE_DB="$REMOTE_ROOT/knowledge.db"
BINARY="$STAGE/bin/prism-go-runtime-linux-arm64"
DATA="$STAGE/data"
EVIDENCE="$STAGE/evidence"
CADDY_FILE="/etc/caddy/Caddyfile"

if [ ! -f "$LIVE_DB" ]; then
  echo "Missing live DB: $LIVE_DB" >&2
  exit 20
fi
if [ ! -x "$BINARY" ]; then
  chmod +x "$BINARY"
fi

live_hash_before="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
if sudo test -f "$CADDY_FILE"; then
  caddy_hash_before="$(sudo sha256sum "$CADDY_FILE" | awk '{print $1}')"
else
  caddy_hash_before="missing"
fi

rm -rf "$DATA"
mkdir -p "$DATA/static" "$DATA/docs" "$DATA/backups" "$EVIDENCE"
cp "$LIVE_DB" "$DATA/knowledge_t041_staging.db"
if [ -d "$REMOTE_ROOT/static/uploads" ]; then
  cp -a "$REMOTE_ROOT/static/uploads" "$DATA/static/uploads"
else
  mkdir -p "$DATA/static/uploads"
fi
if [ -d "$REMOTE_ROOT/docs/attachments" ]; then
  cp -a "$REMOTE_ROOT/docs/attachments" "$DATA/docs/attachments"
else
  mkdir -p "$DATA/docs/attachments"
fi

cat <<UNIT | sudo tee "/etc/systemd/system/$SERVICE_NAME" >/dev/null
[Unit]
Description=Prism Go Primary Staging (copied data)
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$STAGE
ExecStart=$BINARY --db $DATA/knowledge_t041_staging.db --data-dir $DATA --addr 127.0.0.1:$PORT --enable-notes-write --enable-upload-write --enable-thumbnail-write --enable-upload-url-write --enable-upload-delete --enable-media-cleanup --enable-import-export --enable-server-system
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE_NAME"
sleep 2
sudo systemctl is-active --quiet "$SERVICE_NAME"

live_hash_after="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
if [ "$live_hash_before" != "$live_hash_after" ]; then
  echo "Live DB hash changed during staging prepare" >&2
  exit 21
fi
if sudo test -f "$CADDY_FILE"; then
  caddy_hash_after="$(sudo sha256sum "$CADDY_FILE" | awk '{print $1}')"
else
  caddy_hash_after="missing"
fi
if [ "$caddy_hash_before" != "$caddy_hash_after" ]; then
  echo "Caddyfile hash changed during staging prepare" >&2
  exit 22
fi

cat > "$EVIDENCE/preflight.json" <<JSON
{
  "status": "passed",
  "service": "$SERVICE_NAME",
  "remote_root": "$REMOTE_ROOT",
  "stage": "$STAGE",
  "port": $PORT,
  "live_db": "$LIVE_DB",
  "staging_db": "$DATA/knowledge_t041_staging.db",
  "live_db_sha256_before": "$live_hash_before",
  "live_db_sha256_after_prepare": "$live_hash_after",
  "caddyfile_sha256_before": "$caddy_hash_before",
  "caddyfile_sha256_after_prepare": "$caddy_hash_after",
  "caddy_changed": false,
  "live_default_changed": false,
  "data_copy": {
    "db": true,
    "static_uploads": true,
    "docs_attachments": true
  }
}
JSON
'@

Invoke-RemoteBash "Pi staging prepare" $prepareScript @($RemoteRoot, $remoteStage, [string]$Port, $RemoteUser)

$smokeCommand = "python3 '$remoteStage/scripts/go_primary_full_workflow_smoke.py' --base-url 'http://127.0.0.1:$Port' --label 't041-pi-staging' --evidence-out '$remoteStage/evidence/full-workflow.json'"
& ssh $HostAlias $smokeCommand
if ($LASTEXITCODE -ne 0) {
    throw "Pi staging full workflow smoke failed with exit code $LASTEXITCODE"
}

$verifyScript = @'
set -euo pipefail

REMOTE_ROOT="$1"
STAGE="$2"
PORT="$3"
SERVICE_NAME="prism-go-primary-staging.service"
LIVE_DB="$REMOTE_ROOT/knowledge.db"
EVIDENCE="$STAGE/evidence"
CADDY_FILE="/etc/caddy/Caddyfile"

expected_live_hash="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["live_db_sha256_before"])' "$EVIDENCE/preflight.json")"
expected_caddy_hash="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["caddyfile_sha256_before"])' "$EVIDENCE/preflight.json")"
live_hash_after="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
if [ "$expected_live_hash" != "$live_hash_after" ]; then
  echo "Live DB hash changed during staging smoke" >&2
  exit 30
fi
if sudo test -f "$CADDY_FILE"; then
  caddy_hash_after="$(sudo sha256sum "$CADDY_FILE" | awk '{print $1}')"
else
  caddy_hash_after="missing"
fi
if [ "$expected_caddy_hash" != "$caddy_hash_after" ]; then
  echo "Caddyfile hash changed during staging smoke" >&2
  exit 31
fi

sudo systemctl is-active --quiet "$SERVICE_NAME"
healthz="$(curl -fsS "http://127.0.0.1:$PORT/healthz")"

cat > "$EVIDENCE/staging-summary.json" <<JSON
{
  "status": "passed",
  "service": "$SERVICE_NAME",
  "service_active": true,
  "base_url": "http://127.0.0.1:$PORT",
  "live_db_sha256_after_smoke": "$live_hash_after",
  "live_db_sha256_unchanged": true,
  "caddyfile_sha256_after_smoke": "$caddy_hash_after",
  "caddy_changed": false,
  "live_default_changed": false,
  "healthz": $healthz
}
JSON
'@

Invoke-RemoteBash "Pi staging verify" $verifyScript @($RemoteRoot, $remoteStage, [string]$Port)

foreach ($name in @("preflight.json", "full-workflow.json", "staging-summary.json")) {
    & scp "${HostAlias}:$remoteStage/evidence/$name" (Join-Path $localEvidencePath $name)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to copy remote evidence $name from $HostAlias"
    }
}

$preflight = Get-Content -Raw (Join-Path $localEvidencePath "preflight.json") | ConvertFrom-Json
$workflow = Get-Content -Raw (Join-Path $localEvidencePath "full-workflow.json") | ConvertFrom-Json
$summary = Get-Content -Raw (Join-Path $localEvidencePath "staging-summary.json") | ConvertFrom-Json
$evidence = [ordered]@{
    status = "passed"
    task_ids = @("T040", "T041")
    host_alias = $HostAlias
    linux_arm64_artifact = $linuxArm64Artifact
    remote_stage = $remoteStage
    service = "prism-go-primary-staging.service"
    base_url = "http://127.0.0.1:$Port"
    live_db_sha256_unchanged = $summary.live_db_sha256_unchanged
    caddy_changed = $false
    live_default_changed = $false
    preflight = $preflight
    workflow_smoke = $workflow
    staging_summary = $summary
    boundary = @{
        copied_production_db_data_only = $true
        live_caddy_default_changed = $false
        production_db_mutated = $false
        python_service_stopped = $false
        public_exposure_expanded = $false
    }
}
$evidencePath = Join-Path $localEvidencePath "evidence.json"
$evidence | ConvertTo-Json -Depth 16 | Set-Content -Path $evidencePath -Encoding UTF8
Write-Host "Go primary Pi staging smoke passed. Evidence: $evidencePath"
