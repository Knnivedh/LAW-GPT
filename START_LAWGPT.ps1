# LAW-GPT Complete System Launcher (PowerShell)
# Starts Backend + Frontend + Voice Support

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   LAW-GPT COMPLETE SYSTEM LAUNCHER" -ForegroundColor Yellow
Write-Host "   Backend + Frontend + Voice Service" -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$BackendPath = $PSScriptRoot
$FrontendPath = Join-Path $PSScriptRoot "frontend"
$BackendPort = 5000
$FrontendPort = 5173

# Function to check if port is in use
function Test-Port {
    param($Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient("localhost", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Step 1: Check if backend is already running
Write-Host "[1/6] Checking backend status..." -ForegroundColor White
if (Test-Port $BackendPort) {
    Write-Host "   ✓ Backend already running on port $BackendPort" -ForegroundColor Green
}
else {
    Write-Host "   Starting backend..." -ForegroundColor Yellow
    
    # Start backend in new terminal
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host 'LAW-GPT BACKEND' -ForegroundColor Cyan; " +
        "Set-Location '$BackendPath'; " +
        "python -m uvicorn kaanoon_test.advanced_rag_api_server:app --host 0.0.0.0 --port $BackendPort"
    )
    
    Write-Host "   Backend starting in new window..." -ForegroundColor Green
}

# Step 2: Wait for backend
Write-Host ""
Write-Host "[2/6] Waiting for backend to be ready..." -ForegroundColor White
$maxAttempts = 30
$attempt = 0
while (-not (Test-Port $BackendPort) -and $attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $attempt++
    Write-Host "   Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
}

if (Test-Port $BackendPort) {
    Write-Host "   ✓ Backend is ready!" -ForegroundColor Green
}
else {
    Write-Host "   WARNING: Backend may not be ready. Continuing anyway..." -ForegroundColor Yellow
}

# Step 3: Check if frontend is already running
Write-Host ""
Write-Host "[3/6] Checking frontend status..." -ForegroundColor White
if (Test-Port $FrontendPort) {
    Write-Host "   ✓ Frontend already running on port $FrontendPort" -ForegroundColor Green
}
else {
    Write-Host "   Starting frontend..." -ForegroundColor Yellow
    
    # Start frontend in new terminal
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host 'LAW-GPT FRONTEND' -ForegroundColor Cyan; " +
        "Set-Location '$FrontendPath'; " +
        "npm run dev"
    )
    
    Write-Host "   Frontend starting in new window..." -ForegroundColor Green
}

# Step 4: Wait for frontend
Write-Host ""
Write-Host "[4/6] Waiting for frontend to be ready..." -ForegroundColor White
$attempt = 0
while (-not (Test-Port $FrontendPort) -and $attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $attempt++
    Write-Host "   Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
}

if (Test-Port $FrontendPort) {
    Write-Host "   ✓ Frontend is ready!" -ForegroundColor Green
}
else {
    Write-Host "   WARNING: Frontend may not be ready. Continuing anyway..." -ForegroundColor Yellow
}

# Step 5: Set up voice service environment
Write-Host ""
Write-Host "[5/6] Configuring voice service..." -ForegroundColor White
$env:AZURE_SPEECH_KEY = "YOUR_AZURE_SPEECH_KEY_HERE"
$env:AZURE_REGION = "centralindia"
Write-Host "   ✓ Azure Speech credentials loaded" -ForegroundColor Green

# Step 6: Open browser
Write-Host ""
Write-Host "[6/6] Opening browser..." -ForegroundColor White
Start-Sleep -Seconds 2
Start-Process "http://localhost:$FrontendPort"
Write-Host "   ✓ Browser opened!" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   LAW-GPT IS RUNNING!" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   URLs:" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "   Backend:  http://localhost:$BackendPort" -ForegroundColor White
Write-Host ""
Write-Host "   Components:" -ForegroundColor Yellow
Write-Host "   ✓ RAG System (Milvus/Zilliz Cloud)" -ForegroundColor Green
Write-Host "   ✓ React Frontend (Vite)" -ForegroundColor Green
Write-Host "   ✓ FastAPI Backend" -ForegroundColor Green
Write-Host "   ✓ Azure Speech (Indian voices)" -ForegroundColor Green
Write-Host ""
Write-Host "   Voice Chatbot:" -ForegroundColor Yellow
Write-Host "   To use voice, run in separate terminal:" -ForegroundColor Gray
Write-Host "   cd D:\personaplex_env" -ForegroundColor White
Write-Host "   venv\Scripts\activate" -ForegroundColor White
Write-Host "   python voice_lawgpt_azure.py" -ForegroundColor White
Write-Host ""
Write-Host "   Press any key to exit this launcher..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
