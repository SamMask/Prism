@echo off
chcp 65001 >nul
REM Prism - 打包腳本
REM 確保腳本在根目錄 context 執行
cd /d "%~dp0.."

set VERSION=v1.4.1

REM 取得日期時間 (格式: YYYYMMDD_HHMM)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set DATETIME=%datetime:~0,8%_%datetime:~8,4%
set ARCHIVE_NAME=Prism_%VERSION%_%DATETIME%

echo ================================================
echo  Prism - 打包壓縮腳本
echo  版本: %VERSION%
echo ================================================
echo.

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
xcopy /E /I /Y "scripts" "dist\%ARCHIVE_NAME%\scripts" >nul
xcopy /E /I /Y "resources\wheels" "dist\%ARCHIVE_NAME%\wheels" >nul

REM 複製根目錄檔案
copy "app.py" "dist\%ARCHIVE_NAME%\" >nul
copy "config.py" "dist\%ARCHIVE_NAME%\" >nul
copy "db.py" "dist\%ARCHIVE_NAME%\" >nul
copy "requirements.txt" "dist\%ARCHIVE_NAME%\" >nul
copy "README.md" "dist\%ARCHIVE_NAME%\" >nul
copy "install.bat" "dist\%ARCHIVE_NAME%\" >nul
copy "install.sh" "dist\%ARCHIVE_NAME%\" >nul
copy "start.bat" "dist\%ARCHIVE_NAME%\" >nul

REM 使用 PowerShell 壓縮
echo [3/3] 壓縮中...
powershell -Command "Compress-Archive -Path 'dist\%ARCHIVE_NAME%' -DestinationPath 'dist\%ARCHIVE_NAME%.zip' -Force"

echo.
echo ================================================
echo  打包完成！
echo  檔案: dist\%ARCHIVE_NAME%.zip
echo ================================================
echo.

REM 清理臨時資料夾
rd /s /q "dist\%ARCHIVE_NAME%"

pause
