@echo off
chcp 65001 >nul
echo ========================================
echo   Prism - Go Primary Build
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_go_runtime.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Go primary build failed.
    pause
    exit /b 1
)

echo.
echo Build complete. Start Prism with scripts\start.bat or start_v2.bat.
pause
