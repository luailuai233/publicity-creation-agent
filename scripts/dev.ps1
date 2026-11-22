$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Assert-WorkbenchVenv
& $VenvPython -m uvicorn workbench.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir $ProjectRoot
