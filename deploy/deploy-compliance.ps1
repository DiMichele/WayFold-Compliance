# Deploy WayFold Compliance to VPS (independent from travel-app deploy.ps1).
# Does NOT print secrets.
#
# Usage (from repo root or this folder):
#   powershell -ExecutionPolicy Bypass -File apps/wayfold-compliance/deploy/deploy-compliance.ps1
#   powershell -ExecutionPolicy Bypass -File apps/wayfold-compliance/deploy/deploy-compliance.ps1 -SetupTls

param(
    [switch]$SetupTls,
    [switch]$SkipSync,
    [switch]$WipeDb
)

$ErrorActionPreference = "Stop"
$Remote = "wayfold@167.233.121.159"
$RemoteDir = "/home/wayfold/apps/wayfold-compliance"
$Here = $PSScriptRoot
$AppRoot = Resolve-Path (Join-Path $Here "..")

function Invoke-RemoteBash([string]$Script) {
    $unix = ($Script -replace "`r`n", "`n") -replace "`r", "`n"
    $tmp = Join-Path $env:TEMP ("wayfold-compliance-remote-" + [guid]::NewGuid().ToString("n") + ".sh")
    [System.IO.File]::WriteAllText($tmp, $unix, [System.Text.UTF8Encoding]::new($false))
    try {
        scp $tmp "${Remote}:/tmp/wayfold-compliance-remote.sh"
        ssh $Remote "bash /tmp/wayfold-compliance-remote.sh; ec=`$?; rm -f /tmp/wayfold-compliance-remote.sh; exit `$ec"
        if ($LASTEXITCODE -ne 0) { throw "Remote bash failed with exit $LASTEXITCODE" }
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

if (-not $SkipSync) {
    Write-Host "-> Sync $AppRoot → ${Remote}:${RemoteDir}"
    ssh $Remote "mkdir -p $RemoteDir"
    if ($LASTEXITCODE -ne 0) { throw "ssh mkdir failed" }

    $Archive = Join-Path $env:TEMP "wayfold-compliance-deploy.tgz"
    if (Test-Path $Archive) { Remove-Item $Archive -Force }

    Push-Location $AppRoot
    try {
        tar -czf $Archive `
            --exclude=vendor `
            --exclude=.git `
            --exclude=.wayfold/logs `
            --exclude=.wayfold/orchestrator.lock `
            --exclude=__pycache__ `
            --exclude=.venv `
            --exclude=*.sqlite3 `
            --exclude=data `
            .
        if ($LASTEXITCODE -ne 0) { throw "tar failed" }
    } finally {
        Pop-Location
    }

    scp $Archive "${Remote}:${RemoteDir}/wayfold-compliance-deploy.tgz"
    if ($LASTEXITCODE -ne 0) { throw "scp failed" }
    Remove-Item $Archive -Force

    $wipeLine = if ($WipeDb) { "touch data/.wipe_db" } else { "true" }
    if ($WipeDb) { Write-Host "-> WipeDb: reset GRC DB + engine stores on VPS" }

    $buildSha = (git -C $AppRoot rev-parse HEAD 2>$null)
    if (-not $buildSha) { $buildSha = "unknown" }
    $builtAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    Write-Host "-> Build SHA: $buildSha"

    Invoke-RemoteBash @"
set -euo pipefail
cd $RemoteDir
tar -xzf wayfold-compliance-deploy.tgz
rm -f wayfold-compliance-deploy.tgz
chmod +x deploy/update-remote.sh deploy/setup-nginx-tls.sh 2>/dev/null || true
sed -i 's/\r$//' deploy/update-remote.sh deploy/setup-nginx-tls.sh 2>/dev/null || true
mkdir -p data
export WAYFOLD_BUILD_SHA='$buildSha'
export WAYFOLD_BUILT_AT='$builtAt'
# Persist build metadata for compose interpolation
umask 077
cat > data/engine/.build.env <<EOF
WAYFOLD_BUILD_SHA=$buildSha
WAYFOLD_BUILT_AT=$builtAt
WAYFOLD_APP_VERSION=0.1.0
WAYFOLD_SCHEMA_VERSION=1
EOF
chmod 600 data/engine/.build.env 2>/dev/null || true
$wipeLine
bash deploy/update-remote.sh
"@
}

$tlsOk = $false
if ($SetupTls) {
    Write-Host "-> Nginx + Let's Encrypt for compliance.wayfold.xyz"
    # Prefer root SSH (available on this VPS); fallback to passwordless sudo as wayfold
    ssh -o BatchMode=yes root@167.233.121.159 "bash $RemoteDir/deploy/setup-nginx-tls.sh"
    if ($LASTEXITCODE -eq 0) {
        $tlsOk = $true
    } else {
        ssh $Remote "sudo -n bash $RemoteDir/deploy/setup-nginx-tls.sh"
        if ($LASTEXITCODE -eq 0) {
            $tlsOk = $true
        } else {
            Write-Host "WARN: TLS/nginx setup needs root on VPS."
            Write-Host "      App stack is up on localhost. Run once:"
            Write-Host "      ssh root@167.233.121.159 bash $RemoteDir/deploy/setup-nginx-tls.sh"
        }
    }
}

# Local health on VPS (does not depend on public TLS)
ssh $Remote "curl -fsS -H 'Host: localhost' http://127.0.0.1:18000/api/health/ || docker inspect -f '{{.State.Health.Status}}' wayfold-compliance-backend | grep -qx healthy"
if ($LASTEXITCODE -ne 0) { throw "Local backend health failed on VPS" }

Write-Host "-> Reload nginx site (build-info route)"
ssh $Remote "sudo -n cp $RemoteDir/deploy/nginx-compliance.conf /etc/nginx/sites-available/compliance && sudo -n nginx -t && sudo -n systemctl reload nginx" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: nginx reload skipped (needs passwordless sudo or root)."
}

Write-Host ""
if ($tlsOk) {
    Write-Host "Deploy completato: https://compliance.wayfold.xyz"
} else {
    Write-Host "Deploy app OK (Docker). Public HTTPS pending root TLS setup."
    Write-Host "Local engine: http://127.0.0.1:18092/healthz on VPS"
}
