@echo off
chcp 65001 >nul
REM Prism Portable - Quick Start Script
REM Uses embedded Python, no system Python required

cd /d "%~dp0"

echo ================================================
echo  Prism v1.3 - Portable Edition
echo ================================================
echo.

REM ===== Browser preference (v1.3: default auto-open) =====
REM Create .auto_open_no file to disable auto-open
if exist ".auto_open_no" (
    set OPEN_BROWSER=0
) else (
    set OPEN_BROWSER=1
)

REM ===== Check embedded Python =====
if not exist "python\python.exe" (
    echo [ERROR] Embedded Python not found!
    echo Please make sure python\ folder exists.
    pause
    exit /b 1
)

REM ===== Check port =====
echo [1/2] Checking port 5000...
netstat -ano | findstr :5000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo Found process using port 5000 - closing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    echo Old process closed
) else (
    echo Port 5000 available
)

REM ===== Start Flask =====
echo [2/2] Starting server...
echo.

if "%OPEN_BROWSER%"=="1" (
    REM v1.3: Delay browser open, wait for server startup
    start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"
    echo Browser will open in 3 seconds: http://127.0.0.1:5000
) else (
    echo Please open browser and visit: http://127.0.0.1:5000
)

echo.
echo ================================================
echo  Server started! Press Ctrl+C to stop
echo ================================================
echo.

python\python.exe app.py

echo.
echo Server stopped
pause
