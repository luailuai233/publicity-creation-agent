$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Assert-WorkbenchVenv
$TestTemp = Join-Path $env:TEMP ("pytest-e2e-" + [Guid]::NewGuid().ToString("N"))
& $VenvPython -m pytest --basetemp $TestTemp tests/e2e @args
exit $LASTEXITCODE
