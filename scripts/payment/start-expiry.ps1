$ErrorActionPreference = 'Stop'
$paymentProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$paymentPython = Join-Path $paymentProjectRoot '.venv/Scripts/python.exe'
$paymentEntry = Join-Path $PSScriptRoot 'expire_pending.py'
Push-Location $paymentProjectRoot
try {
    & $paymentPython -X utf8 -c "import sys;sys.path.insert(0,'backend');from app import create_app;a=create_app();a.extensions['mongo'].close()"
    if ($LASTEXITCODE -ne 0) { throw 'Expiry environment/database configuration is not ready' }
} finally { Pop-Location }
$paymentLogRoot = Join-Path $paymentProjectRoot '.local/payment'
New-Item -ItemType Directory -Path $paymentLogRoot -Force | Out-Null
$paymentPidPath = Join-Path $paymentLogRoot 'expiry.pid'
if (Test-Path -LiteralPath $paymentPidPath) {
    $paymentSavedPid = [int](Get-Content -LiteralPath $paymentPidPath)
    $paymentExisting = Get-CimInstance Win32_Process -Filter "ProcessId = $paymentSavedPid"
    if ($paymentExisting) {
        if (!$paymentExisting.CommandLine.Contains($paymentEntry)) { throw 'Saved expiry PID belongs to another process; refusing to replace it' }
        Write-Output 'Project expiry worker is already running.'
        exit 0
    }
}
$paymentWorker = Start-Process -FilePath $paymentPython -ArgumentList @('-X', 'utf8', ('"' + $paymentEntry + '"')) -WorkingDirectory $paymentProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $paymentLogRoot 'expiry.stdout.log') -RedirectStandardError (Join-Path $paymentLogRoot 'expiry.stderr.log')
$paymentWorker.Id | Set-Content -LiteralPath $paymentPidPath
Write-Output "Started expiry worker PID $($paymentWorker.Id); interval 30 seconds."
