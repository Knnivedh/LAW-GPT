@echo off
REM Set NewsAPI Key for LAW-GPT
SET NEWSAPI_KEY=27d5439e1c86430fa7190244cd6238fb

REM Navigate to backend directory
cd /d "%~dp0kaanoon_test"

REM Start the backend server
echo ============================================
echo STARTING BACKEND SERVER (Port 5000)
echo WITH ULTRA WEB SEARCH ENABLED
echo - Google News RSS: Active
echo - NewsAPI: Active (100 req/day)
echo - Reddit RSS: Active
echo - Wikipedia: Active
echo - DuckDuckGo: Active
echo ============================================
echo.
echo Starting Python server...
python comprehensive_accuracy_test_server.py

pause
