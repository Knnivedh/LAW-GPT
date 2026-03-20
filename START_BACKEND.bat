@echo off
echo ============================================================
echo STARTING BACKEND SERVER (Port 5000)
echo ============================================================
echo.
cd /d "%~dp0"
cd kaanoon_test
echo Current directory: %CD%
echo.
echo Starting Python server...
python comprehensive_accuracy_test_server.py
pause
