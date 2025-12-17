@echo off
REM ===================================================================
REM Prism V2 - Production Mode Launcher
REM 先編譯 React App，然後啟動 Flask 並服務 SPA
REM ===================================================================

echo ===================================
echo   Prism V2 - Production Build
echo ===================================
echo.

REM Check if frontend/node_modules exists
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Build frontend
echo [1/2] Building React Frontend...
cd frontend
call npm run build
cd ..

if not exist "frontend\dist\index.html" (
    echo [ERROR] Build failed! index.html not found.
    pause
    exit /b 1
)

echo [2/2] Starting Prism V2 Server...
echo.
echo ===================================
echo   Access: http://127.0.0.1:5000
echo ===================================
echo.

REM Start Flask with V2 mode enabled
set PRISM_V2=true
python app.py

pause
