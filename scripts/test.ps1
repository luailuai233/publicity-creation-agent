$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime-env.ps1')

$VenvPython = Assert-WorkbenchVenv
$TestTemp = Join-Path $env:TEMP ("pytest-" + [Guid]::NewGuid().ToString("N"))
& $VenvPython -m pytest --basetemp $TestTemp @args
exit $LASTEXITCODE
