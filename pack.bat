@echo off
chcp 65001 >nul
REM Local Insight - 打包腳本

set VERSION=v1.0.0
set DATETIME=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%
set DATETIME=%DATETIME: =0%
set ARCHIVE_NAME=Local_Insight_%VERSION%_%DATETIME%

echo ================================================
echo  Local Insight - 打包壓縮腳本
echo  版本: %VERSION%
echo ================================================
echo.

REM 建立臨時資料夾
echo [1/3] 準備打包...
if exist "dist" rd /s /q "dist"
mkdir "dist\%ARCHIVE_NAME%"

REM 複製檔案 (排除不需要的)
echo [2/3] 複製檔案...
xcopy /E /I /Y "routes" "dist\%ARCHIVE_NAME%\routes" >nul
xcopy /E /I /Y "static" "dist\%ARCHIVE_NAME%\static" >nul
xcopy /E /I /Y "templates" "dist\%ARCHIVE_NAME%\templates" >nul
xcopy /E /I /Y "docs" "dist\%ARCHIVE_NAME%\docs" >nul
xcopy /E /I /Y "migrations" "dist\%ARCHIVE_NAME%\migrations" >nul
xcopy /E /I /Y "scripts" "dist\%ARCHIVE_NAME%\scripts" >nul

copy "app.py" "dist\%ARCHIVE_NAME%\" >nul
copy "config.py" "dist\%ARCHIVE_NAME%\" >nul
copy "db.py" "dist\%ARCHIVE_NAME%\" >nul
copy "requirements.txt" "dist\%ARCHIVE_NAME%\" >nul
copy "README.md" "dist\%ARCHIVE_NAME%\" >nul
copy "TODO.md" "dist\%ARCHIVE_NAME%\" >nul
copy "SCHEMA.md" "dist\%ARCHIVE_NAME%\" >nul
copy "Local Insight.md" "dist\%ARCHIVE_NAME%\" >nul
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
