$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repo 'backend'
$frontend = Join-Path $repo 'frontend'

Push-Location $backend
try {
    python -m py_compile auth_security.py owner_policy.py persistent_world.py persistent_world_app.py world_status.py action_engine.py society_engine.py competency_engine.py causal_ledger.py economy/ledger.py economy/policy.py economy/public_ledger.py economy/compute_settlement.py mail/domain.py security/rate_limit.py
    python -m unittest tests.test_owner_policy tests.test_auth_security tests.test_persistent_world tests.test_persistent_world_app tests.test_action_engine tests.test_society_engine tests.test_competency_engine tests.test_causal_ledger tests.test_simulation_ledger tests.test_compute_settlement tests.test_public_ledger tests.test_mail_domain tests.test_rate_limit
} finally {
    Pop-Location
}

Push-Location $frontend
try {
    pnpm install --frozen-lockfile
    pnpm run test:desktop-store
    pnpm exec playwright install chromium
    pnpm run test:e2e
    $env:CI = 'false'
    pnpm run build
} finally {
    Pop-Location
}
