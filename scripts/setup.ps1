$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if ((Test-Path -LiteralPath $VenvPython) -and -not (Test-SupportedPython -PythonExecutable $VenvPython)) {
    throw 'Existing .venv uses an unsupported Python. Move or remove it, then rerun setup with WORKBENCH_PYTHON pointing to Python 3.11 or 3.12.'
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $BasePython = $env:WORKBENCH_PYTHON
    if (-not $BasePython -or -not (Test-SupportedPython -PythonExecutable $BasePython)) {
        throw 'Set WORKBENCH_PYTHON to a Python 3.11 or 3.12 executable.'
    }
    & $BasePython -m venv (Join-Path $ProjectRoot '.venv')
}

$VenvPython = Assert-WorkbenchVenv
& $VenvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    & $VenvPython -m ensurepip --upgrade
}
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectRoot 'requirements.lock.txt')
& $VenvPython -m alembic -c (Join-Path $ProjectRoot 'alembic.ini') upgrade head
