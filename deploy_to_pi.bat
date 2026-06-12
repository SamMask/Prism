@echo off
REM Prism Go primary Raspberry Pi deploy wrapper.
REM Uses scripts\go_primary_pi_live_ops.ps1; no Python package install path.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\go_primary_pi_live_ops.ps1" -Mode Cutover
exit /b %ERRORLEVEL%
