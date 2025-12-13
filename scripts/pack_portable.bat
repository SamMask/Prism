@echo off
chcp 65001 >nul
REM Prism - 完整版打包腳本 (含內嵌 Python)
REM 確保腳本在根目錄 context 執行
cd /d "%~dp0.."

set VERSION=v1.3.0

REM 取得日期時間 (格式: YYYYMMDD_HHMM)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set DATETIME=%datetime:~0,8%_%datetime:~8,4%
set ARCHIVE_NAME=Prism_%VERSION%_Portable_%DATETIME%

echo ================================================
echo  Prism - 完整版打包腳本 (含 Python)
echo  版本: %VERSION%
echo ================================================
echo.

REM 檢查 python 資料夾是否存在
if not exist "python\python.exe" (
    echo [錯誤] 找不到 python\ 資料夾！
    echo 請先執行內嵌 Python 設置。
    pause
    exit /b 1
)

REM 建立臨時資料夾 (保留舊版 zip)
echo [1/3] 準備打包...
if not exist "dist" mkdir "dist"
if exist "dist\%ARCHIVE_NAME%" rd /s /q "dist\%ARCHIVE_NAME%"
mkdir "dist\%ARCHIVE_NAME%"

REM 複製資料夾
echo [2/3] 複製檔案...
xcopy /E /I /Y "routes" "dist\%ARCHIVE_NAME%\routes" >nul
xcopy /E /I /Y "static" "dist\%ARCHIVE_NAME%\static" >nul
xcopy /E /I /Y "templates" "dist\%ARCHIVE_NAME%\templates" >nul
xcopy /E /I /Y "docs" "dist\%ARCHIVE_NAME%\docs" >nul
xcopy /E /I /Y "migrations" "dist\%ARCHIVE_NAME%\migrations" >nul
xcopy /E /I /Y "python" "dist\%ARCHIVE_NAME%\python" >nul

REM 複製根目錄檔案
copy "app.py" "dist\%ARCHIVE_NAME%\" >nul
copy "config.py" "dist\%ARCHIVE_NAME%\" >nul
copy "db.py" "dist\%ARCHIVE_NAME%\" >nul
copy "requirements.txt" "dist\%ARCHIVE_NAME%\" >nul
copy "README.md" "dist\%ARCHIVE_NAME%\" >nul
copy "start_portable.bat" "dist\%ARCHIVE_NAME%\start.bat" >nul

REM 使用 PowerShell 壓縮
echo [3/3] 壓縮中...
powershell -Command "Compress-Archive -Path 'dist\%ARCHIVE_NAME%' -DestinationPath 'dist\%ARCHIVE_NAME%.zip' -Force"

echo.
echo ================================================
echo  打包完成！
echo  檔案: dist\%ARCHIVE_NAME%.zip
echo  (含內嵌 Python，解壓即用)
echo ================================================
echo.

REM 清理臨時資料夾
rd /s /q "dist\%ARCHIVE_NAME%"

pause
