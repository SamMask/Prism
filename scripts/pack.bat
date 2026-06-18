@echo off
chcp 65001 >nul
cd /d "%~dp0.."

set VERSION=v2.5-go-primary
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set DATETIME=%datetime:~0,8%_%datetime:~8,4%
set ARCHIVE_NAME=Prism_%VERSION%_%DATETIME%

echo ================================================
echo  Prism - Go Primary Package
echo ================================================
echo.

echo [1/4] Building Go primary runtime...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build_go_runtime.ps1"
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

echo [2/4] Preparing package...
if not exist "dist" mkdir "dist"
if exist "dist\%ARCHIVE_NAME%" rd /s /q "dist\%ARCHIVE_NAME%"
mkdir "dist\%ARCHIVE_NAME%"
mkdir "dist\%ARCHIVE_NAME%\build\go-runtime"
mkdir "dist\%ARCHIVE_NAME%\scripts"

echo [3/4] Copying Go artifacts and docs...
copy "build\go-runtime\prism-go-runtime.exe" "dist\%ARCHIVE_NAME%\build\go-runtime\" >nul
copy "build\go-runtime\prism-go-runtime-linux-arm64" "dist\%ARCHIVE_NAME%\build\go-runtime\" >nul
copy "scripts\start_go_primary.ps1" "dist\%ARCHIVE_NAME%\scripts\" >nul
copy "scripts\start.bat" "dist\%ARCHIVE_NAME%\scripts\" >nul
copy "start_v2.bat" "dist\%ARCHIVE_NAME%\" >nul
copy "README.md" "dist\%ARCHIVE_NAME%\" >nul
xcopy /E /I /Y "docs" "dist\%ARCHIVE_NAME%\docs" >nul

echo [4/4] Compressing...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\%ARCHIVE_NAME%' -DestinationPath 'dist\%ARCHIVE_NAME%.zip' -Force"

echo.
echo Package complete: dist\%ARCHIVE_NAME%.zip
echo.
rd /s /q "dist\%ARCHIVE_NAME%"
pause
