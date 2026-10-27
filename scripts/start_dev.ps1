param([string]$SessionSecret = $env:EOV_SESSION_SECRET)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $SessionSecret -or [Text.Encoding]::UTF8.GetByteCount($SessionSecret) -lt 32) {
    throw 'Pass -SessionSecret with at least 32 bytes or set EOV_SESSION_SECRET.'
}

docker compose -f (Join-Path $repo 'compose.yaml') up -d mongo
$env:MONGO_URL = 'mongodb://127.0.0.1:27017'
$env:DB_NAME = 'eov_development'
$env:EOV_SESSION_SECRET = $SessionSecret
$env:EOV_ECONOMY_MODE = 'simulation'
$env:CORS_ORIGINS = 'http://127.0.0.1:3000,http://localhost:3000,null'
$env:EOV_ALLOWED_ORIGINS = 'http://127.0.0.1:3000,http://localhost:3000,null'
$env:REACT_APP_BACKEND_URL = 'http://127.0.0.1:8000'
$env:REACT_APP_WORLD_SERVER_URL = 'http://127.0.0.1:8765'

Start-Process python -ArgumentList '-m','uvicorn','server:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $repo 'backend') -WindowStyle Hidden
Start-Process python -ArgumentList '-m','uvicorn','persistent_world_app:app','--host','127.0.0.1','--port','8765' -WorkingDirectory (Join-Path $repo 'backend') -WindowStyle Hidden
Start-Process pnpm -ArgumentList 'start' -WorkingDirectory (Join-Path $repo 'frontend') -WindowStyle Hidden
Write-Host 'EoV development services started: client 3000, identity API 8000, world authority 8765.'
