# PowerShell script to start Expert Legal RAG System
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "STARTING EXPERT LEGAL RAG SYSTEM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3001" -ForegroundColor Green
Write-Host ""
Write-Host "NOTE: Backend may take 30-60 seconds to initialize!" -ForegroundColor Yellow
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Starting Backend Server..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "cd /d `"$scriptPath\kaanoon_test`" && python advanced_rag_api_server.py" -WindowStyle Normal

Start-Sleep -Seconds 5

Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "cd /d `"$scriptPath\frontend`" && npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Both servers are starting in separate windows!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Please check the windows for startup messages." -ForegroundColor Yellow
Write-Host "Backend may take 30-60 seconds to load the database." -ForegroundColor Yellow
Write-Host ""

