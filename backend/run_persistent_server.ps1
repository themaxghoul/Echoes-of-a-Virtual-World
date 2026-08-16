param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8765,
    [string]$Database = ".\data\persistent-world.sqlite3"
)

if (-not $env:EOV_SESSION_SECRET) {
    throw "Set EOV_SESSION_SECRET to the same 32-byte-or-longer signing secret used by the EoV authentication API."
}

$env:EOV_WORLD_DATABASE = $Database
python -m uvicorn persistent_world_app:app --host $HostAddress --port $Port
