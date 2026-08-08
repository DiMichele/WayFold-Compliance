param()
$ErrorActionPreference = "Stop"
& "$PSScriptRoot\overnight.ps1" -Command preflight
exit $LASTEXITCODE
