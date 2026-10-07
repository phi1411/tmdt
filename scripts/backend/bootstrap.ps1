$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $projectRoot
try {
    $pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Create the Python3.12 environment with scripts/db/bootstrap.ps1 first' }
    $dependencyFile = 'backend/requirements-dev.txt'
    if (Test-Path -LiteralPath 'backend/requirements-dev.lock.txt') { $dependencyFile = 'backend/requirements-dev.lock.txt' }
    & $pythonPath -m pip install -r $dependencyFile
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed' }
    & $pythonPath (Join-Path $PSScriptRoot 'create_env.py')
    if ($LASTEXITCODE -ne 0) { throw 'Development environment preparation failed' }
    & $pythonPath -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependencies are inconsistent' }
} finally { Pop-Location }
