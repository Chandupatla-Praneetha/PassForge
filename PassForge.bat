@echo off
REM Double-click this file to open PassForge directly — no VS Code, no terminal.
setlocal
cd /d "%~dp0"

REM If you've already built the standalone exe (via build.bat), use it — it's
REM faster and doesn't need Python installed at all.
if exist "dist\PassForge.exe" (
    start "" "dist\PassForge.exe"
    goto :eof
)

REM Otherwise, run from source. Make sure dependencies are installed —
REM this only actually installs anything the very first time.
python -c "import customtkinter, cryptography, PIL" 2>nul
if errorlevel 1 (
    echo Setting up PassForge for the first time, this may take a minute...
    python -m pip install -r requirements.txt --quiet
)

REM Launch with pythonw so no black console window stays open.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw main.py
) else (
    start "" python main.py
)
