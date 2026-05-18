@echo off
REM PostgreSQL Database Setup Script for Windows
REM This script helps set up the PostgreSQL database for Telegram Football Manager

echo ============================================================
echo PostgreSQL Database Setup for Telegram Football Manager
echo ============================================================
echo.

REM Check if psql is available
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PostgreSQL is not installed or not in PATH
    echo.
    echo Please install PostgreSQL 15+ from:
    echo https://www.postgresql.org/download/windows/
    echo.
    echo After installation, add PostgreSQL bin directory to PATH:
    echo Example: C:\Program Files\PostgreSQL\15\bin
    echo.
    pause
    exit /b 1
)

echo PostgreSQL found!
echo.

REM Get PostgreSQL superuser password
set /p POSTGRES_PASSWORD="Enter PostgreSQL superuser (postgres) password: "
echo.

REM Database configuration
set DB_NAME=tfm_db
set DB_USER=tfm_user
set DB_PASSWORD=tfm_password

echo Creating database and user...
echo.

REM Create SQL commands file
echo -- Create database user > setup_db.sql
echo CREATE USER %DB_USER% WITH PASSWORD '%DB_PASSWORD%'; >> setup_db.sql
echo. >> setup_db.sql
echo -- Create database >> setup_db.sql
echo CREATE DATABASE %DB_NAME% OWNER %DB_USER%; >> setup_db.sql
echo. >> setup_db.sql
echo -- Grant privileges >> setup_db.sql
echo GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%; >> setup_db.sql

REM Execute SQL commands
set PGPASSWORD=%POSTGRES_PASSWORD%
psql -U postgres -f setup_db.sql

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to create database and user
    echo Please check your PostgreSQL superuser password and try again
    echo.
    del setup_db.sql
    pause
    exit /b 1
)

REM Grant schema privileges
echo \c %DB_NAME% > grant_privileges.sql
echo GRANT ALL ON SCHEMA public TO %DB_USER%; >> grant_privileges.sql
echo GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %DB_USER%; >> grant_privileges.sql
echo GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %DB_USER%; >> grant_privileges.sql
echo ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %DB_USER%; >> grant_privileges.sql
echo ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO %DB_USER%; >> grant_privileges.sql

psql -U postgres -f grant_privileges.sql

REM Clean up SQL files
del setup_db.sql
del grant_privileges.sql

echo.
echo ============================================================
echo Database setup completed successfully!
echo ============================================================
echo.
echo Database Name: %DB_NAME%
echo Database User: %DB_USER%
echo Database Password: %DB_PASSWORD%
echo.
echo Next steps:
echo 1. Update your .env file with the database credentials
echo 2. Run: python scripts\test_db_connection.py
echo 3. If test passes, you're ready to start development!
echo.
echo DATABASE_URL=postgresql+asyncpg://%DB_USER%:%DB_PASSWORD%@localhost:5432/%DB_NAME%
echo.
pause
