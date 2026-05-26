@echo off
setlocal
chcp 65001 >nul
title Prism Server Launcher
REM Prism - Quick Start Script (with first-run guide)

echo ================================================
echo  Prism v1.4.1 - Quick Start
echo ================================================
echo.

REM ===== Browser preference (v1.3: default auto-open) =====
REM Delete .auto_open_no file to enable auto-open
if exist ".auto_open_no" (
    set OPEN_BROWSER=0
) else (
    set OPEN_BROWSER=1
)

:START_SERVER
REM ===== Detect Python (v1.3: actual execution test) =====
echo [1/4] Checking Python...
set PYTHON_CMD=

REM Try py launcher first (handles multiple versions well)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :PYTHON_FOUND
)

REM Try python (actual execution test, avoids MS Store alias)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :PYTHON_FOUND
)

REM Try python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :PYTHON_FOUND
)

REM Not found
echo.
echo [WARNING] Python not detected!
echo.
echo Please select installation method:
echo   [1] Auto install (using winget, requires Windows 10/11)
echo   [2] Manual download (open Python website)
echo   [3] Cancel
echo.
choice /C 123 /N /M "Enter option (1, 2, or 3): "
if errorlevel 3 goto :CANCEL
if errorlevel 2 goto :MANUAL_PYTHON
if errorlevel 1 goto :AUTO_PYTHON

:PYTHON_FOUND
echo Found Python: %PYTHON_CMD%
goto :CHECK_FLASK

:AUTO_PYTHON
echo.
echo Installing Python 3.12 via winget...
winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 (
    echo [ERROR] winget installation failed, please install Python manually.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.
echo ================================================
echo  Python installed successfully!
echo  IMPORTANT: Please CLOSE this window and
echo  run start.bat again for PATH to take effect.
echo ================================================
pause
exit /b 0

:MANUAL_PYTHON
echo Opening Python download page...
start https://www.python.org/downloads/
echo.
echo After installation, please run start.bat again.
echo (Make sure to check "Add Python to PATH" during install)
pause
exit /b 0

:CANCEL
echo Cancelled.
pause
exit /b 0

:CHECK_FLASK
REM ===== Check dependencies (Flask + Pillow) =====
echo [2/4] Checking dependencies...
%PYTHON_CMD% -c "import flask; import PIL" 2>nul
if %errorlevel% neq 0 (
    echo First run, installing dependencies...
    
    REM Strategy A: Try local offline packages first (wheels/)
    if exist "wheels\*.whl" (
        echo Found local packages, trying offline install...
        %PYTHON_CMD% -m pip install --user --no-index --find-links=wheels flask pillow 2>nul
        if %errorlevel% equ 0 (
            echo Offline install successful!
            goto :DEPS_OK
        )
        echo Offline install failed, trying online...
    )
    
    REM Strategy B: Online install (--user to avoid permission issues)
    echo Installing online...
    %PYTHON_CMD% -m pip install --user -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Dependency installation failed!
        echo Possible causes: network issues / Python version issues
        pause
        exit /b 1
    )
    
    REM Try Pillow separately (for thumbnail feature)
    %PYTHON_CMD% -c "import PIL" 2>nul
    if %errorlevel% neq 0 (
        echo [NOTE] Pillow install failed, thumbnails will be disabled.
    )
) else (
    echo Dependencies ready
)

:DEPS_OK

REM ===== Check port =====
REM v1.4.2: Changed to port 8000 (Windows reserves 4913-5012 for Hyper-V)
set PORT=8000
echo [3/4] Checking port %PORT%...
netstat -ano | findstr :%PORT% | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo Found process using port %PORT% - closing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    echo Old process closed
) else (
    echo Port %PORT% available
)

REM ===== Start Flask =====
echo [4/4] Starting server...
echo.

if "%OPEN_BROWSER%"=="1" (
    start "" http://127.0.0.1:%PORT%
    echo Browser opened: http://127.0.0.1:%PORT%
) else (
    echo Please open browser and visit: http://127.0.0.1:%PORT%
)

echo.
echo ================================================
echo  Server started! Press Ctrl+C to stop
echo ================================================
echo.

%PYTHON_CMD% app.py

echo.
echo Server stopped
pause
