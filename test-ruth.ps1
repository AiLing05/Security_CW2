param([switch]$Postgres, [switch]$Full)
# Alternative if PowerShell blocks scripts: python -m pytest assets/tests -v
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $settings = if ($Postgres) { 'dam_backend.settings_test_postgres' } else { 'dam_backend.settings_test' }
    $targets = if ($Full) { @('assets/tests', 'audit/tests', 'dam_backend/test_infrastructure.py') } else {
        @('assets/tests/test_authorization.py', 'assets/tests/test_metadata_updates.py', 'assets/tests/test_rbac_security.py')
    }
    $engine = if ($Postgres) { 'postgres' } else { 'sqlite' }
    New-Item -ItemType Directory -Path 'docs/ruth/evidence' -Force | Out-Null
    python -m pytest @targets "--ds=$settings" -v --tb=short "--junitxml=docs/ruth/evidence/$engine-results.xml"
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Review the failures above.' }
    Write-Host 'PASS. Test evidence saved in docs/ruth/evidence.' -ForegroundColor Green
} finally {
    Pop-Location
}
