param([string]$MongodPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$localRoot = Join-Path $projectRoot '.local/mongodb'
New-Item -ItemType Directory -Path (Join-Path $localRoot 'data') -Force | Out-Null
if (!$MongodPath) {
    $MongodPath = Join-Path $projectRoot '.tools/mongodb/mongodb-win32-x86_64-windows-8.0.32/bin/mongod.exe'
}
if (!(Test-Path -LiteralPath $MongodPath)) { throw 'MongoDB binary missing. Run bootstrap.ps1 first.' }
$listeners = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $running = Get-Process -Id ($listeners | Select-Object -First 1).OwningProcess
    if ($running.Path -ne (Resolve-Path -LiteralPath $MongodPath).Path) { throw 'Port 27017 belongs to another process; refusing to replace it.' }
    Write-Output 'Project MongoDB is already running.'
} else {
    $configPath = Join-Path $localRoot 'mongod.yml'
    $dataPath = (Join-Path $localRoot 'data').Replace('\','/')
    $logPath = (Join-Path $localRoot 'mongod.log').Replace('\','/')
    @"
storage:
  dbPath: "$dataPath"
  engine: wiredTiger
  wiredTiger:
    engineConfig:
      cacheSizeGB: 0.25
systemLog:
  destination: file
  path: "$logPath"
  logAppend: true
net:
  bindIp: localhost
  port: 27017
replication:
  replSetName: rs0
  oplogSizeMB: 128
"@ | Set-Content -LiteralPath $configPath -Encoding utf8
    $mongoProcess = Start-Process -FilePath $MongodPath -ArgumentList @('--config', ('"' + $configPath + '"')) -WindowStyle Hidden -PassThru
    $mongoProcess.Id | Set-Content -LiteralPath (Join-Path $localRoot 'mongod.pid')
    Write-Output "Started project mongod PID $($mongoProcess.Id) on localhost:27017."
}
& (Join-Path $projectRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'init_replica.py')
if ($LASTEXITCODE -ne 0) { throw 'Replica initialization failed. See .local/mongodb/mongod.log' }
