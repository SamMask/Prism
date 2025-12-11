@echo off
chcp 65001 >nul
REM Local Insight - 快速啟動腳本 (含首次引導)

echo ================================================
echo  Local Insight v1.0 - Quick Start
echo ================================================
echo.

REM ===== 首次啟動引導 =====
REM 使用獨立檔案標記，避免變數問題

if exist ".auto_open_yes" goto :AUTO_OPEN
if exist ".auto_open_no" goto :MANUAL_OPEN

REM 首次執行詢問
echo ================================================
echo  歡迎使用 Local Insight！
echo  請選擇啟動方式：
echo ================================================
echo.
echo   [1] 自動開啟瀏覽器 (推薦)
echo   [2] 手動開啟 http://127.0.0.1:5000
echo.
choice /C 12 /N /M "請輸入選項 (1 或 2): "
if errorlevel 2 goto :SAVE_MANUAL
if errorlevel 1 goto :SAVE_AUTO

:SAVE_AUTO
del ".auto_open_no" 2>nul
echo 1 > ".auto_open_yes"
echo.
echo 設定已儲存！刪除 .auto_open_yes 可重設偏好。
echo.
goto :AUTO_OPEN

:SAVE_MANUAL
del ".auto_open_yes" 2>nul
echo 0 > ".auto_open_no"
echo.
echo 設定已儲存！刪除 .auto_open_no 可重設偏好。
echo.
goto :MANUAL_OPEN

:AUTO_OPEN
set OPEN_BROWSER=1
goto :START_SERVER

:MANUAL_OPEN
set OPEN_BROWSER=0
goto :START_SERVER

:START_SERVER
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
echo [2/2] 啟動服務器...
echo.

if "%OPEN_BROWSER%"=="1" (
    start "" http://127.0.0.1:5000
    echo 瀏覽器已開啟: http://127.0.0.1:5000
) else (
    echo 請手動開啟瀏覽器訪問: http://127.0.0.1:5000
)

echo.
echo ================================================
echo  服務器已啟動！按 Ctrl+C 停止
echo ================================================
echo.

python app.py

echo.
echo 服務器已停止
pause
