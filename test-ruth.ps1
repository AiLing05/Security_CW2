# Run from PowerShell: .\test-ruth.ps1
# Uses an isolated SQLite test database; does not use the Docker app database.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python manage.py test assets.tests.test_authorization assets.tests.test_metadata_updates --settings=dam_backend.settings_test --verbosity=2
    if ($LASTEXITCODE -ne 0) { throw 'Ruth tests failed. Review the failures above.' }
    Write-Host 'PASS: authorization and metadata-only update tests.' -ForegroundColor Green
} finally {
    Pop-Location
}
