param(
    [ValidateSet("doctor", "status", "preflight", "overnight", "dry-run")]
    [string]$Command = "overnight"
)

$ErrorActionPreference = "Stop"
& "$PSScriptRoot\overnight.ps1" -Command $Command
exit $LASTEXITCODE
