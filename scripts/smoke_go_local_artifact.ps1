param(
    [string]$BuildOutputDir = "build/go-runtime",
    [string]$SmokeRoot = "build/go-local-smoke",
    [string]$SourceDb = "knowledge.db",
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
        throw "Refusing to clean smoke path outside repo build/: $fullPath"
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

function Invoke-HttpJson([string]$Url, [string]$Method = "GET", [object]$Body = $null) {
    $request = [System.Net.WebRequest]::Create($Url)
    $request.Method = $Method
    $request.Timeout = 5000
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 12 -Compress
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        $request.ContentType = "application/json"
        $request.ContentLength = $bytes.Length
        $stream = $request.GetRequestStream()
        try {
            $stream.Write($bytes, 0, $bytes.Length)
        }
        finally {
            $stream.Dispose()
        }
    }

    $response = $null
    try {
        $response = $request.GetResponse()
    }
    catch [System.Net.WebException] {
        if ($_.Exception.Response -eq $null) {
            throw
        }
        $response = $_.Exception.Response
    }

    $reader = $null
    try {
        $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
        $raw = $reader.ReadToEnd()
        $parsed = $null
        if ($raw.TrimStart().StartsWith("{") -or $raw.TrimStart().StartsWith("[")) {
            $parsed = $raw | ConvertFrom-Json
        }
        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Body = $parsed
            Raw = $raw
        }
    }
    finally {
        if ($null -ne $reader) {
            $reader.Dispose()
        }
        if ($null -ne $response) {
            $response.Dispose()
        }
    }
}

function Wait-ForGoRuntime([string]$BaseUrl) {
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-HttpJson "$BaseUrl/healthz"
            if ($health.StatusCode -eq 200) {
                return $health
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Go runtime did not become healthy at $BaseUrl"
}

function Start-GoArtifact([string]$Artifact, [string[]]$RuntimeArgs, [string]$LogPrefix) {
    $stdout = Join-Path $logsDir "$LogPrefix.stdout.log"
    $stderr = Join-Path $logsDir "$LogPrefix.stderr.log"
    $argLine = ($RuntimeArgs | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join " "
    return Start-Process -FilePath $Artifact -ArgumentList $argLine -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
}

function Stop-GoArtifact($Process) {
    if ($null -eq $Process) {
        return
    }
    if (-not $Process.HasExited) {
        $Process.Kill()
        $Process.WaitForExit()
    }
}

function Add-AttachmentFixture([string]$DbPath, [string]$DataDir, [string]$SeedProgram) {
    $seedSource = @'
package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

func main() {
	if len(os.Args) != 3 {
		panic("usage: seed_attachment_fixture <db> <data-dir>")
	}
	dbPath := os.Args[1]
	dataDir := os.Args[2]
	relPath := "docs/attachments/c_release_candidate_file.md"
	attachmentDir := filepath.Join(dataDir, "docs", "attachments")
	if err := os.MkdirAll(attachmentDir, 0755); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(dataDir, filepath.FromSlash(relPath)), []byte("C release candidate attachment\nsecond line"), 0644); err != nil {
		panic(err)
	}
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		panic(err)
	}
	defer db.Close()
	var noteID int64
	if err := db.QueryRow("SELECT id FROM Notes ORDER BY id LIMIT 1").Scan(&noteID); err != nil {
		panic(err)
	}
	result, err := db.Exec(
		"INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted) VALUES (?, ?, 'md', 'C Release Candidate File', 48, 0)",
		noteID,
		relPath,
	)
	if err != nil {
		panic(err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		panic(err)
	}
	fmt.Print(id)
}
'@
    Set-Content -Path $SeedProgram -Value $seedSource -Encoding UTF8
    Push-Location (Join-Path $repoRoot "go-shadow")
    try {
        $seedOutput = & go run $SeedProgram $DbPath $DataDir
        if ($LASTEXITCODE -ne 0) {
            throw "Attachment fixture seed failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
    $attachmentIdText = ($seedOutput | Out-String).Trim()
    if (-not ($attachmentIdText -match '^\d+$')) {
        throw "Attachment fixture seed returned invalid id: $attachmentIdText"
    }
    return [int]$attachmentIdText
}

if (-not $SkipBuild) {
    & (Join-Path $repoRoot "scripts/build_go_runtime.ps1") -OutputDir $BuildOutputDir
}

$outDir = Resolve-RepoPath $BuildOutputDir
$artifact = Join-Path $outDir "prism-go-runtime.exe"
if (-not (Test-Path $artifact)) {
    throw "Missing local Go artifact: $artifact"
}
$linuxArm64Artifact = Join-Path $outDir "prism-go-runtime-linux-arm64"
if (-not (Test-Path $linuxArm64Artifact)) {
    throw "Missing linux/arm64 Go artifact: $linuxArm64Artifact"
}

$sourceDbPath = Resolve-RepoPath $SourceDb
if (-not (Test-Path $sourceDbPath)) {
    throw "Missing source DB for smoke copy: $sourceDbPath"
}
$sourceHashBefore = (Get-FileHash -Algorithm SHA256 -Path $sourceDbPath).Hash

$smokeRootPath = Resolve-RepoPath $SmokeRoot
Assert-UnderBuild $smokeRootPath
if (Test-Path $smokeRootPath) {
    Remove-Item -LiteralPath $smokeRootPath -Recurse -Force
}

$dataDir = Join-Path $smokeRootPath "data"
$logsDir = Join-Path $smokeRootPath "logs"
foreach ($dir in @(
    $dataDir,
    $logsDir,
    (Join-Path $dataDir "static/uploads"),
    (Join-Path $dataDir "docs/attachments"),
    (Join-Path $dataDir "backups")
)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$readDb = Join-Path $dataDir "prism_local_smoke_read_dev.db"
$writeDb = Join-Path $dataDir "prism_local_smoke_write_dev.db"
Copy-Item -LiteralPath $sourceDbPath -Destination $readDb -Force
Copy-Item -LiteralPath $sourceDbPath -Destination $writeDb -Force
$attachmentSeedProgram = Join-Path $smokeRootPath "seed_attachment_fixture.go"
$attachmentId = Add-AttachmentFixture $readDb $dataDir $attachmentSeedProgram

$thumbnailInput = Join-Path $dataDir "pillow_closure_source.png"
$thumbnailOutput = Join-Path $dataDir "static/uploads/pillow_closure_thumb.webp"
Add-Type -AssemblyName System.Drawing
$bitmap = [System.Drawing.Bitmap]::new(16, 16)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.Clear([System.Drawing.Color]::FromArgb(40, 120, 200))
    $bitmap.Save($thumbnailInput, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
& $artifact --thumbnail-input $thumbnailInput --thumbnail-output $thumbnailOutput
if ($LASTEXITCODE -ne 0) {
    throw "Go artifact thumbnail helper failed with exit code $LASTEXITCODE"
}
if (-not (Test-Path $thumbnailOutput)) {
    throw "Go artifact thumbnail helper did not create _thumb.webp"
}
$thumbBytes = [System.IO.File]::ReadAllBytes($thumbnailOutput)
$thumbText = [System.Text.Encoding]::ASCII.GetString($thumbBytes, 0, [Math]::Min($thumbBytes.Length, 12))
if (-not ($thumbText.StartsWith("RIFF") -and $thumbText.Contains("WEBP"))) {
    throw "Go artifact thumbnail helper output is not a WebP file"
}

$readPort = Get-FreeTcpPort
$readBase = "http://127.0.0.1:$readPort"
$readProc = $null
try {
    $readProc = Start-GoArtifact $artifact @(
        "--db", $readDb,
        "--addr", "127.0.0.1:$readPort",
        "--data-dir", $dataDir
    ) "read-only"
    $readHealth = Wait-ForGoRuntime $readBase
    if ($readHealth.Body.runtime.sqlite_query_only -ne $true) {
        throw "Default local artifact must keep SQLite query_only enabled"
    }
    if ($readHealth.Body.runtime.api_surface -ne "get-read-only") {
        throw "Default local artifact API surface drifted: $($readHealth.Body.runtime.api_surface)"
    }

    foreach ($endpoint in @("/api/test", "/api/categories", "/api/tags", "/api/notes?per_page=1")) {
        $response = Invoke-HttpJson "$readBase$endpoint"
        if ($response.StatusCode -ne 200) {
            throw "Read smoke failed for $endpoint with HTTP $($response.StatusCode)"
        }
    }
    $migration = Invoke-HttpJson "$readBase/api/system/migration-status"
    if ($migration.StatusCode -ne 200) {
        throw "Migration-status smoke failed with HTTP $($migration.StatusCode): $($migration.Raw)"
    }
    if ($migration.Body.data.current_version -ne $migration.Body.data.latest_version -or @($migration.Body.data.pending).Count -ne 0) {
        throw "Migration-status smoke drifted: $($migration.Raw)"
    }

    $spa = Invoke-HttpJson "$readBase/"
    if ($spa.StatusCode -ne 200 -or -not $spa.Raw.ToLowerInvariant().Contains("<html")) {
        throw "SPA smoke failed: root did not serve index.html"
    }

    $disabledWrite = Invoke-HttpJson "$readBase/api/tags/1" "PUT" @{ name = "blocked-by-default" }
    if ($disabledWrite.StatusCode -ne 405) {
        throw "Default runtime unexpectedly accepted write candidate route"
    }
    $disabledNotesWrite = Invoke-HttpJson "$readBase/api/notes" "POST" @{ title = "blocked"; content = "blocked" }
    if ($disabledNotesWrite.StatusCode -ne 405) {
        throw "Default runtime unexpectedly accepted notes write candidate route"
    }
    $disabledAttachmentTextRead = Invoke-HttpJson "$readBase/api/attachments/$attachmentId"
    if ($disabledAttachmentTextRead.StatusCode -ne 405) {
        throw "Default runtime unexpectedly accepted attachment text read candidate route"
    }
}
finally {
    Stop-GoArtifact $readProc
}

$fileReadPort = Get-FreeTcpPort
$fileReadBase = "http://127.0.0.1:$fileReadPort"
$fileReadProc = $null
try {
    $fileReadProc = Start-GoArtifact $artifact @(
        "--db", $readDb,
        "--addr", "127.0.0.1:$fileReadPort",
        "--data-dir", $dataDir,
        "--enable-attachment-text-read"
    ) "file-read-candidate"
    $fileReadHealth = Wait-ForGoRuntime $fileReadBase
    if ($fileReadHealth.Body.runtime.sqlite_query_only -ne $true) {
        throw "File-read candidate must keep SQLite query_only enabled"
    }
    if ($fileReadHealth.Body.runtime.api_surface -ne "get-read-only+local-attachment-text-read") {
        throw "File-read candidate API surface drifted: $($fileReadHealth.Body.runtime.api_surface)"
    }
    $attachmentRead = Invoke-HttpJson "$fileReadBase/api/attachments/$attachmentId"
    if ($attachmentRead.StatusCode -ne 200 -or $attachmentRead.Body.data.content -ne "C release candidate attachment`nsecond line") {
        throw "Attachment text read smoke failed with HTTP $($attachmentRead.StatusCode): $($attachmentRead.Raw)"
    }
}
finally {
    Stop-GoArtifact $fileReadProc
}

$writePort = Get-FreeTcpPort
$writeBase = "http://127.0.0.1:$writePort"
$writeProc = $null
$stamp = Get-Date -Format "yyyyMMddHHmmss"
try {
    $writeProc = Start-GoArtifact $artifact @(
        "--db", $writeDb,
        "--addr", "127.0.0.1:$writePort",
        "--data-dir", $dataDir,
        "--enable-tag-write",
        "--enable-category-write",
        "--enable-notes-write"
    ) "write-candidate"
    $writeHealth = Wait-ForGoRuntime $writeBase
    if ($writeHealth.Body.runtime.sqlite_query_only -ne $false) {
        throw "Write-candidate smoke should disable SQLite query_only only on the copied DB"
    }
    if ($writeHealth.Body.runtime.api_surface -ne "get-read-only+local-tag-write+local-category-write+local-notes-write") {
        throw "Write-candidate API surface drifted: $($writeHealth.Body.runtime.api_surface)"
    }

    $tags = Invoke-HttpJson "$writeBase/api/tags"
    $tag = @($tags.Body.data)[0]
    if ($null -eq $tag) {
        throw "Write smoke requires at least one tag in the copied DB"
    }
    $tagWrite = Invoke-HttpJson "$writeBase/api/tags/$($tag.id)" "PUT" @{ name = "local-smoke-tag-$stamp" }
    if ($tagWrite.StatusCode -ne 200) {
        throw "Tag write smoke failed with HTTP $($tagWrite.StatusCode): $($tagWrite.Raw)"
    }

    $categories = Invoke-HttpJson "$writeBase/api/categories"
    $category = @($categories.Body.data)[0]
    if ($null -eq $category) {
        throw "Write smoke requires at least one category in the copied DB"
    }
    $categoryWrite = Invoke-HttpJson "$writeBase/api/categories/$($category.id)" "PUT" @{ icon = "S" }
    if ($categoryWrite.StatusCode -ne 200) {
        throw "Category write smoke failed with HTTP $($categoryWrite.StatusCode): $($categoryWrite.Raw)"
    }

    $noteCreate = Invoke-HttpJson "$writeBase/api/notes" "POST" @{
        title = "local-smoke-note-$stamp"
        content = "local smoke note content"
        category_id = $category.id
        tags = @("local-smoke-note-tag-$stamp")
        urls = @("https://local-smoke.example/$stamp")
    }
    if ($noteCreate.StatusCode -ne 201) {
        throw "Notes create smoke failed with HTTP $($noteCreate.StatusCode): $($noteCreate.Raw)"
    }
    $noteId = $noteCreate.Body.data.note_id
    $noteUpdate = Invoke-HttpJson "$writeBase/api/notes/$noteId" "PUT" @{
        title = "local-smoke-note-updated-$stamp"
        content = "local smoke note content updated"
        category_id = $category.id
        tags = @("local-smoke-note-updated-tag-$stamp")
        urls = @("https://local-smoke-updated.example/$stamp")
    }
    if ($noteUpdate.StatusCode -ne 200) {
        throw "Notes update smoke failed with HTTP $($noteUpdate.StatusCode): $($noteUpdate.Raw)"
    }
    $noteHistory = Invoke-HttpJson "$writeBase/api/notes/$noteId/history"
    if ($noteHistory.StatusCode -ne 200 -or $noteHistory.Body.data.total -lt 1) {
        throw "Notes history smoke failed with HTTP $($noteHistory.StatusCode): $($noteHistory.Raw)"
    }
    $noteDelete = Invoke-HttpJson "$writeBase/api/notes/$noteId" "DELETE"
    if ($noteDelete.StatusCode -ne 200) {
        throw "Notes delete smoke failed with HTTP $($noteDelete.StatusCode): $($noteDelete.Raw)"
    }
}
finally {
    Stop-GoArtifact $writeProc
}

$sourceHashAfter = (Get-FileHash -Algorithm SHA256 -Path $sourceDbPath).Hash
if ($sourceHashAfter -ne $sourceHashBefore) {
    throw "Production/source DB hash changed during local smoke"
}

$evidence = [pscustomobject]@{
    status = "passed"
    artifact = $artifact
    linux_arm64_artifact = $linuxArm64Artifact
    smoke_root = $smokeRootPath
    source_db = $sourceDbPath
    source_db_sha256 = $sourceHashAfter
    copied_dbs = @($readDb, $writeDb)
    read_only_smoke = @{
        base_url = $readBase
        sqlite_query_only = $true
        api_surface = "get-read-only"
        endpoints = @("/healthz", "/", "/api/test", "/api/system/migration-status", "/api/categories", "/api/tags", "/api/notes?per_page=1")
        disabled_write_status = 405
        disabled_notes_write_status = 405
        disabled_attachment_text_read_status = 405
    }
    file_read_candidate_smoke = @{
        base_url = $fileReadBase
        flags = @("--enable-attachment-text-read")
        sqlite_query_only = $true
        api_surface = "get-read-only+local-attachment-text-read"
        route = "GET /api/attachments/<id>"
        db_scope = "copied DB only"
        data_scope = "copied data dir only"
    }
    write_candidate_smoke = @{
        base_url = $writeBase
        sqlite_query_only = $false
        api_surface = "get-read-only+local-tag-write+local-category-write+local-notes-write"
        routes = @("PUT /api/tags/<id>", "PUT /api/categories/<id>", "POST /api/notes", "PUT /api/notes/<id>", "GET /api/notes/<id>/history", "DELETE /api/notes/<id>")
        db_scope = "copied DB only"
    }
    thumbnail_helper_smoke = @{
        command = "--thumbnail-input $thumbnailInput --thumbnail-output $thumbnailOutput"
        output = $thumbnailOutput
        output_convention = "_thumb.webp"
        python_or_pillow_required = $false
    }
    release_boundary = @{
        pi_deployed = $false
        caddy_changed = $false
        systemd_changed = $false
        frontend_default_changed = $false
        production_db_mutated = $false
    }
}
$evidencePath = Join-Path $smokeRootPath "evidence.json"
$evidence | ConvertTo-Json -Depth 12 | Set-Content -Path $evidencePath -Encoding UTF8
Write-Host "Local Go artifact smoke passed. Evidence: $evidencePath"
