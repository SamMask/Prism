@echo off
chcp 65001 >nul
title Prism V2 完整打包

echo ========================================
echo   Prism V2 完整打包到 Prism_日常使用版
echo ========================================
echo.

set ROOT_DIR=%~dp0
set FRONTEND_DIR=%ROOT_DIR%frontend
set DIST_DIR=%ROOT_DIR%Prism_日常使用版

cd /d "%FRONTEND_DIR%"

echo [1/3] 安裝前端依賴...
call npm install

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ npm install 失敗!
    pause
    exit /b 1
)

echo.
echo [2/3] 打包前端 (TypeScript + Vite)...
call npm run build

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 前端打包失敗!
    pause
    exit /b 1
)

echo.
echo [3/3] 複製檔案到 Prism_日常使用版...
echo.

cd /d "%ROOT_DIR%"

REM === Python 主程式 ===
echo   複製 Python 主程式...
copy /Y app.py "%DIST_DIR%\" >nul
copy /Y config.py "%DIST_DIR%\" >nul
copy /Y db.py "%DIST_DIR%\" >nul
copy /Y requirements.txt "%DIST_DIR%\" >nul

REM === 啟動腳本 ===
echo   複製啟動腳本...
copy /Y start_v2.bat "%DIST_DIR%\" >nul

REM === 前端打包結果 ===
echo   複製前端 dist...
xcopy "%FRONTEND_DIR%\dist" "%DIST_DIR%\frontend\dist\" /E /Y /I >nul

REM === Python 後端模組 ===
echo   複製 routes...
xcopy routes "%DIST_DIR%\routes\" /E /Y /I >nul

echo   複製 services...
xcopy services "%DIST_DIR%\services\" /E /Y /I >nul

echo   複製 models...
if exist models (
    xcopy models "%DIST_DIR%\models\" /E /Y /I >nul
)

echo   複製 utils...
xcopy utils "%DIST_DIR%\utils\" /E /Y /I >nul

echo   複製 workers...
xcopy workers "%DIST_DIR%\workers\" /E /Y /I >nul

echo   複製 migrations...
if exist migrations (
    xcopy migrations "%DIST_DIR%\migrations\" /E /Y /I >nul
)

REM === Vue 前端 (V1) ===
echo   複製 static (Vue 前端)...
xcopy static "%DIST_DIR%\static\" /E /Y /I >nul

echo   複製 templates...
xcopy templates "%DIST_DIR%\templates\" /E /Y /I >nul

REM === 資源檔案 ===
echo   複製 resources...
if exist resources (
    xcopy resources "%DIST_DIR%\resources\" /E /Y /I >nul
)

REM === 內嵌 Python (如果存在) ===
if exist python (
    echo   複製內嵌 Python 環境...
    xcopy python "%DIST_DIR%\python\" /E /Y /I >nul
)

echo.
echo ========================================
echo ✅ 打包完成!
echo ========================================
echo.
echo 輸出目錄: %DIST_DIR%
echo.
echo 包含:
echo   - 前端 React (V2)
echo   - 前端 Vue (V1)  
echo   - Python 後端
echo   - 內嵌 Python 環境
echo.
pause
