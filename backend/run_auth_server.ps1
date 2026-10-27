param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Copy .env.playtest.example to .env and fill in the local test settings first."
}

Push-Location $PSScriptRoot
try {
    python -m uvicorn server:app --host $HostAddress --port $Port
}
finally {
    Pop-Location
}
