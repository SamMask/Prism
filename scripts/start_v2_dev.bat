@echo off
REM ===================================================================
REM Prism V2 - Development Mode Launcher
REM 同時啟動 Flask Backend 和 Vite Dev Server
REM ===================================================================

echo ===================================
echo   Prism V2 - Development Mode
echo ===================================
echo.

REM Check if frontend/node_modules exists
if not exist "frontend\node_modules" (
    echo [WARN] node_modules not found. Running npm install...
    cd frontend
    call npm install
    cd ..
)

REM Start Flask backend in background
echo [1/2] Starting Flask Backend (Port 5000)...
start "Prism Backend" cmd /c "python app.py"

REM Wait for Flask to start
timeout /t 2 /nobreak > nul

REM Start Vite dev server
echo [2/2] Starting Vite Dev Server (Port 5173)...
cd frontend
call npm run dev

REM Note: In dev mode, access the app via http://localhost:5173
REM The Vite dev server will proxy /api requests to Flask on port 5000
