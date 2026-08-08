# Thin Windows wrapper — state machine stays in Python.
param(
    [ValidateSet("overnight", "preflight", "doctor", "status", "dry-run")]
    [string]$Command = "overnight"
)

$ErrorActionPreference = "Stop"
$repo = (git rev-parse --show-toplevel).Trim()
Set-Location $repo

$agentDir = Join-Path $env:LOCALAPPDATA "cursor-agent"
if (Test-Path $agentDir) {
    $env:PATH = "$agentDir;$env:PATH"
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python non trovato nel PATH." }

& $py.Source "apps/wayfold-compliance/automation/wayfold_orchestrator.py" $Command
exit $LASTEXITCODE
