# Deploy latest code from GitHub and restart server
# Usage: powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1

$ProjectDir = "C:\wechat-ai-assistant"
$Port = 9000

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $msg"
}

Set-Location $ProjectDir

# Pull latest code
Write-Log "Pulling latest code..."
git pull origin main --tags
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: git pull failed"
    exit 1
}

# Install/update dependencies
Write-Log "Updating dependencies..."
& "$ProjectDir\venv\Scripts\pip.exe" install -r requirements.txt -q

# Rebuild FAISS index (in case knowledge base changed)
Write-Log "Rebuilding search index..."
& "$ProjectDir\venv\Scripts\python.exe" scripts\build_index.py

# Kill existing server process on the port
$proc = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($proc) {
    foreach ($pid in $proc) {
        Write-Log "Killing process $pid on port $Port..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Restart server
Write-Log "Starting server..."
$env:HF_HUB_OFFLINE = "1"
Start-Process -FilePath "$ProjectDir\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Port" `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden

Start-Sleep -Seconds 10

# Health check
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:$Port/health" -TimeoutSec 5
    if ($resp.StatusCode -eq 200) {
        Write-Log "Deploy complete. Server is healthy."
    } else {
        Write-Log "WARNING: Server returned status $($resp.StatusCode)"
    }
} catch {
    Write-Log "WARNING: Health check failed — server may still be loading"
}
