$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $BasePython = if ($env:WORKBENCH_PYTHON) { $env:WORKBENCH_PYTHON } else { 'D:\conda\python.exe' }
    if (-not (Test-Path -LiteralPath $BasePython)) {
        throw "No usable Python interpreter found. Set WORKBENCH_PYTHON to a Python 3.9+ executable."
    }
    & $BasePython -m venv (Join-Path $ProjectRoot '.venv')
}

& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectRoot 'requirements-dev.txt')
