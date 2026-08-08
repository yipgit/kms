param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$EnvFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
if (-not $EnvFile) { $EnvFile = Join-Path $ProjectRoot ".env" }
$BridgeScript = Join-Path $ProjectRoot "host_bridge\codex_bridge.py"
$LogDirectory = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDirectory "codex-bridge.log"

if (-not (Test-Path $EnvFile)) { throw "Missing .env file: $EnvFile" }
if (-not (Test-Path $BridgeScript)) { throw "Missing bridge script: $BridgeScript" }
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Get-DotEnvValue([string]$Name) {
    $line = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) { return "" }
    $value = ($line -split "=", 2)[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
}

$bridgeToken = Get-DotEnvValue "CODEX_BRIDGE_TOKEN"
if (-not $bridgeToken) { throw "CODEX_BRIDGE_TOKEN is missing in $EnvFile" }

$env:CODEX_BRIDGE_TOKEN = $bridgeToken
$env:CODEX_BRIDGE_HOST = if (Get-DotEnvValue "CODEX_BRIDGE_HOST") { Get-DotEnvValue "CODEX_BRIDGE_HOST" } else { "0.0.0.0" }
$env:CODEX_BRIDGE_PORT = if (Get-DotEnvValue "CODEX_BRIDGE_PORT") { Get-DotEnvValue "CODEX_BRIDGE_PORT" } else { "8765" }
$env:CODEX_COMMAND = if (Get-DotEnvValue "CODEX_COMMAND") { Get-DotEnvValue "CODEX_COMMAND" } else { "codex" }

"$(Get-Date -Format o) starting Codex bridge on $($env:CODEX_BRIDGE_HOST):$($env:CODEX_BRIDGE_PORT)" | Add-Content -LiteralPath $LogFile
$python = (Get-Command python -ErrorAction Stop).Source
& $python $BridgeScript *>> $LogFile
$exitCode = $LASTEXITCODE
"$(Get-Date -Format o) bridge exited with code $exitCode" | Add-Content -LiteralPath $LogFile
exit $exitCode
