@echo off
setlocal
chcp 65001 >nul
title Prism Go Primary Launcher

echo ================================================
echo  Prism - Go Primary Runtime
echo ================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_go_primary.ps1" %*
exit /b %ERRORLEVEL%
