@echo off
rem ============================================================
rem  Angel — double-click launcher for Windows
rem  Creates the venv and installs dependencies on first run.
rem ============================================================
setlocal
cd /d "%~dp0"
title Angel

where python >nul 2>nul
if errorlevel 1 (
    echo [Angel] Python was not found on PATH.
    echo         Install Python 3.11 or 3.12 from https://www.python.org/downloads/
    echo         and check "Add python.exe to PATH" during install.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Angel] First run — creating virtual environment...
    python -m venv .venv || (echo [Angel] venv creation failed & pause & exit /b 1)
    echo [Angel] Installing dependencies ^(a few minutes the first time^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (
        echo [Angel] Dependency install failed — see messages above.
        pause
        exit /b 1
    )
)

if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [Angel] Created .env — add your OPENROUTER_API_KEY and FISH_API_KEY to it.
    )
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
endlocal
