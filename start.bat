@echo off
chcp 65001 >nul
REM Prism - 快速啟動腳本 (含首次引導)

echo ================================================
echo  Prism v1.2 - Quick Start
echo ================================================
echo.

REM ===== 首次啟動引導 =====
REM 使用獨立檔案標記，避免變數問題

if exist ".auto_open_yes" goto :AUTO_OPEN
if exist ".auto_open_no" goto :MANUAL_OPEN

REM 首次執行詢問
echo ================================================
echo  歡迎使用 Prism！
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
REM ===== 檢查 Python 是否已安裝 =====
echo [1/4] 檢查 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [警告] 未偵測到 Python！
    echo.
    echo 請選擇安裝方式：
    echo   [1] 自動安裝 (使用 winget，需要 Windows 10/11)
    echo   [2] 手動下載 (開啟 Python 官網)
    echo   [3] 取消
    echo.
    choice /C 123 /N /M "請輸入選項 (1, 2, 或 3): "
    if errorlevel 3 goto :CANCEL
    if errorlevel 2 goto :MANUAL_PYTHON
    if errorlevel 1 goto :AUTO_PYTHON
)
goto :CHECK_FLASK

:AUTO_PYTHON
echo.
echo 正在使用 winget 安裝 Python 3.12...
winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 (
    echo [錯誤] winget 安裝失敗，請手動安裝 Python。
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.
echo Python 安裝完成！請關閉此視窗，重新執行 start.bat。
pause
exit /b 0

:MANUAL_PYTHON
echo 正在開啟 Python 下載頁面...
start https://www.python.org/downloads/
echo.
echo 安裝完成後，請重新執行 start.bat。
echo (安裝時請務必勾選 "Add Python to PATH")
pause
exit /b 0

:CANCEL
echo 已取消。
pause
exit /b 0

:CHECK_FLASK
REM ===== 檢查 Flask 是否已安裝 =====
echo [2/4] 檢查依賴...
python -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo Flask 未安裝，正在自動安裝依賴...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [錯誤] 安裝失敗！請確認 Python 已正確安裝。
        pause
        exit /b 1
    )
    echo 依賴安裝完成！
) else (
    echo 依賴已就緒
)

REM ===== 檢查端口 =====
echo [3/4] 檢查 5000 端口...
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
echo [4/4] 啟動伺服器...
echo.

if "%OPEN_BROWSER%"=="1" (
    start "" http://127.0.0.1:5000
    echo 瀏覽器已開啟: http://127.0.0.1:5000
) else (
    echo 請手動開啟瀏覽器訪問: http://127.0.0.1:5000
)

echo.
echo ================================================
echo  伺服器已啟動！按 Ctrl+C 停止
echo ================================================
echo.

python app.py

echo.
echo 伺服器已停止
pause
