param([switch]$SkipBuild)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $repo 'frontend'
$outputs = Join-Path $repo 'outputs'
$stage = Join-Path $repo '.release-stage-alpha33'
$clientArchive = Join-Path $outputs 'EoV-Alpha33-Windows-x64.zip'
$serverArchive = Join-Path $outputs 'EoV-Alpha33-Persistent-Server.zip'
$checksumFile = Join-Path $outputs 'EoV-Alpha33-SHA256.txt'

New-Item -ItemType Directory -Force -Path $outputs | Out-Null
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    if (-not $SkipBuild) {
        Push-Location $frontend
        try { pnpm run desktop:package } finally { Pop-Location }
    }
    $clientSource = Get-ChildItem -LiteralPath (Join-Path $frontend 'out') -Directory | Where-Object Name -Like '*win32-x64' | Select-Object -First 1
    if (-not $clientSource) { throw 'Packaged Windows client directory was not produced' }
    $clientStage = Join-Path $stage 'Echoes-of-Virtuality-Alpha33-Windows-x64'
    Copy-Item -LiteralPath $clientSource.FullName -Destination $clientStage -Recurse
    Copy-Item -LiteralPath (Join-Path $repo 'docs\ALPHA33_RELEASE_NOTES.md') -Destination (Join-Path $clientStage 'ALPHA33_RELEASE_NOTES.md')

    $serverStage = Join-Path $stage 'Echoes-of-Virtuality-Alpha33-Persistent-Server'
    New-Item -ItemType Directory -Path $serverStage | Out-Null
    foreach ($relative in @(
        'persistent_world_app.py', 'persistent_world.py', 'terrain_engine.py', 'action_engine.py',
        'competency_engine.py', 'causal_ledger.py', 'auth_security.py', 'owner_policy.py',
        'persistent-world-requirements.txt', 'run_persistent_server.ps1', '.env.example'
    )) {
        Copy-Item -LiteralPath (Join-Path $repo "backend\$relative") -Destination (Join-Path $serverStage $relative)
    }
    Copy-Item -LiteralPath (Join-Path $repo 'docs\PERSISTENT_MULTIPLAYER_SERVER.md') -Destination (Join-Path $serverStage 'SERVER_SETUP.md')
    Copy-Item -LiteralPath (Join-Path $repo 'docs\ALPHA33_RELEASE_NOTES.md') -Destination (Join-Path $serverStage 'ALPHA33_RELEASE_NOTES.md')

    foreach ($archive in @($clientArchive, $serverArchive, $checksumFile)) {
        if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
    }
    Compress-Archive -LiteralPath $clientStage -DestinationPath $clientArchive -CompressionLevel Optimal
    Compress-Archive -LiteralPath $serverStage -DestinationPath $serverArchive -CompressionLevel Optimal
    $checksumLines = foreach ($archive in @($clientArchive, $serverArchive)) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
        "$hash  $(Split-Path -Leaf $archive)"
    }
    Set-Content -LiteralPath $checksumFile -Value $checksumLines -Encoding utf8NoBOM
} finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}

& (Join-Path $PSScriptRoot 'verify_frontier_release.ps1') -OutputDirectory $outputs
