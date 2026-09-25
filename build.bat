@echo off
REM Build a standalone PassForge.exe for Windows.

cd /d "%~dp0"

echo Installing dependencies...
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller --quiet

echo Building PassForge...
pyinstaller --noconfirm passforge.spec

echo.
echo Done. Find PassForge.exe in the dist folder.
pause
