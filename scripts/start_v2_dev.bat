@echo off
REM ===================================================================
REM Prism V2 - Development Mode Launcher
REM Starts Go primary runtime and Vite Dev Server.
REM ===================================================================

echo ===================================
echo   Prism V2 - Development Mode
echo ===================================
echo.

if not exist "frontend\node_modules" (
    echo [WARN] node_modules not found. Running npm install...
    cd frontend
    call npm install
    cd ..
)

echo [1/2] Starting Go Primary Backend (Port 5004)...
start "Prism Go Primary" cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_go_primary.ps1"

timeout /t 2 /nobreak > nul

echo [2/2] Starting Vite Dev Server (Port 5173)...
cd frontend
call npm run dev

REM In dev mode, access the app via http://localhost:5173.
REM The Vite dev server proxies /api and /static requests to Go primary on port 5004.
