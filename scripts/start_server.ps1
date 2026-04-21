# WeChat AI Assistant — Auto-restart Server + Cloudflare Tunnel
# Run this script on the deployment server (friend's PC)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_server.ps1

$ProjectDir = "C:\wechat-ai-assistant"
$Port = 9000
$LogDir = "$ProjectDir\logs"
$RetryDelay = 5

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $msg"
    Add-Content "$LogDir\startup.log" "[$ts] $msg"
}

# Rotate logs if > 10MB
function Rotate-Log($path) {
    if ((Test-Path $path) -and (Get-Item $path).Length -gt 10MB) {
        $backup = "$path.$(Get-Date -Format 'yyyyMMdd-HHmmss').bak"
        Move-Item $path $backup -Force
        Write-Log "Rotated log: $path -> $backup"
    }
}

# Start uvicorn with auto-restart
function Start-Server {
    while ($true) {
        Rotate-Log "$LogDir\server.log"
        Write-Log "Starting uvicorn on port $Port..."

        $env:HF_HUB_OFFLINE = "1"
        & "$ProjectDir\venv\Scripts\python.exe" -m uvicorn app.main:app `
            --host 0.0.0.0 --port $Port `
            *>> "$LogDir\server.log"

        $exitCode = $LASTEXITCODE
        Write-Log "Server exited with code $exitCode. Restarting in ${RetryDelay}s..."
        Start-Sleep -Seconds $RetryDelay
    }
}

# Start cloudflared tunnel with auto-restart
function Start-Tunnel {
    while ($true) {
        Rotate-Log "$LogDir\tunnel.log"
        Write-Log "Starting cloudflared tunnel..."

        & "$ProjectDir\cloudflared.exe" tunnel --url "http://localhost:$Port" `
            *>> "$LogDir\tunnel.log"

        Write-Log "Tunnel exited. Restarting in ${RetryDelay}s..."
        Start-Sleep -Seconds $RetryDelay
    }
}

Write-Log "=== Starting WeChat AI Assistant ==="
Write-Log "Project: $ProjectDir"
Write-Log "Port: $Port"

Set-Location $ProjectDir

# Run server and tunnel as parallel jobs
$serverJob = Start-Job -ScriptBlock ${function:Start-Server} -ArgumentList $ProjectDir, $Port, $LogDir, $RetryDelay
$tunnelJob = Start-Job -ScriptBlock ${function:Start-Tunnel} -ArgumentList $ProjectDir, $Port, $LogDir, $RetryDelay

Write-Log "Server job: $($serverJob.Id), Tunnel job: $($tunnelJob.Id)"
Write-Log "Press Ctrl+C to stop."

try {
    while ($true) {
        Start-Sleep -Seconds 30
        # Check job health
        foreach ($job in @($serverJob, $tunnelJob)) {
            if ($job.State -eq "Failed") {
                Write-Log "WARNING: Job $($job.Id) failed. Check logs."
            }
        }
    }
} finally {
    Write-Log "Stopping jobs..."
    Stop-Job $serverJob, $tunnelJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob, $tunnelJob -Force -ErrorAction SilentlyContinue
    Write-Log "Stopped."
}
