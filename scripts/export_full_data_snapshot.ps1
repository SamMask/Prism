param(
    [string]$DataDir = ".",
    [string]$OutputDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-ExistingDirectory {
    param([string]$PathValue)
    $resolved = Resolve-Path -LiteralPath $PathValue -ErrorAction Stop
    return $resolved.ProviderPath
}

function Add-SnapshotItem {
    param(
        [string]$SourcePath,
        [string]$RelativePath,
        [System.Collections.Generic.List[object]]$ManifestItems
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return
    }

    $item = Get-Item -LiteralPath $SourcePath
    if ($item.PSIsContainer) {
        $files = Get-ChildItem -LiteralPath $SourcePath -File -Recurse
        foreach ($file in $files) {
            $relativeChild = Join-Path $RelativePath ($file.FullName.Substring($SourcePath.Length).TrimStart('\', '/'))
            $ManifestItems.Add([ordered]@{
                path = ($relativeChild -replace '\\', '/')
                size_bytes = $file.Length
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
            })
        }
        return
    }

    $ManifestItems.Add([ordered]@{
        path = ($RelativePath -replace '\\', '/')
        size_bytes = $item.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash.ToLowerInvariant()
    })
}

$resolvedDataDir = Resolve-ExistingDirectory $DataDir
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $resolvedDataDir "backups"
}
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$snapshotName = "prism_full_data_snapshot_$timestamp"
$zipPath = Join-Path $OutputDir "$snapshotName.zip"
$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) $snapshotName

$includeSpecs = @(
    @{ Source = "knowledge.db"; Relative = "knowledge.db" },
    @{ Source = "knowledge.db-wal"; Relative = "knowledge.db-wal" },
    @{ Source = "knowledge.db-shm"; Relative = "knowledge.db-shm" },
    @{ Source = "static\uploads"; Relative = "static\uploads" },
    @{ Source = "docs\attachments"; Relative = "docs\attachments" },
    @{ Source = "docs\notes"; Relative = "docs\notes" },
    @{ Source = "config"; Relative = "config" }
)

$manifestItems = [System.Collections.Generic.List[object]]::new()
foreach ($spec in $includeSpecs) {
    $sourcePath = Join-Path $resolvedDataDir $spec.Source
    Add-SnapshotItem -SourcePath $sourcePath -RelativePath $spec.Relative -ManifestItems $manifestItems
}

$manifest = [ordered]@{
    format = "prism.full_data_snapshot.v1"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    data_dir = $resolvedDataDir
    dry_run = [bool]$DryRun
    includes = @("knowledge.db", "knowledge.db-wal", "knowledge.db-shm", "static/uploads", "docs/attachments", "docs/notes", "config")
    item_count = $manifestItems.Count
    items = @($manifestItems)
}

if ($DryRun) {
    $manifest | ConvertTo-Json -Depth 6
    exit 0
}

if (Test-Path -LiteralPath $stageDir) {
    Remove-Item -LiteralPath $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

try {
    foreach ($spec in $includeSpecs) {
        $sourcePath = Join-Path $resolvedDataDir $spec.Source
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }
        $destPath = Join-Path $stageDir $spec.Relative
        $destParent = Split-Path -Parent $destPath
        New-Item -ItemType Directory -Force -Path $destParent | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destPath -Recurse -Force
    }

    $manifestPath = Join-Path $stageDir "snapshot-manifest.json"
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -Force
    Write-Output $zipPath
}
finally {
    if (Test-Path -LiteralPath $stageDir) {
        Remove-Item -LiteralPath $stageDir -Recurse -Force
    }
}
