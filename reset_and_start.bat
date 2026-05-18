@echo off
echo ========================================
echo   FM26 - Reset and Start
echo ========================================
echo.

REM Kill any running python processes on port 8000
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Delete old database
if exist fm26_local.db (
    del /f fm26_local.db
    echo   Deleted old database
)

echo   Creating fresh database...
REM Start server briefly to create tables
start /b python run_local.py
timeout /t 5 /nobreak >nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo   Seeding players from CSV...
python seed_local.py

echo.
echo   Starting game server...
echo   Game: http://localhost:3000
echo   API:  http://localhost:8000/docs
echo.
python run_local.py
