@echo off
REM Telegram Football Manager - Virtual Environment Setup Script for Windows

echo ========================================
echo Telegram Football Manager Setup
echo ========================================
echo.

REM Check if Python 3.11 is installed
echo Checking Python version...
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11 is not installed!
    echo Please install Python 3.11 from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python 3.11 found!
echo.

REM Create virtual environment
echo Creating virtual environment...
py -3.11 -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)

echo Virtual environment created successfully!
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo To deactivate, run:
echo   deactivate
echo.
pause
