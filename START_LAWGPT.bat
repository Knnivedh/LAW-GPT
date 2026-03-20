@echo off
REM LAW-GPT Complete System Launcher
REM Starts Backend + Frontend + Opens Browser

echo.
echo ====================================================
echo    LAW-GPT COMPLETE SYSTEM LAUNCHER
echo    Backend (RAG + Milvus) + Frontend (React)
echo ====================================================
echo.

REM Kill any existing processes on ports 5000 and 5173
echo [1/5] Cleaning up old processes...
netstat -ano | findstr ":5000" > nul 2>&1 && taskkill /F /PID $(for /f "tokens=5" %a in ('netstat -ano ^| findstr ":5000"') do echo %a) > nul 2>&1
netstat -ano | findstr ":5173" > nul 2>&1 && taskkill /F /PID $(for /f "tokens=5" %a in ('netstat -ano ^| findstr ":5173"') do echo %a) > nul 2>&1

REM Start Backend in new window
echo [2/5] Starting Backend (Port 5000)...
start "LAW-GPT Backend" cmd /k "cd /d C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT && python -m uvicorn kaanoon_test.advanced_rag_api_server:app --host 0.0.0.0 --port 5000"

REM Wait for backend to initialize
echo [3/5] Waiting for backend to initialize (15 seconds)...
timeout /t 15 /nobreak > nul

REM Start Frontend in new window
echo [4/5] Starting Frontend (Port 5173)...
start "LAW-GPT Frontend" cmd /k "cd /d C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\frontend && npm run dev"

REM Wait for frontend to start
echo [5/5] Waiting for frontend to start (10 seconds)...
timeout /t 10 /nobreak > nul

REM Open browser
echo Opening LAW-GPT in browser...
start http://localhost:5173

echo.
echo ====================================================
echo    LAW-GPT IS RUNNING!
echo ====================================================
echo.
echo    Frontend: http://localhost:5173
echo    Backend:  http://localhost:5000
echo.
echo    Voice Chatbot: Run voice_lawgpt_azure.py separately
echo.
echo    Press any key to close this launcher...
pause > nul
