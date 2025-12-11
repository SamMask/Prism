@echo off
chcp 65001 >nul
REM Local Insight - 快速啟動腳本

echo ================================================
echo  Local Insight v1.0 - Quick Start
echo ================================================
echo.

REM 檢查並關閉佔用 5000 端口的進程
echo [1/2] 檢查 5000 端口...
netstat -ano | findstr :5000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo 發現佔用 5000 端口的進程 - 正在關閉...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    echo 舊進程已關閉
) else (
    echo 5000 端口可用
)

REM 啟動 Flask 應用
echo [2/2] 啟動服務器...
echo.
echo ================================================
echo  服務器已啟動！
echo  請開啟瀏覽器訪問: http://127.0.0.1:5000
echo  按 Ctrl+C 停止服務器
echo ================================================
echo.

python app.py

echo.
echo 服務器已停止
pause
