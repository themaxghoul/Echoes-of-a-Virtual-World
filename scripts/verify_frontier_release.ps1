param([string]$OutputDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'outputs'))

$ErrorActionPreference = 'Stop'
$required = @(
    'EoV-Alpha34-Windows-x64.zip',
    'EoV-Alpha34-Persistent-Server.zip',
    'EoV-Alpha34-SHA256.txt'
)
foreach ($name in $required) {
    $path = Join-Path $OutputDirectory $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing release artifact: $name" }
    if ((Get-Item -LiteralPath $path).Length -eq 0) { throw "Empty release artifact: $name" }
}

$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("eov-alpha34-verify-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $scratch | Out-Null
try {
    $client = Join-Path $scratch 'client'
    $server = Join-Path $scratch 'server'
    Expand-Archive -LiteralPath (Join-Path $OutputDirectory $required[0]) -DestinationPath $client
    Expand-Archive -LiteralPath (Join-Path $OutputDirectory $required[1]) -DestinationPath $server
    if (-not (Get-ChildItem -LiteralPath $client -Recurse -File -Filter 'EchoesOfVirtuality.exe')) { throw 'Client archive has no executable' }
    $serverRoot = Get-ChildItem -LiteralPath $server -Directory | Select-Object -First 1
    if (-not $serverRoot) { throw 'Server archive has no root directory' }
    foreach ($name in @('persistent_world_app.py', 'persistent_world.py', 'terrain_engine.py', 'run_persistent_server.ps1', 'persistent-world-requirements.txt', '.env.example')) {
        if (-not (Get-ChildItem -LiteralPath $server -Recurse -File -Force | Where-Object Name -eq $name)) { throw "Server archive is missing $name" }
    }
    & python -m compileall -q $serverRoot.FullName
    if ($LASTEXITCODE -ne 0) { throw 'Packaged persistent world server contains Python syntax errors' }
    $forbidden = Get-ChildItem -LiteralPath $server -Recurse -File -Force | Where-Object { $_.Extension -in @('.sqlite', '.sqlite3', '.db') -or ($_.Name -eq '.env') }
    if ($forbidden) { throw "Server archive contains private runtime state: $($forbidden.Name -join ', ')" }
    $checksums = Get-Content -Raw -LiteralPath (Join-Path $OutputDirectory $required[2])
    foreach ($name in $required[0..1]) {
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $OutputDirectory $name)).Hash.ToLowerInvariant()
        if ($checksums -notmatch [regex]::Escape("$actual  $name")) { throw "Checksum mismatch for $name" }
    }
} finally {
    if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}

Write-Output 'Alpha 34 release verification passed.'
