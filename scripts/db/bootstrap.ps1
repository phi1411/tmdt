param([string]$Python312 = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Path '.tools' -Force | Out-Null
    $archive = Join-Path $projectRoot '.tools/mongodb-8.0.32.zip'
    $checksum = "$archive.sha256"
    $url = 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.32.zip'
    if (!(Test-Path -LiteralPath $archive)) { Invoke-WebRequest -Uri $url -OutFile $archive }
    if (!(Test-Path -LiteralPath $checksum)) { Invoke-WebRequest -Uri "$url.sha256" -OutFile $checksum }
    $expectedHash = ((Get-Content -LiteralPath $checksum -Raw).Trim() -split '\s+')[0]
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) { throw 'MongoDB archive checksum mismatch' }
    if (!(Test-Path -LiteralPath '.tools/mongodb')) { Expand-Archive -LiteralPath $archive -DestinationPath '.tools/mongodb' }
    if (!$Python312) {
        $uvPath = Join-Path $projectRoot '.tools/python-tools/bin/uv.exe'
        if (!(Test-Path -LiteralPath $uvPath)) {
            python -m pip install --target .tools/python-tools uv==0.9.2
            if ($LASTEXITCODE -ne 0) { throw 'Installing local Python bootstrap tool failed' }
        }
        & $uvPath python install 3.12 --install-dir (Join-Path $projectRoot '.tools/python')
        if ($LASTEXITCODE -ne 0) { throw 'Installing Python 3.12 failed' }
        # Explicitly locate the runtime under the project instead of relying on PATH.
        $Python312 = (Get-ChildItem -LiteralPath '.tools/python' -Filter 'python.exe' -Recurse | Select-Object -First 1).FullName
    }
    if ((& $Python312 -c 'import sys; print(".".join(map(str,sys.version_info[:2])))') -ne '3.12') { throw 'Python 3.12 is required' }
    if (!(Test-Path -LiteralPath '.venv/Scripts/python.exe')) { & $Python312 -m venv .venv }
    $dependencyFile = 'scripts/db/requirements.txt'
    if (Test-Path -LiteralPath 'scripts/db/requirements.lock.txt') { $dependencyFile = 'scripts/db/requirements.lock.txt' }
    & '.venv/Scripts/python.exe' -m pip install -r $dependencyFile
    if ($LASTEXITCODE -ne 0) { throw 'Database dependency installation failed' }
    & (Join-Path $PSScriptRoot 'start-mongo.ps1')
} finally { Pop-Location }
