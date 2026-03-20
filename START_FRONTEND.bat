@echo off
echo ============================================================
echo STARTING FRONTEND SERVER (Port 3001)
echo ============================================================
echo.
cd /d "%~dp0"
cd frontend
echo Current directory: %CD%
echo.
echo Starting npm dev server...
call npm run dev
pause
