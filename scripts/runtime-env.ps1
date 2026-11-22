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
    (Join-Path $RuntimeRoot 'browser-cache'),
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
$SystemEdge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if ($env:WORKBENCH_USE_SYSTEM_EDGE -eq '1' -and (Test-Path -LiteralPath $SystemEdge)) {
    $env:PLAYWRIGHT_EXECUTABLE_PATH = $SystemEdge
} else {
    Remove-Item Env:PLAYWRIGHT_EXECUTABLE_PATH -ErrorAction SilentlyContinue
}
$env:PLAYWRIGHT_BROWSER_CACHE = Join-Path $RuntimeRoot 'browser-cache'
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $ProjectRoot 'storage\app.db') -replace '\\', '/')
$env:WORKBENCH_ROOT = $ProjectRoot

function Test-SupportedPython {
    param([Parameter(Mandatory = $true)][string]$PythonExecutable)
    if (-not (Test-Path -LiteralPath $PythonExecutable)) { return $false }
    & $PythonExecutable -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 13) else 1)"
    return $LASTEXITCODE -eq 0
}

function Assert-WorkbenchVenv {
    $VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-SupportedPython -PythonExecutable $VenvPython)) {
        throw 'Project .venv must use Python 3.11 or 3.12. Run scripts/setup.ps1 with WORKBENCH_PYTHON set to a supported interpreter.'
    }
    & $VenvPython -c "import pathlib,sys; root=pathlib.Path(r'$ProjectRoot').resolve(); exe=pathlib.Path(sys.executable).resolve(); raise SystemExit(0 if root in exe.parents else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'The active interpreter is not inside the project workspace.' }
    return $VenvPython
}
