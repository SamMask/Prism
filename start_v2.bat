@echo off
REM ===================================================================
REM Prism - Go Primary Production Launcher
REM ===================================================================

echo ===================================
echo   Prism - Go Primary Runtime
echo ===================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_go_primary.ps1" %*
exit /b %ERRORLEVEL%
