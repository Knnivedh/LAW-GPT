@echo off
echo ============================================================
echo STARTING LAW-GPT SYSTEM
echo ============================================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3001
echo.
echo NOTE: Backend takes 30-60 seconds to initialize
echo       Frontend ready in 5-10 seconds
echo.

REM Kill any existing processes on ports 5000 and 3001
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001"') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

REM Start Backend
echo.
echo [1/2] Starting Backend Server...
start "LAW-GPT Backend (Port 5000)" cmd /k "cd /d %~dp0kaanoon_test && python advanced_rag_api_server.py"
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [2/2] Starting Frontend Server...
start "LAW-GPT Frontend (Port 3001)" cmd /k "cd /d %~dp0frontend && "C:\Program Files\nodejs\npm.cmd" run dev"

echo.
echo ============================================================
echo SERVERS STARTING IN SEPARATE WINDOWS
echo ============================================================
echo.
echo Please wait 30-60 seconds for full initialization
echo Then open: http://localhost:3001
echo.
pause
