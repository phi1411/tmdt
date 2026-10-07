$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $projectRoot
try {
    $pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
    $entryPath = Join-Path $projectRoot 'backend/run.py'
    $runtimeConfig = (& $pythonPath -c "import sys,json;sys.path.insert(0,'backend');from app.config import load_config;c=load_config();print(json.dumps({'host':c['API_HOST'],'port':c['API_PORT']}))") | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Backend environment configuration is invalid' }
    $listeners = Get-NetTCPConnection -LocalPort $runtimeConfig.port -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $(($listeners | Select-Object -First 1).OwningProcess)"
        if (!$owner.CommandLine.Contains($entryPath)) { throw 'Backend port belongs to another process; refusing to replace it' }
        Write-Output 'Project backend is already running.'
    } else {
        $localRoot = Join-Path $projectRoot '.local/backend'
        New-Item -ItemType Directory -Path $localRoot -Force | Out-Null
        $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-X', 'utf8', ('"' + $entryPath + '"')) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localRoot 'stdout.log') -RedirectStandardError (Join-Path $localRoot 'stderr.log')
        $serverProcess.Id | Set-Content -LiteralPath (Join-Path $localRoot 'server.pid')
        Write-Output "Started local backend PID $($serverProcess.Id)."
    }
    $url = "http://$($runtimeConfig.host):$($runtimeConfig.port)/api/v1/health"
    $ready = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri $url -TimeoutSec 2
            if ($health.data.status -eq 'ok') { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$ready) { throw 'Backend health did not become ready; see .local/backend/stderr.log' }
    Write-Output "Health ready: $url"
} finally { Pop-Location }
