@echo off
echo ========================================
echo   Local Insight - Installation Script
echo ========================================
echo.

echo [1/2] Installing Python dependencies...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo Please make sure Python and pip are installed.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting server...
echo.
echo Server will start at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.

python app.py

pause
