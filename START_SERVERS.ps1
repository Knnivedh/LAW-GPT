# Start LAW-GPT Backend and Frontend
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "STARTING LAW-GPT SERVERS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend Server (Port 5000)..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "kaanoon_test"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python advanced_rag_api_server.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend Server (Port 3001)..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "frontend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; node node_modules/vite/bin/vite.js --port 3001" -WindowStyle Normal

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "SERVERS STARTING IN SEPARATE WINDOWS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3001" -ForegroundColor White
Write-Host ""
Write-Host "NOTE: Backend may take 30-60 seconds to initialize!" -ForegroundColor Gray
Write-Host "      Frontend should be ready in 5-10 seconds." -ForegroundColor Gray
Write-Host ""
