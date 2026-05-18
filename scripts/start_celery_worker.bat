@echo off
REM Start Celery Worker for Telegram Football Manager

echo Starting Celery Worker...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Set Python path to include app directory
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Start Celery worker with configuration
celery -A app.core.celery:celery_app worker ^
    --loglevel=info ^
    --concurrency=4 ^
    --queues=matches,updates,ai,default ^
    --max-tasks-per-child=1000 ^
    --time-limit=300 ^
    --soft-time-limit=240 ^
    --pool=solo

echo Celery Worker stopped.
pause
