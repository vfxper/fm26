@echo off
REM Start Celery Beat Scheduler for Telegram Football Manager

echo Starting Celery Beat Scheduler...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Set Python path to include app directory
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Start Celery beat scheduler
celery -A app.core.celery:celery_app beat ^
    --loglevel=info ^
    --scheduler=celery.beat:PersistentScheduler

echo Celery Beat stopped.
pause
