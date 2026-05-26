@echo off
set SRC=d:\AI\Prism
set DST=D:\Program Files\Prism_V2

echo [1/7] Copying routes\system.py...
copy /Y "%SRC%\routes\system.py" "%DST%\routes\system.py"

echo [2/7] Copying app.py...
copy /Y "%SRC%\app.py" "%DST%\app.py"

echo [3/7] Copying static\js\composables\useEditor.js...
copy /Y "%SRC%\static\js\composables\useEditor.js" "%DST%\static\js\composables\useEditor.js"

echo [4/7] Copying static\js\composables\useSettings.js...
copy /Y "%SRC%\static\js\composables\useSettings.js" "%DST%\static\js\composables\useSettings.js"

echo [5/7] Copying static\js\app.js...
copy /Y "%SRC%\static\js\app.js" "%DST%\static\js\app.js"

echo [6/7] Copying templates\components\_editor-modal.html...
copy /Y "%SRC%\templates\components\_editor-modal.html" "%DST%\templates\components\_editor-modal.html"

echo [7/7] Copying templates\components\_settings-modal.html...
copy /Y "%SRC%\templates\components\_settings-modal.html" "%DST%\templates\components\_settings-modal.html"

echo.
echo === ALL 7 FILES DEPLOYED TO %DST% ===
pause
