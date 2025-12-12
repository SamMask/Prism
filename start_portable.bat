@echo off
chcp 65001 >nul
REM Prism Portable - 免安裝啟動腳本
REM 使用內嵌的 Python，無需系統安裝 Python

cd /d "%~dp0"

echo ================================================
echo  Prism v1.2 - Portable Edition
echo ================================================
echo.

REM ===== 檢查內嵌 Python =====
if not exist "python\python.exe" (
    echo [錯誤] 找不到內嵌的 Python！
    echo 請確認 python\ 資料夾存在。
    pause
    exit /b 1
)

REM ===== 檢查端口 =====
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

REM ===== 啟動 Flask =====
echo [2/2] 啟動伺服器...
echo.

start "" http://127.0.0.1:5000
echo 瀏覽器已開啟: http://127.0.0.1:5000

echo.
echo ================================================
echo  伺服器已啟動！按 Ctrl+C 停止
echo ================================================
echo.

python\python.exe app.py

echo.
echo 伺服器已停止
pause
