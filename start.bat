@echo off
title BinGO — Smart Waste Platform Launcher
color 0A
echo.
echo  ======================================================
echo   BinGO  ^|  Smart Waste Management & AI Platform
echo  ======================================================
echo.

set SCRIPT_DIR=%~dp0
set INDEX_FILE=%SCRIPT_DIR%frontend\index.html

if not exist "%INDEX_FILE%" (
    echo  [ERROR] frontend\index.html not found!
    echo  Make sure start.bat is in the root project folder.
    echo.
    pause
    exit /b 1
)

echo  [1/3] Checking Docker status...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [WARNING] Docker Desktop is not running or not installed.
    echo  Launching BinGO in standalone Demo Mode (Offline)...
    echo.
    start "" "%INDEX_FILE%"
    echo  [OK] BinGO App opened in browser!
    echo.
    pause
    exit /b 0
)

echo  [2/3] Starting BinGO Docker containers in background...
echo  Running: docker compose up -d
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo  [WARNING] Could not start Docker containers automatically.
    echo  Launching BinGO in Demo Mode fallback...
    start "" "%INDEX_FILE%"
) else (
    echo.
    echo  [3/3] Backend services starting!
    echo  - Nginx Gateway: http://localhost
    echo  - API Endpoint:  http://localhost/api/v1
    echo.
    echo  Opening BinGO in browser...
    timeout /t 2 >nul
    start "" "http://localhost"
)

echo.
echo  [OK] BinGO is running!
echo  Press any key to close launcher window...
pause > nul
