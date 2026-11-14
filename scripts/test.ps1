$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
& $VenvPython -m pytest @args
exit $LASTEXITCODE
