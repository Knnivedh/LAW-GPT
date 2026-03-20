@echo off
echo ============================================================
echo STARTING LAW-GPT SERVERS
echo ============================================================
echo.
echo This will start both servers in separate windows.
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3001
echo.
echo NOTE: Backend may take 30-60 seconds to initialize!
echo.

cd /d "%~dp0"

echo.
echo Starting Backend Server...
start "Backend Server - Port 5000" cmd /k "cd /d "%~dp0" && cd kaanoon_test && python advanced_rag_api_server.py"

timeout /t 3 /nobreak >nul

echo Starting Frontend Server...
start "Frontend Server - Port 3001" cmd /k "cd /d "%~dp0" && cd frontend && npm run dev"

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

