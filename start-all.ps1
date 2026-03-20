# Start Both Servers
Write-Host "=" -ForegroundColor Cyan
Write-Host "Starting LAW-GPT Servers" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""

# Start Backend in new window
Write-Host "Starting Backend Server (port 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-backend.ps1"

# Wait a bit
Start-Sleep -Seconds 3

# Start Frontend in new window
Write-Host "Starting Frontend Server (port 3001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-frontend.ps1"

Write-Host ""
Write-Host "✅ Both servers are starting in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Backend may take 30-60 seconds to initialize the database." -ForegroundColor Yellow

