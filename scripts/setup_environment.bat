@echo off
REM Environment Setup Script for Windows
REM This script helps set up the appropriate environment for Telegram Football Manager

setlocal enabledelayedexpansion

echo ============================================================
echo Telegram Football Manager - Environment Setup
echo ============================================================
echo.

REM Check if environment argument is provided
if "%1"=="" (
    echo ERROR: No environment specified
    echo.
    goto usage
)

set ENVIRONMENT=%1

REM Validate environment
if not "%ENVIRONMENT%"=="development" if not "%ENVIRONMENT%"=="staging" if not "%ENVIRONMENT%"=="production" (
    echo ERROR: Invalid environment '%ENVIRONMENT%'
    echo Valid environments: development, staging, production
    echo.
    goto usage
)

echo Setting up %ENVIRONMENT% environment...
echo.

REM Check if environment file exists
set ENV_FILE=.env.%ENVIRONMENT%
if not exist "%ENV_FILE%" (
    echo ERROR: Environment file '%ENV_FILE%' not found
    echo.
    exit /b 1
)

REM Backup existing .env if it exists
if exist ".env" (
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
    for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
    set BACKUP_FILE=.env.backup.!mydate!_!mytime!
    echo Backing up existing .env to !BACKUP_FILE!
    copy .env "!BACKUP_FILE!" >nul
    echo.
)

REM Copy environment-specific file to .env
echo Copying %ENV_FILE% to .env
copy "%ENV_FILE%" .env >nul
echo.

REM Display environment configuration
echo ============================================================
echo Environment Configuration
echo ============================================================
echo.
echo Environment: %ENVIRONMENT%
echo.

REM Extract key configuration values
echo Key Settings:
findstr /B "ENVIRONMENT=" .env 2>nul
findstr /B "DEBUG=" .env 2>nul
findstr /B "API_PORT=" .env 2>nul
findstr /B "LOG_LEVEL=" .env 2>nul
findstr /B "RATE_LIMIT_ENABLED=" .env 2>nul
echo.

REM Environment-specific instructions
if "%ENVIRONMENT%"=="development" goto development
if "%ENVIRONMENT%"=="staging" goto staging
if "%ENVIRONMENT%"=="production" goto production

:development
echo Development Environment Setup Complete!
echo.
echo Next steps:
echo 1. Ensure PostgreSQL is running (default: localhost:5432)
echo 2. Ensure Redis is running (default: localhost:6379)
echo 3. Create development database:
echo    scripts\setup_database.bat
echo 4. Start the development server:
echo    python app\main.py
echo    or
echo    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo Development features enabled:
echo   - Debug mode: ON
echo   - Database echo: ON
echo   - Auto-reload: ON
echo   - Rate limiting: OFF
echo   - Verbose logging: DEBUG level
echo.
goto end

:staging
echo Staging Environment Setup Complete!
echo.
echo IMPORTANT: Update the following in .env before deploying:
echo   - DATABASE_URL (staging database credentials)
echo   - REDIS_URL (staging Redis host)
echo   - TELEGRAM_BOT_TOKEN (staging bot token)
echo   - SECRET_KEY (generate strong random key)
echo   - TELEGRAM_WEBHOOK_URL (staging domain)
echo   - CORS_ORIGINS (staging domain)
echo.
echo Next steps:
echo 1. Update .env with staging credentials
echo 2. Run database migrations:
echo    alembic upgrade head
echo 3. Start the application:
echo    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
echo 4. Configure reverse proxy (Nginx) for HTTPS
echo 5. Set up Telegram webhook
echo.
echo Staging features:
echo   - Debug mode: OFF
echo   - Rate limiting: MODERATE (120/min)
echo   - Logging: INFO level
echo   - Monitoring: ENABLED
echo.
goto end

:production
echo Production Environment Setup Complete!
echo.
echo WARNING: CRITICAL - Update the following in .env before deploying:
echo   - DATABASE_URL (production database with strong password)
echo   - REDIS_URL (production Redis host)
echo   - TELEGRAM_BOT_TOKEN (production bot token)
echo   - SECRET_KEY (MUST be strong random key, min 32 chars)
echo   - TELEGRAM_WEBHOOK_URL (production domain)
echo   - CORS_ORIGINS (production domain only)
echo.
echo Security checklist:
echo   [x] Use strong database passwords
echo   [x] Enable SSL/TLS for all connections
echo   [x] Configure firewall rules
echo   [x] Set up automated backups
echo   [x] Enable monitoring and alerting
echo   [x] Review CORS settings
echo   [x] Test rate limiting
echo.
echo Next steps:
echo 1. Update .env with production credentials
echo 2. Run database migrations:
echo    alembic upgrade head
echo 3. Load player database:
echo    python scripts\load_players.py
echo 4. Start the application with multiple workers:
echo    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
echo 5. Configure reverse proxy (Nginx) with SSL
echo 6. Set up Telegram webhook
echo 7. Configure monitoring (Prometheus/Grafana)
echo 8. Set up log aggregation
echo.
echo Production features:
echo   - Debug mode: OFF
echo   - Rate limiting: STRICT (60/min)
echo   - Logging: WARNING level
echo   - Monitoring: ENABLED
echo   - Multiple workers: 4
echo.
goto end

:usage
echo Usage: %0 [development^|staging^|production]
echo.
echo Examples:
echo   %0 development    # Set up development environment
echo   %0 staging        # Set up staging environment
echo   %0 production     # Set up production environment
echo.
exit /b 1

:end
echo ============================================================
echo.
echo To verify your environment setup, run:
echo   python scripts\verify_environment.py
echo.

endlocal
