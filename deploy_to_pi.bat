@echo off
REM ===================================================================
REM Prism V2 - Raspberry Pi 自動部署腳本
REM Phase 8.2: 透過 SCP/SSH 發佈檔案至樹莓派並重啟服務
REM ===================================================================
REM 使用方式:
REM   1. 編輯下方設定區塊，填入您的 Pi 連線資訊
REM   2. 確認本地已設定 SSH Key (免密碼登入)
REM   3. 在本地端執行此腳本
REM ===================================================================

setlocal EnableDelayedExpansion

REM -------------------------------------------------------------------
REM 設定區塊 (請依照您的環境修改)
REM -------------------------------------------------------------------
set PI_USER=sam
set PI_HOST=prism.local
set PI_PORT=22
set PI_DEPLOY_DIR=/home/sam/prism
set PI_SERVICE_NAME=prism

REM 本地專案目錄
set LOCAL_SRC=d:\AI\Prism

REM -------------------------------------------------------------------
REM 前置檢查
REM -------------------------------------------------------------------
echo.
echo ============================================================
echo   Prism V2 - Raspberry Pi 部署工具
echo ============================================================
echo.
echo   目標主機: %PI_USER%@%PI_HOST%:%PI_PORT%
echo   部署目錄: %PI_DEPLOY_DIR%
echo   服務名稱: %PI_SERVICE_NAME%
echo.

REM 檢查 SSH 可用性
where ssh >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 SSH 命令。請確認 OpenSSH 已安裝。
    pause
    exit /b 1
)

REM 檢查 SCP 可用性
where scp >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 SCP 命令。請確認 OpenSSH 已安裝。
    pause
    exit /b 1
)

REM -------------------------------------------------------------------
REM Step 0: 連線測試
REM -------------------------------------------------------------------
echo [0/6] 測試 SSH 連線...
ssh -o ConnectTimeout=5 -p %PI_PORT% %PI_USER%@%PI_HOST% "echo OK" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 無法連線至 %PI_HOST%。請檢查:
    echo   - 樹莓派是否已開機
    echo   - 網路連線是否正常
    echo   - SSH Key 是否已設定
    echo   - 主機名稱/IP 是否正確
    pause
    exit /b 1
)
echo [OK] SSH 連線成功

REM -------------------------------------------------------------------
REM Step 1: 前端 Build (如果有變更)
REM -------------------------------------------------------------------
echo.
echo [1/6] 建置前端 (npm run build)...
cd /d "%LOCAL_SRC%\frontend"
call npm run build
if errorlevel 1 (
    echo [ERROR] 前端建置失敗！
    pause
    exit /b 1
)
echo [OK] 前端建置完成

REM -------------------------------------------------------------------
REM Step 2: 同步後端 Python 檔案
REM -------------------------------------------------------------------
echo.
echo [2/6] 同步後端檔案...

REM 核心檔案
scp -P %PI_PORT% "%LOCAL_SRC%\app.py" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/
scp -P %PI_PORT% "%LOCAL_SRC%\config.py" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/
scp -P %PI_PORT% "%LOCAL_SRC%\db.py" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM Routes
scp -P %PI_PORT% -r "%LOCAL_SRC%\routes" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM Services
scp -P %PI_PORT% -r "%LOCAL_SRC%\services" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM Utils
scp -P %PI_PORT% -r "%LOCAL_SRC%\utils" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM Workers
scp -P %PI_PORT% -r "%LOCAL_SRC%\workers" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM Migrations
scp -P %PI_PORT% -r "%LOCAL_SRC%\migrations" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

echo [OK] 後端檔案同步完成

REM -------------------------------------------------------------------
REM Step 3: 同步前端 dist
REM -------------------------------------------------------------------
echo.
echo [3/6] 同步前端建置產出...
scp -P %PI_PORT% -r "%LOCAL_SRC%\frontend\dist" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/frontend/
echo [OK] 前端建置產出同步完成

REM -------------------------------------------------------------------
REM Step 4: 同步設定檔與文件
REM -------------------------------------------------------------------
echo.
echo [4/6] 同步設定檔與文件...
scp -P %PI_PORT% "%LOCAL_SRC%\requirements.txt" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

REM static/config (prompt_options etc.)
scp -P %PI_PORT% -r "%LOCAL_SRC%\static\config" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/static/

REM docs
scp -P %PI_PORT% -r "%LOCAL_SRC%\docs" %PI_USER%@%PI_HOST%:%PI_DEPLOY_DIR%/

echo [OK] 設定檔同步完成

REM -------------------------------------------------------------------
REM Step 5: 遠端安裝依賴 (如有新增)
REM -------------------------------------------------------------------
echo.
echo [5/6] 檢查並安裝 Python 依賴...
ssh -p %PI_PORT% %PI_USER%@%PI_HOST% "cd %PI_DEPLOY_DIR% && pip3 install -r requirements.txt --quiet 2>&1 | tail -1"
echo [OK] 依賴檢查完成

REM -------------------------------------------------------------------
REM Step 6: 重啟服務
REM -------------------------------------------------------------------
echo.
echo [6/6] 重啟 Prism 服務...
ssh -p %PI_PORT% %PI_USER%@%PI_HOST% "sudo systemctl restart %PI_SERVICE_NAME%"
if errorlevel 1 (
    echo [WARNING] 服務重啟失敗。請手動執行:
    echo   ssh %PI_USER%@%PI_HOST% "sudo systemctl restart %PI_SERVICE_NAME%"
) else (
    echo [OK] 服務重啟成功
)

REM -------------------------------------------------------------------
REM Step 7: 驗證服務狀態
REM -------------------------------------------------------------------
echo.
echo [VERIFY] 等待服務啟動 (3秒)...
timeout /t 3 /nobreak >nul
ssh -p %PI_PORT% %PI_USER%@%PI_HOST% "systemctl is-active %PI_SERVICE_NAME%"

echo.
echo ============================================================
echo   部署完成！
echo   存取網址: http://%PI_HOST%/
echo ============================================================
echo.
pause
