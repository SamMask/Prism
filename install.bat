@echo off
chcp 65001 >nul
echo ========================================
echo   Prism - Installation Script
echo ========================================
echo.

REM ===== Detect Python (v1.3: actual execution test) =====
echo [1/3] Checking Python...
set PYTHON_CMD=

REM Try py launcher first
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
echo  run install.bat again for PATH to take effect.
echo ================================================
pause
exit /b 0

:MANUAL_PYTHON
echo Opening Python download page...
start https://www.python.org/downloads/
echo.
echo After installation, please run install.bat again.
echo (Make sure to check "Add Python to PATH" during install)
pause
exit /b 0

:CANCEL
echo Cancelled.
pause
exit /b 0

:PYTHON_FOUND
echo Found Python: %PYTHON_CMD%

echo.
echo [2/3] Installing dependencies...
%PYTHON_CMD% -m pip install --user -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo Please check your network connection and try again.
    pause
    exit /b 1
)

REM ===== Auto-install Offline Wheels (v1.4.1) =====
if exist "wheels\*.whl" (
    echo.
    echo [2.5/3] Found offline packages, installing...
    for %%f in (wheels\*.whl) do (
        echo   - Installing %%~nxf...
        %PYTHON_CMD% -m pip install --user "%%f" >nul
        if errorlevel 1 echo     [WARNING] Failed to install %%~nxf
    )
)

echo.
echo [3/3] Starting server...
echo.
echo Server will start at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.

%PYTHON_CMD% app.py

pause
