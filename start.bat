@echo off
title BinGO — Smart Waste Management Platform Launcher
color 0A
cls
echo.
echo  ======================================================
echo   BinGO  ^|  Smart Waste Management ^& AI Platform
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

echo  [1/3] Checking environment ^& Docker status...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo  [INFO] Docker Desktop is running!
    echo  [2/3] Starting BinGO Docker containers in background...
    echo  Running: docker compose up -d
    docker compose up -d
    if %errorlevel% equ 0 (
        echo.
        echo  [3/3] Backend services started successfully!
        echo  - Nginx Gateway: http://localhost
        echo  - API Endpoint:  http://localhost/api/v1
        echo.
        echo  Opening BinGO in web browser...
        timeout /t 2 >nul
        start "" "http://localhost"
        echo.
        echo  [OK] BinGO is running in full Docker mode!
        echo  Press any key to exit launcher...
        pause >nul
        exit /b 0
    )
)

echo.
echo  [WARNING] Docker Desktop is not running or not installed.
echo  Fallback: Launching BinGO via Python Local HTTP Server...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  [OK] Python detected! Starting BinGO HTTP Server on port 3000...
    echo  Serving directory: %SCRIPT_DIR%frontend
    echo  Opening http://localhost:3000 in your browser...
    echo.
    start "" "http://localhost:3000"
    echo  ------------------------------------------------------
    echo   BinGO App running on http://localhost:3000
    echo   Press Ctrl+C or close window to stop server.
    echo  ------------------------------------------------------
    python -m http.server 3000 --directory "%SCRIPT_DIR%frontend"
    exit /b 0
)

echo.
echo  [NOTICE] Python not found. Launching BinGO frontend file directly...
start "" "%INDEX_FILE%"
echo  [OK] Opened BinGO in default browser!
echo.
pause
exit /b 0
