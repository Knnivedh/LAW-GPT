@echo off
setlocal
title Cloudflare Tunnel - Share LAW-GPT

echo ========================================================
echo   LAW-GPT Client Share Tool
echo ========================================================
echo.

:: Check if cloudflared is in PATH
where cloudflared >nul 2>nul
if %errorlevel% EQU 0 (
    echo [OK] cloudflared found in system PATH.
    set CMD=cloudflared
    goto :START_TUNNEL
)

:: Check if cloudflared.exe exists in current directory
if exist "cloudflared.exe" (
    echo [OK] cloudflared.exe found in current directory.
    set CMD=cloudflared.exe
    goto :START_TUNNEL
)

:: Download cloudflared if not found
echo [INFO] cloudflared not found. Downloading standalone executable...
echo [INFO] Downloading from https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe...
powershell -Command "Invoke-WebRequest -Uri https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile cloudflared.exe"

if exist "cloudflared.exe" (
    echo [SUCCESS] Download complete.
    set CMD=cloudflared.exe
) else (
    echo [ERROR] Failed to download cloudflared. Please check your internet connection.
    pause
    exit /b 1
)

:START_TUNNEL
echo.
echo [INFO] Starting Cloudflare Tunnel for http://localhost:3001...
echo.
echo ************************************************************
echo *  COPY THE URL ENDING IN .trycloudflare.com BELOW         *
echo *  AND SEND IT TO YOUR CLIENT.                             *
echo ************************************************************
echo.

%CMD% tunnel --url http://localhost:3001

pause
