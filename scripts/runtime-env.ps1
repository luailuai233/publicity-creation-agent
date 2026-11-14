$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$RuntimeRoot = Join-Path $ProjectRoot '.runtime'

$RuntimeDirectories = @(
    $RuntimeRoot,
    (Join-Path $RuntimeRoot 'pip-cache'),
    (Join-Path $RuntimeRoot 'pycache'),
    (Join-Path $RuntimeRoot 'python-user'),
    (Join-Path $RuntimeRoot 'tmp'),
    (Join-Path $RuntimeRoot 'playwright-browsers'),
    (Join-Path $ProjectRoot 'storage'),
    (Join-Path $ProjectRoot 'storage\projects'),
    (Join-Path $ProjectRoot 'exports'),
    (Join-Path $ProjectRoot 'test-results')
)

foreach ($Directory in $RuntimeDirectories) {
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
}

$env:PIP_CACHE_DIR = Join-Path $RuntimeRoot 'pip-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $RuntimeRoot 'pycache'
$env:PYTHONUSERBASE = Join-Path $RuntimeRoot 'python-user'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = Join-Path $RuntimeRoot 'tmp'
$env:TMP = Join-Path $RuntimeRoot 'tmp'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $RuntimeRoot 'playwright-browsers'
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $ProjectRoot 'storage\app.db') -replace '\\', '/')
$env:WORKBENCH_ROOT = $ProjectRoot
