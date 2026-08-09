# Sync apps/wayfold-compliance → DiMichele/WayFold-Compliance (review mirror).
# Run from monorepo root after live SHA verified.
param(
    [string]$Message = "sync: review mirror from WayFold monorepo"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$Source = Join-Path $Root "apps\wayfold-compliance"
$MirrorDir = Join-Path $env:TEMP "WayFold-Compliance-mirror"
$MirrorUrl = "https://github.com/DiMichele/WayFold-Compliance.git"

if (-not (Test-Path $Source)) {
    throw "Source not found: $Source"
}

if (-not (Test-Path $MirrorDir)) {
    Write-Host "-> Clone mirror $MirrorUrl"
    git clone $MirrorUrl $MirrorDir
} else {
    Write-Host "-> Pull mirror"
    git -C $MirrorDir pull --ff-only origin main
}

$Exclude = @(
    ".git", "vendor", "data", ".wayfold", "__pycache__", ".venv", "*.sqlite3"
)
Write-Host "-> Copy $Source -> $MirrorDir"
Get-ChildItem -LiteralPath $MirrorDir -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
robocopy $Source $MirrorDir /MIR /XD vendor data .wayfold .git __pycache__ .venv /XF *.sqlite3 /NFL /NDL /NJH /NJS /nc /ns /np
if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }

$SourceSha = (git -C $Root rev-parse HEAD).Trim()
$TreeHash = (git -C $MirrorDir rev-parse HEAD:"docs/review" 2>$null)
# Update SYNC manifest inside mirror copy
$ManifestPath = Join-Path $MirrorDir "docs\review\SYNC-MANIFEST.json"
if (Test-Path $ManifestPath) {
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $manifest.source_sha = $SourceSha
    $manifest.sync_timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $manifest | ConvertTo-Json -Depth 5 | Set-Content $ManifestPath -Encoding utf8
}

Write-Host "-> Commit mirror (source_sha=$SourceSha)"
git -C $MirrorDir add -A
$status = git -C $MirrorDir status --porcelain
if ($status) {
    git -C $MirrorDir commit -m $Message
    git -C $MirrorDir push origin main
    $mirrorSha = (git -C $MirrorDir rev-parse HEAD).Trim()
    Write-Host "Mirror SHA: $mirrorSha"
} else {
    Write-Host "Mirror already up to date."
}

Write-Host "Done."
