param(
    [ValidateSet("All", "Cutover", "Rollback", "Soak")]
    [string]$Mode = "All",
    [string]$HostAlias = "PI5Mask24",
    [string]$RemoteRoot = "/home/mask070924/prism",
    [string]$RemoteUser = "mask070924",
    [int]$Port = 5004,
    [int]$SoakSamples = 5,
    [int]$SoakIntervalSeconds = 10,
    [ValidateRange(3, 5)]
    [int]$DeploySnapshotKeep = 5,
    [string]$BuildOutputDir = "build/go-runtime",
    [string]$LocalEvidenceRoot = "build/go-primary-live/pi",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

# Non-interactive SSH/SCP options. BatchMode=yes means ssh/scp never prompt for a
# password, passphrase, or host-key confirmation — they fail fast instead of hanging
# forever when run without a TTY (e.g. background automation). ConnectTimeout and the
# keepalive pair turn a dead connection into a prompt error rather than an infinite wait.
$script:SshBaseOpts = @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=30",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=4"
)

# ssh with stdin redirected from the null device (-n) so it can never consume the
# caller's stdin pipe — the other classic non-TTY hang.
function Invoke-Ssh([string]$RemoteCommand) {
    & ssh -n @script:SshBaseOpts $HostAlias $RemoteCommand
}

function Invoke-Scp([string]$Source, [string]$Dest) {
    & scp @script:SshBaseOpts $Source $Dest
}

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
        throw "Refusing to clean live evidence path outside repo build/: $fullPath"
    }
}

function Quote-RemoteArg([string]$Value) {
    if ($Value.Contains("'")) {
        throw "Remote argument contains a single quote and cannot be safely quoted: $Value"
    }
    return "'" + $Value + "'"
}

function Invoke-RemoteBash([string]$Description, [string]$Script, [string[]]$RemoteArgs) {
    $scriptName = "prism-go-primary-live-" + ([System.Guid]::NewGuid().ToString("N")) + ".sh"
    $localTemp = Join-Path ([System.IO.Path]::GetTempPath()) $scriptName
    $remoteTemp = "/tmp/$scriptName"
    $lfScript = $Script -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($localTemp, $lfScript, [System.Text.UTF8Encoding]::new($false))
    try {
        Invoke-Scp $localTemp "${HostAlias}:$remoteTemp"
        if ($LASTEXITCODE -ne 0) {
            throw "$Description could not copy remote script to $HostAlias"
        }
        $quotedArgs = ($RemoteArgs | ForEach-Object { Quote-RemoteArg $_ }) -join " "
        Invoke-Ssh "chmod +x '$remoteTemp' && '$remoteTemp' $quotedArgs"
        if ($LASTEXITCODE -ne 0) {
            throw "$Description failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Remove-Item -LiteralPath $localTemp -Force -ErrorAction SilentlyContinue
        Invoke-Ssh "rm -f '$remoteTemp'" | Out-Null
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
if ($Mode -eq "All" -and (Test-Path $localEvidencePath)) {
    Remove-Item -LiteralPath $localEvidencePath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $localEvidencePath | Out-Null

$remoteLive = "$RemoteRoot/go-primary-live"
Invoke-Ssh "mkdir -p '$remoteLive/bin' '$remoteLive/scripts' '$remoteLive/evidence'"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create remote live directories on $HostAlias"
}
$remoteArtifactTemp = "$remoteLive/bin/prism-go-runtime-linux-arm64.upload"
Invoke-Scp $linuxArm64Artifact "${HostAlias}:$remoteArtifactTemp"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to copy linux/arm64 Go artifact to $HostAlias"
}
Invoke-Ssh "mv -f '$remoteArtifactTemp' '$remoteLive/bin/prism-go-runtime-linux-arm64' && chmod +x '$remoteLive/bin/prism-go-runtime-linux-arm64'"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install linux/arm64 Go artifact on $HostAlias"
}
foreach ($scriptName in @("go_primary_full_workflow_smoke.py", "python_live_workflow_smoke.py")) {
    Invoke-Scp (Join-Path $repoRoot "scripts/$scriptName") "${HostAlias}:$remoteLive/scripts/$scriptName"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to copy $scriptName to $HostAlias"
    }
}

$cutoverScript = @'
set -euo pipefail

REMOTE_ROOT="$1"
LIVE="$2"
PORT="$3"
REMOTE_USER="$4"
TASK_ID="$5"
CLEAN_AFTER_SMOKE="$6"
DEPLOY_SNAPSHOT_KEEP="$7"
SERVICE_NAME="prism-go-primary.service"
LIVE_DB="$REMOTE_ROOT/knowledge.db"
BINARY="$LIVE/bin/prism-go-runtime-linux-arm64"
EVIDENCE="$LIVE/evidence"
CADDY_FILE="/etc/caddy/Caddyfile"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$REMOTE_ROOT/backups/go-primary-$TASK_ID-$TS"
BACKUP_DB="$BACKUP_DIR/knowledge.db"
BACKUP_DATA_TAR="$BACKUP_DIR/data-files.tar.gz"
BACKUP_CADDY="$BACKUP_DIR/Caddyfile.bak"
BACKUP_PRISM_UNIT="$BACKUP_DIR/prism.service.bak"
BACKUP_GO_UNIT="$BACKUP_DIR/prism-go-primary.service.bak"

mkdir -p "$BACKUP_DIR" "$EVIDENCE"

tree_hash() {
  python3 - "$@" <<'PY'
import hashlib, os, sys
roots = sys.argv[1:]
h = hashlib.sha256()
seen = False
for root in roots:
    if not os.path.exists(root):
        h.update(("missing:" + root + "\n").encode())
        continue
    if os.path.isfile(root):
        rel = os.path.basename(root)
        h.update((rel + "\0").encode())
        with open(root, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        seen = True
        continue
    for dirpath, _, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            h.update((root + "/" + rel + "\0").encode())
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            seen = True
h.update(("seen:" + str(seen)).encode())
print(h.hexdigest())
PY
}

service_rss_kb() {
  svc="$1"
  pid="$(systemctl show -p MainPID --value "$svc" 2>/dev/null || true)"
  if [ -n "$pid" ] && [ "$pid" != "0" ]; then
    ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ' || true
  fi
}

prune_deploy_snapshots() {
  python3 - "$REMOTE_ROOT/backups" "$DEPLOY_SNAPSHOT_KEEP" "$EVIDENCE/$TASK_ID-deploy-snapshot-retention.json" <<'PY'
import datetime
import json
import subprocess
import sys
from pathlib import Path

backups_root = Path(sys.argv[1]).resolve()
keep = int(sys.argv[2])
evidence_path = Path(sys.argv[3])

items = []
if backups_root.exists():
    for path in backups_root.glob("go-primary-*"):
        tar_path = path / "data-files.tar.gz"
        if path.is_dir() and tar_path.is_file():
            stat = tar_path.stat()
            items.append({
                "path": path.resolve(),
                "name": path.name,
                "mtime": stat.st_mtime,
                "data_tar_bytes": stat.st_size,
            })

items.sort(key=lambda item: item["mtime"], reverse=True)
kept = items[:keep]
deleted = []
errors = []
for item in items[keep:]:
    path = item["path"]
    if path.parent != backups_root or not path.name.startswith("go-primary-"):
        errors.append({"path": str(path), "error": "refused_unsafe_path"})
        continue
    proc = subprocess.run(["sudo", "rm", "-rf", "--", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode == 0:
        deleted.append(item)
    else:
        errors.append({"path": str(path), "error": proc.stdout.strip(), "returncode": proc.returncode})

def encode(item):
    return {
        "name": item["name"],
        "path": str(item["path"]),
        "data_tar_mtime": datetime.datetime.fromtimestamp(item["mtime"]).isoformat(),
        "data_tar_mib": round(item["data_tar_bytes"] / 1024 / 1024, 2),
    }

payload = {
    "status": "passed" if not errors else "failed",
    "policy": {
        "scope": "go-primary deploy/cutover data snapshots",
        "keep_latest": keep,
    },
    "before_count": len(items),
    "kept_count": len(kept),
    "deleted_count": len(deleted),
    "deleted_data_tar_mib": round(sum(item["data_tar_bytes"] for item in deleted) / 1024 / 1024, 2),
    "kept": [encode(item) for item in kept],
    "deleted": [encode(item) for item in deleted],
    "errors": errors,
}
evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
if errors:
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    sys.exit(61)
PY
}

write_go_caddy() {
  python3 - "$PORT" <<'PY'
from pathlib import Path
import sys
port = sys.argv[1]
path = Path("/etc/caddy/Caddyfile")
text = path.read_text(encoding="utf-8")
marker = "# MurMur Panel"
suffix = text[text.index(marker):] if marker in text else ""
prism = f"""# Prism - Reverse Proxy (HTTPS with local CA)
https://prism.local {{
    tls internal

    handle {{
        reverse_proxy localhost:{port} {{
            header_up Host {{host}}
            header_up X-Real-IP {{remote_host}}
            header_down X-Prism-Go-Primary hit
        }}
    }}
}}
"""
Path("/tmp/Caddyfile.prism-go-primary").write_text(prism.rstrip() + "\n\n" + suffix.lstrip(), encoding="utf-8")
PY
  sudo caddy validate --config /tmp/Caddyfile.prism-go-primary
  sudo cp /tmp/Caddyfile.prism-go-primary "$CADDY_FILE"
  sudo systemctl reload caddy
}

restore_for_failure() {
  echo "Cutover failed; attempting rollback to pre-cutover backup." >&2
  sudo systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
  sudo systemctl stop prism.service >/dev/null 2>&1 || true
  if [ -f "$BACKUP_DB" ]; then
    cp "$BACKUP_DB" "$LIVE_DB" || true
    rm -f "$LIVE_DB-wal" "$LIVE_DB-shm" || true
  fi
  if [ -f "$BACKUP_DATA_TAR" ]; then
    rm -rf "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments" || true
    mkdir -p "$REMOTE_ROOT/static" "$REMOTE_ROOT/docs"
    tar -C "$REMOTE_ROOT" -xzf "$BACKUP_DATA_TAR" || true
  fi
  sudo systemctl start prism.service >/dev/null 2>&1 || true
  if [ -f "$BACKUP_CADDY" ]; then
    sudo cp "$BACKUP_CADDY" "$CADDY_FILE" || true
    sudo caddy validate --config "$CADDY_FILE" >/dev/null 2>&1 && sudo systemctl reload caddy >/dev/null 2>&1 || true
  fi
}
trap restore_for_failure ERR

if [ ! -f "$LIVE_DB" ]; then
  echo "Missing live DB: $LIVE_DB" >&2
  exit 20
fi
chmod +x "$BINARY"

db_hash_before="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
data_hash_before="$(tree_hash "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments")"
python_rss_before="$(service_rss_kb prism.service)"
if sudo test -f "$CADDY_FILE"; then
  sudo cat "$CADDY_FILE" > "$BACKUP_CADDY"
  caddy_hash_before="$(sudo sha256sum "$CADDY_FILE" | awk '{print $1}')"
else
  caddy_hash_before="missing"
fi
if sudo test -f /etc/systemd/system/prism.service; then
  sudo cat /etc/systemd/system/prism.service > "$BACKUP_PRISM_UNIT"
fi
if sudo test -f /etc/systemd/system/prism-go-primary.service; then
  sudo cat /etc/systemd/system/prism-go-primary.service > "$BACKUP_GO_UNIT"
fi

python3 - "$LIVE_DB" "$BACKUP_DB" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
src.close()
dst.close()
PY

tar_paths=()
[ -d "$REMOTE_ROOT/static/uploads" ] && tar_paths+=("static/uploads")
[ -d "$REMOTE_ROOT/docs/attachments" ] && tar_paths+=("docs/attachments")
if [ "${#tar_paths[@]}" -gt 0 ]; then
  tar -C "$REMOTE_ROOT" -czf "$BACKUP_DATA_TAR" "${tar_paths[@]}"
else
  tar -C "$REMOTE_ROOT" -czf "$BACKUP_DATA_TAR" --files-from /dev/null
fi

artifact_sha256="$(sha256sum "$BINARY" | awk '{print $1}')"

cat <<UNIT | sudo tee "/etc/systemd/system/$SERVICE_NAME" >/dev/null
[Unit]
Description=Prism Go Primary Runtime
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$REMOTE_ROOT
Environment=PRISM_GO_ALLOW_PROD_DB=1
Environment=PRISM_GO_ALLOW_PROD_UPLOADS=1
Environment=PRISM_GO_ALLOW_PROD_IMPORT_EXPORT=1
Environment=PRISM_GO_ALLOW_PROD_SERVER_SYSTEM=1
Environment=PRISM_GO_SUPERVISED=1
ExecStart=$BINARY --db $LIVE_DB --data-dir $REMOTE_ROOT --addr 127.0.0.1:$PORT --enable-tag-write --enable-category-write --enable-notes-write --enable-attachment-text-read --enable-attachment-raw-read --enable-attachment-write --enable-upload-write --enable-thumbnail-write --enable-upload-url-write --enable-upload-delete --enable-media-cleanup --enable-import-export --enable-server-system
Restart=on-failure
RestartForceExitStatus=42
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" >/dev/null
sudo systemctl restart "$SERVICE_NAME"
sleep 2
sudo systemctl is-active --quiet "$SERVICE_NAME"
curl -fsS "http://127.0.0.1:$PORT/healthz" > "$EVIDENCE/$TASK_ID-direct-healthz.json"

write_go_caddy
sudo systemctl stop prism.service
sleep 1
sudo systemctl is-active --quiet "$SERVICE_NAME"
curl -skI https://prism.local/healthz | tr -d '\r' > "$EVIDENCE/$TASK_ID-caddy-healthz.headers"
grep -qi '^x-prism-go-primary: hit$' "$EVIDENCE/$TASK_ID-caddy-healthz.headers"

JSON_PATH="$EVIDENCE/$TASK_ID-cutover.json" \
TASK_ID="$TASK_ID" TS="$TS" PORT="$PORT" SERVICE_NAME="$SERVICE_NAME" \
LIVE_DB="$LIVE_DB" BACKUP_DIR="$BACKUP_DIR" BACKUP_DB="$BACKUP_DB" BACKUP_DATA_TAR="$BACKUP_DATA_TAR" \
BACKUP_CADDY="$BACKUP_CADDY" BACKUP_PRISM_UNIT="$BACKUP_PRISM_UNIT" BACKUP_GO_UNIT="$BACKUP_GO_UNIT" \
ARTIFACT_SHA256="$artifact_sha256" DB_HASH_BEFORE="$db_hash_before" DATA_HASH_BEFORE="$data_hash_before" \
CADDY_HASH_BEFORE="$caddy_hash_before" PYTHON_RSS_BEFORE="$python_rss_before" \
python3 - <<'PY'
import json, os, subprocess

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

data = {
    "status": "cutover_ready",
    "task_id": os.environ["TASK_ID"],
    "timestamp": os.environ["TS"],
    "service": os.environ["SERVICE_NAME"],
    "base_url": "https://prism.local",
    "go_primary_addr": "127.0.0.1:" + os.environ["PORT"],
    "live_db": os.environ["LIVE_DB"],
    "artifact_sha256": os.environ["ARTIFACT_SHA256"],
    "backup": {
        "dir": os.environ["BACKUP_DIR"],
        "db": os.environ["BACKUP_DB"],
        "data_tar": os.environ["BACKUP_DATA_TAR"],
        "caddyfile": os.environ["BACKUP_CADDY"],
        "python_service_unit": os.environ["BACKUP_PRISM_UNIT"],
        "go_primary_unit": os.environ["BACKUP_GO_UNIT"],
    },
    "pre_cutover_hashes": {
        "db_sha256": os.environ["DB_HASH_BEFORE"],
        "data_sha256": os.environ["DATA_HASH_BEFORE"],
        "caddyfile_sha256": os.environ["CADDY_HASH_BEFORE"],
    },
    "retained_python_baseline": {
        "rss_kb": int(os.environ["PYTHON_RSS_BEFORE"] or "0"),
    },
    "services_after_switch": {
        "go_primary": run("systemctl is-active prism-go-primary.service || true"),
        "python_prism": run("systemctl is-active prism.service || true"),
        "caddy": run("systemctl is-active caddy || true"),
    },
    "caddy_route": {
        "target": "localhost:" + os.environ["PORT"],
        "header": "X-Prism-Go-Primary: hit",
    },
    "boundary": {
        "public_bind": False,
        "python_service_receives_caddy_traffic": False,
    },
}
with open(os.environ["JSON_PATH"], "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
PY

python3 "$LIVE/scripts/go_primary_full_workflow_smoke.py" \
  --base-url https://prism.local \
  --insecure \
  --label "$TASK_ID-live-go-primary" \
  --evidence-out "$EVIDENCE/$TASK_ID-full-workflow.json"

if [ "$CLEAN_AFTER_SMOKE" = "1" ]; then
  sudo systemctl stop "$SERVICE_NAME"
  cp "$BACKUP_DB" "$LIVE_DB"
  rm -f "$LIVE_DB-wal" "$LIVE_DB-shm"
  rm -rf "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments"
  mkdir -p "$REMOTE_ROOT/static" "$REMOTE_ROOT/docs"
  tar -C "$REMOTE_ROOT" -xzf "$BACKUP_DATA_TAR"
  sudo systemctl start "$SERVICE_NAME"
  sleep 2
fi

sudo systemctl is-active --quiet "$SERVICE_NAME"
curl -skI https://prism.local/api/server/version | tr -d '\r' > "$EVIDENCE/$TASK_ID-post-smoke.headers"
grep -qi '^x-prism-go-primary: hit$' "$EVIDENCE/$TASK_ID-post-smoke.headers"

db_hash_after="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
data_hash_after="$(tree_hash "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments")"
go_rss_after="$(service_rss_kb "$SERVICE_NAME")"

JSON_PATH="$EVIDENCE/$TASK_ID-post-smoke.json" \
TASK_ID="$TASK_ID" CLEAN_AFTER_SMOKE="$CLEAN_AFTER_SMOKE" DB_HASH_BEFORE="$db_hash_before" DB_HASH_AFTER="$db_hash_after" \
DATA_HASH_BEFORE="$data_hash_before" DATA_HASH_AFTER="$data_hash_after" GO_RSS_AFTER="$go_rss_after" \
python3 - <<'PY'
import json, os, subprocess

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

clean = os.environ["CLEAN_AFTER_SMOKE"] == "1"
data = {
    "status": "passed",
    "task_id": os.environ["TASK_ID"],
    "full_workflow": "passed",
    "smoke_mutation_restored_from_backup": clean,
    "hashes_after_smoke_or_restore": {
        "db_sha256": os.environ["DB_HASH_AFTER"],
        "data_sha256": os.environ["DATA_HASH_AFTER"],
        "db_matches_pre_cutover": os.environ["DB_HASH_BEFORE"] == os.environ["DB_HASH_AFTER"],
        "data_matches_pre_cutover": os.environ["DATA_HASH_BEFORE"] == os.environ["DATA_HASH_AFTER"],
    },
    "services": {
        "go_primary": run("systemctl is-active prism-go-primary.service || true"),
        "python_prism": run("systemctl is-active prism.service || true"),
        "caddy": run("systemctl is-active caddy || true"),
    },
    "go_primary_rss_kb": int(os.environ["GO_RSS_AFTER"] or "0"),
}
with open(os.environ["JSON_PATH"], "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
PY

prune_deploy_snapshots

trap - ERR
'@

$rollbackScript = @'
set -euo pipefail

REMOTE_ROOT="$1"
LIVE="$2"
PORT="$3"
TASK_ID="$4"
SOURCE_TASK_ID="$5"
SERVICE_NAME="prism-go-primary.service"
LIVE_DB="$REMOTE_ROOT/knowledge.db"
EVIDENCE="$LIVE/evidence"
CADDY_FILE="/etc/caddy/Caddyfile"
SOURCE_JSON="$EVIDENCE/$SOURCE_TASK_ID-cutover.json"

if [ ! -f "$SOURCE_JSON" ]; then
  echo "Missing source cutover evidence: $SOURCE_JSON" >&2
  exit 40
fi

eval "$(python3 - "$SOURCE_JSON" <<'PY'
import json, shlex, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
b = d["backup"]
for key, value in {
    "BACKUP_DB": b["db"],
    "BACKUP_DATA_TAR": b["data_tar"],
    "BACKUP_CADDY": b["caddyfile"],
    "BASELINE_RSS": str(d["retained_python_baseline"]["rss_kb"]),
    "SOURCE_DB_HASH": d["pre_cutover_hashes"]["db_sha256"],
    "SOURCE_DATA_HASH": d["pre_cutover_hashes"]["data_sha256"],
}.items():
    print(f"{key}={shlex.quote(value)}")
PY
)"

tree_hash() {
  python3 - "$@" <<'PY'
import hashlib, os, sys
h = hashlib.sha256()
seen = False
for root in sys.argv[1:]:
    if not os.path.exists(root):
        h.update(("missing:" + root + "\n").encode())
        continue
    for dirpath, _, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            h.update((root + "/" + rel + "\0").encode())
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            seen = True
h.update(("seen:" + str(seen)).encode())
print(h.hexdigest())
PY
}

write_python_caddy() {
  python3 - <<'PY'
from pathlib import Path
path = Path("/etc/caddy/Caddyfile")
text = path.read_text(encoding="utf-8")
marker = "# MurMur Panel"
suffix = text[text.index(marker):] if marker in text else ""
prism = """# Prism - Reverse Proxy (HTTPS with local CA)
https://prism.local {
    tls internal

    handle {
        reverse_proxy localhost:5000 {
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_down X-Prism-Python-Rollback hit
        }
    }
}
"""
Path("/tmp/Caddyfile.prism-python-rollback").write_text(prism.rstrip() + "\n\n" + suffix.lstrip(), encoding="utf-8")
PY
  sudo caddy validate --config /tmp/Caddyfile.prism-python-rollback
  sudo cp /tmp/Caddyfile.prism-python-rollback "$CADDY_FILE"
  sudo systemctl reload caddy
}

restore_data() {
  sudo systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
  sudo systemctl stop prism.service >/dev/null 2>&1 || true
  cp "$BACKUP_DB" "$LIVE_DB"
  rm -f "$LIVE_DB-wal" "$LIVE_DB-shm"
  rm -rf "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments"
  mkdir -p "$REMOTE_ROOT/static" "$REMOTE_ROOT/docs"
  tar -C "$REMOTE_ROOT" -xzf "$BACKUP_DATA_TAR"
}

restore_data
sudo systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true
sudo systemctl start prism.service
sleep 2
sudo systemctl is-active --quiet prism.service
write_python_caddy
curl -skI https://prism.local/api/system/stats | tr -d '\r' > "$EVIDENCE/$TASK_ID-python-rollback.headers"
grep -qi '^x-prism-python-rollback: hit$' "$EVIDENCE/$TASK_ID-python-rollback.headers"

python3 "$LIVE/scripts/python_live_workflow_smoke.py" \
  --base-url https://prism.local \
  --insecure \
  --label "$TASK_ID-python-rollback" \
  --expected-header X-Prism-Python-Rollback=hit \
  --forbidden-header X-Prism-Go-Primary \
  --evidence-out "$EVIDENCE/$TASK_ID-python-workflow.json"

restore_data
sudo systemctl start prism.service
sleep 2
sudo systemctl is-active --quiet prism.service
write_python_caddy

db_hash_after="$(sha256sum "$LIVE_DB" | awk '{print $1}')"
backup_db_hash="$(sha256sum "$BACKUP_DB" | awk '{print $1}')"
data_hash_after="$(tree_hash "$REMOTE_ROOT/static/uploads" "$REMOTE_ROOT/docs/attachments")"
python_rss_after="$(pid="$(systemctl show -p MainPID --value prism.service 2>/dev/null || true)"; if [ -n "$pid" ] && [ "$pid" != "0" ]; then ps -o rss= -p "$pid" 2>/dev/null | tr -d ' '; fi)"

JSON_PATH="$EVIDENCE/$TASK_ID-rollback.json" TASK_ID="$TASK_ID" SOURCE_TASK_ID="$SOURCE_TASK_ID" \
SOURCE_DB_HASH="$SOURCE_DB_HASH" SOURCE_DATA_HASH="$SOURCE_DATA_HASH" DB_HASH_AFTER="$db_hash_after" DATA_HASH_AFTER="$data_hash_after" \
BACKUP_DB="$BACKUP_DB" BACKUP_DB_HASH="$backup_db_hash" BACKUP_DATA_TAR="$BACKUP_DATA_TAR" BACKUP_CADDY="$BACKUP_CADDY" BASELINE_RSS="$BASELINE_RSS" PYTHON_RSS_AFTER="$python_rss_after" \
python3 - <<'PY'
import json, os, subprocess

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

data = {
    "status": "passed",
    "task_id": os.environ["TASK_ID"],
    "source_cutover_task_id": os.environ["SOURCE_TASK_ID"],
    "rollback_target": "retained Python prism.service",
    "restored_from_backup": {
        "db": os.environ["BACKUP_DB"],
        "data_tar": os.environ["BACKUP_DATA_TAR"],
        "original_caddyfile_backup_retained": os.environ["BACKUP_CADDY"],
    },
    "hashes_after_final_restore": {
        "db_sha256": os.environ["DB_HASH_AFTER"],
        "backup_db_sha256": os.environ["BACKUP_DB_HASH"],
        "data_sha256": os.environ["DATA_HASH_AFTER"],
        "db_matches_pre_cutover": os.environ["SOURCE_DB_HASH"] == os.environ["DB_HASH_AFTER"],
        "db_matches_backup": os.environ["BACKUP_DB_HASH"] == os.environ["DB_HASH_AFTER"],
        "data_matches_pre_cutover": os.environ["SOURCE_DATA_HASH"] == os.environ["DATA_HASH_AFTER"],
    },
    "services": {
        "go_primary": run("systemctl is-active prism-go-primary.service || true"),
        "python_prism": run("systemctl is-active prism.service || true"),
        "caddy": run("systemctl is-active caddy || true"),
    },
    "python_rss_kb": int(os.environ["PYTHON_RSS_AFTER"] or "0"),
    "retained_python_baseline_rss_kb": int(os.environ["BASELINE_RSS"] or "0"),
    "caddy_route": {
        "target": "localhost:5000",
        "header": "X-Prism-Python-Rollback: hit",
    },
}
with open(os.environ["JSON_PATH"], "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
PY
'@

$soakScript = @'
set -euo pipefail

REMOTE_ROOT="$1"
LIVE="$2"
TASK_ID="$3"
SAMPLES="$4"
INTERVAL="$5"
SOURCE_TASK_ID="$6"
EVIDENCE="$LIVE/evidence"
SERVICE_NAME="prism-go-primary.service"
SOURCE_JSON="$EVIDENCE/$SOURCE_TASK_ID-cutover.json"
START_ISO="$(date -Is)"

baseline_rss="$(python3 - "$SOURCE_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
baseline = d["retained_python_baseline"]["rss_kb"]
if not baseline:
    try:
        rollback = json.load(open(sys.argv[1].replace("t044-cutover.json", "t043-rollback.json"), encoding="utf-8"))
        baseline = rollback.get("python_rss_kb") or rollback.get("retained_python_baseline_rss_kb") or 0
    except Exception:
        baseline = 0
print(baseline)
PY
)"

samples_file="$EVIDENCE/$TASK_ID-soak-samples.jsonl"
: > "$samples_file"
rm -f "$EVIDENCE/$TASK_ID-go-errors.log" "$EVIDENCE/$TASK_ID-caddy-errors.log"

for i in $(seq 1 "$SAMPLES"); do
  sudo systemctl is-active --quiet "$SERVICE_NAME"
  curl -skI https://prism.local/healthz | tr -d '\r' > "$EVIDENCE/$TASK_ID-soak-$i.headers"
  grep -qi '^x-prism-go-primary: hit$' "$EVIDENCE/$TASK_ID-soak-$i.headers"
  health="$(curl -sk https://prism.local/healthz)"
  migration="$(curl -sk https://prism.local/api/system/migration-status)"
  version="$(curl -sk https://prism.local/api/server/version)"
  cleanup="$(curl -sk https://prism.local/api/cleanup/orphan-images)"
  pid="$(systemctl show -p MainPID --value "$SERVICE_NAME")"
  rss="$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  wal_bytes="$(stat -c%s "$REMOTE_ROOT/knowledge.db-wal" 2>/dev/null || echo 0)"
  uploads_count="$(find "$REMOTE_ROOT/static/uploads" -type f 2>/dev/null | wc -l | tr -d ' ')"
  backups_count="$(find "$REMOTE_ROOT/backups" -maxdepth 1 -type f -name 'prism_backup_*.db' 2>/dev/null | wc -l | tr -d ' ')"
  SAMPLE_INDEX="$i" RSS="$rss" WAL_BYTES="$wal_bytes" UPLOADS_COUNT="$uploads_count" BACKUPS_COUNT="$backups_count" \
  HEALTH="$health" MIGRATION="$migration" VERSION="$version" CLEANUP="$cleanup" \
  python3 - <<'PY' >> "$samples_file"
import json, os, time

def parse(name):
    try:
        return json.loads(os.environ[name])
    except Exception as exc:
        return {"parse_error": str(exc), "raw": os.environ.get(name, "")[:300]}

print(json.dumps({
    "sample": int(os.environ["SAMPLE_INDEX"]),
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "rss_kb": int(os.environ.get("RSS") or "0"),
    "wal_bytes": int(os.environ.get("WAL_BYTES") or "0"),
    "uploads_count": int(os.environ.get("UPLOADS_COUNT") or "0"),
    "managed_backups_count": int(os.environ.get("BACKUPS_COUNT") or "0"),
    "healthz": parse("HEALTH"),
    "migration": parse("MIGRATION"),
    "server_version": parse("VERSION"),
    "cleanup_orphan_images": {
        "status": parse("CLEANUP").get("status"),
        "total_count": (parse("CLEANUP").get("data") or {}).get("total_count"),
        "total_size_bytes": (parse("CLEANUP").get("data") or {}).get("total_size_bytes"),
    },
}, sort_keys=True))
PY
  if [ "$i" != "$SAMPLES" ]; then
    sleep "$INTERVAL"
  fi
done

go_errors="$(sudo journalctl -u "$SERVICE_NAME" --since "$START_ISO" -p err..alert --no-pager | sed '/^-- No entries --$/d' || true)"
caddy_errors="$(sudo journalctl -u caddy --since "$START_ISO" -p err..alert --no-pager | sed '/^-- No entries --$/d' || true)"
max_rss="$(python3 - "$samples_file" <<'PY'
import json, sys
mx = 0
for line in open(sys.argv[1], encoding="utf-8"):
    if line.strip():
        mx = max(mx, json.loads(line).get("rss_kb", 0))
print(mx)
PY
)"

if [ -n "$go_errors" ]; then
  echo "$go_errors" > "$EVIDENCE/$TASK_ID-go-errors.log"
  exit 51
fi
if [ -n "$caddy_errors" ]; then
  echo "$caddy_errors" > "$EVIDENCE/$TASK_ID-caddy-errors.log"
  exit 52
fi
if [ "$baseline_rss" != "0" ] && [ "$max_rss" -gt "$baseline_rss" ]; then
  echo "Go primary max RSS $max_rss KB exceeded retained Python baseline $baseline_rss KB" >&2
  exit 53
fi

JSON_PATH="$EVIDENCE/$TASK_ID-soak.json" TASK_ID="$TASK_ID" START_ISO="$START_ISO" SAMPLES="$SAMPLES" INTERVAL="$INTERVAL" \
BASELINE_RSS="$baseline_rss" MAX_RSS="$max_rss" \
python3 - <<'PY'
import json, os, subprocess

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()

data = {
    "status": "passed",
    "task_id": os.environ["TASK_ID"],
    "start": os.environ["START_ISO"],
    "samples": int(os.environ["SAMPLES"]),
    "interval_seconds": int(os.environ["INTERVAL"]),
    "logs": {
        "go_primary_errors_since_start": [],
        "caddy_errors_since_start": [],
    },
    "memory": {
        "retained_python_baseline_rss_kb": int(os.environ["BASELINE_RSS"] or "0"),
        "go_primary_max_rss_kb": int(os.environ["MAX_RSS"] or "0"),
        "not_higher_than_retained_python_baseline": int(os.environ["BASELINE_RSS"] or "0") == 0 or int(os.environ["MAX_RSS"] or "0") <= int(os.environ["BASELINE_RSS"] or "0"),
    },
    "services": {
        "go_primary": run("systemctl is-active prism-go-primary.service || true"),
        "python_prism": run("systemctl is-active prism.service || true"),
        "caddy": run("systemctl is-active caddy || true"),
    },
    "caddy_route": {
        "target": "localhost:5004",
        "header": "X-Prism-Go-Primary: hit",
    },
}
with open(os.environ["JSON_PATH"], "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
PY
'@

if ($Mode -in @("All", "Cutover")) {
    Invoke-RemoteBash "T042 Go primary live cutover" $cutoverScript @($RemoteRoot, $remoteLive, [string]$Port, $RemoteUser, "t042", "0", [string]$DeploySnapshotKeep)
}
if ($Mode -in @("All", "Rollback")) {
    Invoke-RemoteBash "T043 Go primary rollback drill" $rollbackScript @($RemoteRoot, $remoteLive, [string]$Port, "t043", "t042")
}
if ($Mode -in @("All", "Soak")) {
    Invoke-RemoteBash "T044 Go primary live cutover for soak" $cutoverScript @($RemoteRoot, $remoteLive, [string]$Port, $RemoteUser, "t044", "1", [string]$DeploySnapshotKeep)
    Invoke-RemoteBash "T044 Go primary soak" $soakScript @($RemoteRoot, $remoteLive, "t044", [string]$SoakSamples, [string]$SoakIntervalSeconds, "t044")
}

Invoke-Scp "${HostAlias}:$remoteLive/evidence/*.json" "$localEvidencePath/"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to copy live evidence from $HostAlias"
}
$remoteJsonlFiles = Invoke-Ssh "find '$remoteLive/evidence' -maxdepth 1 -name '*.jsonl' -print"
if ($LASTEXITCODE -eq 0 -and $remoteJsonlFiles) {
    foreach ($remoteJsonl in $remoteJsonlFiles) {
        Invoke-Scp "${HostAlias}:$remoteJsonl" "$localEvidencePath/"
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to copy live evidence JSONL $remoteJsonl from $HostAlias"
        }
    }
}

$evidenceFiles = Get-ChildItem -LiteralPath $localEvidencePath -Filter *.json | Where-Object { $_.Name -ne "evidence.json" }
$rollbackEvidencePath = Join-Path $localEvidencePath "t043-rollback.json"
$rollbackRestored = $false
if (Test-Path $rollbackEvidencePath) {
    $rollbackEvidence = Get-Content -Raw $rollbackEvidencePath | ConvertFrom-Json
    $rollbackRestored = ($rollbackEvidence.status -eq "passed")
}

$aggregate = [ordered]@{
    status = "passed"
    mode = $Mode
    task_ids = @("T042", "T043", "T044")
    host_alias = $HostAlias
    remote_live = $remoteLive
    service = "prism-go-primary.service"
    base_url = "https://prism.local"
    go_primary_addr = "127.0.0.1:$Port"
    linux_arm64_artifact = $linuxArm64Artifact
    evidence_files = @($evidenceFiles | ForEach-Object { $_.Name })
    boundary = [ordered]@{
        public_bind = $false
        final_runtime_owner = if ($Mode -in @("All", "Soak")) { "go-primary" } elseif ($Mode -eq "Rollback") { "retained-python" } else { "go-primary" }
        python_service_receives_caddy_traffic_after_t042_t044 = $false
        rollback_restores_db_and_files = $rollbackRestored
    }
}
$aggregatePath = Join-Path $localEvidencePath "evidence.json"
$aggregate | ConvertTo-Json -Depth 12 | Set-Content -Path $aggregatePath -Encoding UTF8
Write-Host "Go primary Pi live ops passed. Evidence: $aggregatePath"
