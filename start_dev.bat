@echo off
chcp 65001 >nul
REM Local Insight - 開發環境啟動腳本
REM 自動清理舊的 Python 進程，避免端口衝突

echo ================================================
echo  Local Insight - 開發環境啟動腳本
echo ================================================
echo.
echo [0/3] 清理 Python 快取...
del /S /Q *.pyc >nul 2>&1
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1
echo 快取已清理

REM 1. 檢查並關閉佔用 5000 端口的進程
echo [1/3] 檢查 5000 端口...
netstat -ano | findstr :5000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo 發現佔用 5000 端口的進程 - 正在關閉...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    echo 舊進程已關閉
) else (
    echo 5000 端口未被佔用
)

REM 2. 等待 1 秒讓系統釋放端口
echo [2/3] 等待系統釋放端口...
timeout /t 1 /nobreak >nul

REM 3. 啟動 Flask 應用
echo [3/3] 啟動 Flask 應用...
echo.
echo ================================================
echo  Flask 開發服務器已啟動
echo  URL: http://127.0.0.1:5000
echo  按 Ctrl+C 停止服務器
echo ================================================
echo.

REM 設置環境變數並啟動
set FLASK_DEBUG=True
python app.py

REM 清理
echo.
echo 服務器已停止
pause
