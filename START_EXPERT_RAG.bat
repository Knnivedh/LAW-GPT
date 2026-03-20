@echo off
echo ============================================================
echo STARTING EXPERT LEGAL RAG SYSTEM
echo ============================================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3001
echo.
echo NOTE: Backend may take 30-60 seconds to initialize!
echo.

cd /d "%~dp0"

echo Stopping any existing Python servers...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo Starting Backend Server...
start "Expert RAG Backend - Port 5000" cmd /k "cd /d "%~dp0\kaanoon_test" && python advanced_rag_api_server.py"

timeout /t 5 /nobreak >nul

echo Starting Frontend Server...
start "Frontend Server - Port 3001" cmd /k "cd /d "%~dp0\frontend" && npm run dev"

echo.
echo ============================================================
echo Both servers are starting in separate windows!
echo ============================================================
echo.
echo Please check the windows for startup messages.
echo Backend may take 30-60 seconds to load the database.
echo.
echo You can close this window now.
timeout /t 5 /nobreak >nul
