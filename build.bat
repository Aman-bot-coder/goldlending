@echo off
REM =========================================================
REM  Gold & Silver Loan Management System — Windows EXE Build
REM  Run this script on a Windows machine with Python 3.11+
REM  Double-click or run from Command Prompt / PowerShell
REM =========================================================

echo.
echo  ===  Gold Silver Loan — Windows EXE Build  ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from https://python.org
    echo        Make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [1/5] Python found.

REM Create virtual environment if not present
if not exist "venv\" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/5] Virtual environment already exists.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install / upgrade dependencies
echo [3/5] Installing dependencies (this may take a few minutes)...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

REM Build EXE
echo [4/5] Building EXE with PyInstaller...
pyinstaller build_exe.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. Check the output above for details.
    pause
    exit /b 1
)

echo [5/5] Build complete!
echo.
echo  EXE location:  dist\GoldSilverLoan\GoldSilverLoan.exe
echo.
echo  To create a Windows installer:
echo    1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
echo    2. Open installer\installer.iss in Inno Setup
echo    3. Press F9 (Build) — output: dist\installer\GoldSilverLoan_Setup_v1.0.0.exe
echo.
pause
