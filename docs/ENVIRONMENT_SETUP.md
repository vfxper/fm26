# Environment Setup Guide

This guide explains how to set up and configure different environments (development, staging, production) for Telegram Football Manager.

## Table of Contents

- [Overview](#overview)
- [Environment Types](#environment-types)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Deployment Guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)

---

## Overview

Telegram Football Manager supports three distinct environments:

1. **Development** - Local development with debug features enabled
2. **Staging** - Pre-production testing environment
3. **Production** - Live production environment

Each environment has its own configuration file (`.env.development`, `.env.staging`, `.env.production`) with environment-specific settings.

---

## Environment Types

### Development Environment

**Purpose**: Local development and testing

**Characteristics**:
- Debug mode enabled
- Verbose logging (DEBUG level)
- Database query echo enabled
- Auto-reload on code changes
- Rate limiting disabled
- Local PostgreSQL and Redis
- Relaxed CORS policy

**Use Cases**:
- Feature development
- Bug fixing
- Local testing
- Experimentation

### Staging Environment

**Purpose**: Pre-production testing and QA

**Characteristics**:
- Debug mode disabled
- Moderate logging (INFO level)
- Rate limiting enabled (moderate)
- Separate staging database
- Staging Telegram bot
- Monitoring enabled
- Restricted CORS policy

**Use Cases**:
- Integration testing
- QA validation
- Performance testing
- Client demos

### Production Environment

**Purpose**: Live production deployment

**Characteristics**:
- Debug mode disabled
- Minimal logging (WARNING level)
- Strict rate limiting
- Production database with backups
- Production Telegram bot
- Full monitoring and alerting
- Strict CORS policy
- Multiple workers

**Use Cases**:
- Live user traffic
- Real game data
- Production operations

---

## Quick Start

### 1. Choose Your Environment

```bash
# Development (default for local work)
./scripts/setup_environment.sh development

# Staging (for testing)
./scripts/setup_environment.sh staging

# Production (for deployment)
./scripts/setup_environment.sh production
```

**Windows:**
```cmd
scripts\setup_environment.bat development
```

### 2. Verify Setup

```bash
python scripts/verify_environment.py
```

This will check:
- Python version (3.11+)
- Required dependencies
- Environment variables
- Database connection
- Redis connection
- File structure

### 3. Start the Application

**Development:**
```bash
# With auto-reload
python app/main.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Staging/Production:**
```bash
# With multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Environment Configuration

### Development Configuration

**File**: `.env.development`

**Key Settings**:
```bash
ENVIRONMENT=development
DEBUG=True
DATABASE_ECHO=True
LOG_LEVEL=DEBUG
RATE_LIMIT_ENABLED=False
```

**Database**:
- Local PostgreSQL: `localhost:5432`
- Database name: `tfm_db_dev`
- User: `tfm_user`
- Password: `tfm_password`

**Redis**:
- Local Redis: `localhost:6379`
- Database: 0 (cache), 1 (Celery broker), 2 (Celery results)

**Setup Steps**:

1. Install PostgreSQL and Redis locally
2. Create development database:
   ```bash
   ./scripts/setup_database.sh
   ```
3. Start Redis:
   ```bash
   redis-server
   ```
4. Run the application:
   ```bash
   python app/main.py
   ```

### Staging Configuration

**File**: `.env.staging`

**Key Settings**:
```bash
ENVIRONMENT=staging
DEBUG=False
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=120
WORKERS=2
```

**Required Updates**:

Before deploying to staging, update these values in `.env.staging`:

1. **Database URL**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://user:password@staging-host:5432/tfm_staging
   ```

2. **Redis URL**:
   ```bash
   REDIS_URL=redis://staging-host:6379/0
   ```

3. **Telegram Bot Token** (create a separate staging bot):
   ```bash
   TELEGRAM_BOT_TOKEN=your_staging_bot_token
   TELEGRAM_WEBHOOK_URL=https://staging.yourdomain.com/webhook
   ```

4. **Secret Key** (generate a strong random key):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   SECRET_KEY=<generated_key>
   ```

5. **CORS Origins**:
   ```bash
   CORS_ORIGINS=["https://staging.yourdomain.com","https://t.me"]
   ```

**Setup Steps**:

1. Provision staging server (VPS or cloud instance)
2. Install PostgreSQL and Redis
3. Update `.env.staging` with staging credentials
4. Copy `.env.staging` to server
5. Run setup script:
   ```bash
   ./scripts/setup_environment.sh staging
   ```
6. Run database migrations:
   ```bash
   alembic upgrade head
   ```
7. Start application with systemd or supervisor
8. Configure Nginx reverse proxy with SSL
9. Set up Telegram webhook

### Production Configuration

**File**: `.env.production`

**Key Settings**:
```bash
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=60
WORKERS=4
PROMETHEUS_ENABLED=True
```

**Critical Security Requirements**:

⚠️ **IMPORTANT**: Never deploy to production without updating these:

1. **Strong Database Password**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://tfm_user:STRONG_RANDOM_PASSWORD@prod-host:5432/tfm_db
   ```

2. **Strong Secret Key** (minimum 32 characters):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   SECRET_KEY=<generated_key>
   ```

3. **Production Bot Token**:
   ```bash
   TELEGRAM_BOT_TOKEN=your_production_bot_token
   TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
   ```

4. **Strict CORS**:
   ```bash
   CORS_ORIGINS=["https://yourdomain.com","https://t.me"]
   ```

**Setup Steps**:

1. Provision production server (recommended: 4+ CPU cores, 8+ GB RAM)
2. Install PostgreSQL 15+ and Redis 7+
3. Configure PostgreSQL for production:
   - Enable SSL connections
   - Set up connection pooling (PgBouncer)
   - Configure automated backups
   - Set up replication (optional)
4. Configure Redis for production:
   - Enable persistence (AOF + RDB)
   - Set up Redis Sentinel or Cluster (optional)
   - Configure memory limits
5. Update `.env.production` with production credentials
6. Copy `.env.production` to server (secure transfer)
7. Run setup script:
   ```bash
   ./scripts/setup_environment.sh production
   ```
8. Run database migrations:
   ```bash
   alembic upgrade head
   ```
9. Load player database:
   ```bash
   python scripts/load_players.py
   ```
10. Configure systemd service for application
11. Configure Nginx reverse proxy with SSL (Let's Encrypt)
12. Set up monitoring (Prometheus + Grafana)
13. Configure log aggregation (ELK stack or similar)
14. Set up error tracking (Sentry)
15. Configure automated backups
16. Set up Telegram webhook
17. Test thoroughly before going live

---

## Deployment Guide

### Development Deployment

**Local Machine**:

```bash
# 1. Set up environment
./scripts/setup_environment.sh development

# 2. Create database
./scripts/setup_database.sh

# 3. Start Redis
redis-server

# 4. Start application
python app/main.py
```

### Staging Deployment

**Cloud Server (AWS/GCP/Azure/VPS)**:

```bash
# 1. SSH into staging server
ssh user@staging-server

# 2. Clone repository
git clone <repository-url>
cd telegram-football-manager

# 3. Set up Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Set up environment
./scripts/setup_environment.sh staging

# 5. Update .env with staging credentials
nano .env

# 6. Run migrations
alembic upgrade head

# 7. Create systemd service
sudo nano /etc/systemd/system/tfm-staging.service
```

**Systemd Service** (`/etc/systemd/system/tfm-staging.service`):

```ini
[Unit]
Description=Telegram Football Manager (Staging)
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=tfm
Group=tfm
WorkingDirectory=/home/tfm/telegram-football-manager
Environment="PATH=/home/tfm/telegram-football-manager/venv/bin"
ExecStart=/home/tfm/telegram-football-manager/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Nginx Configuration** (`/etc/nginx/sites-available/tfm-staging`):

```nginx
server {
    listen 80;
    server_name staging.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging.yourdomain.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/staging.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Start Services**:

```bash
# Enable and start application
sudo systemctl enable tfm-staging
sudo systemctl start tfm-staging

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status tfm-staging
sudo systemctl status nginx
```

### Production Deployment

Follow the same steps as staging, but:

1. Use `.env.production` configuration
2. Use production domain and SSL certificates
3. Configure 4+ workers for higher load
4. Set up monitoring and alerting
5. Configure automated backups
6. Set up log rotation
7. Configure firewall rules
8. Enable fail2ban for security
9. Set up health checks and uptime monitoring
10. Configure CDN for static assets (optional)

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptoms**:
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed
```

**Solutions**:
- Verify DATABASE_URL in .env is correct
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Test connection: `psql -U tfm_user -d tfm_db -h localhost`
- Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-15-main.log`

#### 2. Redis Connection Failed

**Symptoms**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions**:
- Verify REDIS_URL in .env is correct
- Check Redis is running: `sudo systemctl status redis`
- Test connection: `redis-cli ping`
- Check Redis logs: `sudo tail -f /var/log/redis/redis-server.log`

#### 3. Environment Variables Not Loaded

**Symptoms**:
```
KeyError: 'DATABASE_URL'
```

**Solutions**:
- Ensure .env file exists: `ls -la .env`
- Run setup script: `./scripts/setup_environment.sh development`
- Verify python-dotenv is installed: `pip install python-dotenv`
- Check .env file permissions: `chmod 600 .env`

#### 4. Port Already in Use

**Symptoms**:
```
OSError: [Errno 98] Address already in use
```

**Solutions**:
- Check what's using the port: `lsof -i :8000`
- Kill the process: `kill -9 <PID>`
- Or change API_PORT in .env

#### 5. Permission Denied

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied
```

**Solutions**:
- Check file permissions: `ls -la`
- Make scripts executable: `chmod +x scripts/*.sh`
- Run with appropriate user (don't use root in production)

### Verification Checklist

Run the verification script to check all components:

```bash
python scripts/verify_environment.py
```

This will check:
- ✓ Python version (3.11+)
- ✓ Dependencies installed
- ✓ .env file exists
- ✓ Environment variables set
- ✓ Database connection
- ✓ Redis connection
- ✓ File structure
- ✓ Environment configuration

### Getting Help

If you encounter issues not covered here:

1. Check application logs:
   ```bash
   # Development
   tail -f logs/app.log
   
   # Production (systemd)
   sudo journalctl -u tfm-production -f
   ```

2. Check database logs:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-15-main.log
   ```

3. Check Redis logs:
   ```bash
   sudo tail -f /var/log/redis/redis-server.log
   ```

4. Check Nginx logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   sudo tail -f /var/log/nginx/access.log
   ```

5. Review the design document: `.kiro/specs/telegram-football-manager/design.md`

---

## Security Best Practices

### Development
- Use separate development bot token
- Don't commit .env files to version control
- Use local database with weak passwords (acceptable for dev)

### Staging
- Use separate staging bot token
- Restrict access to staging server
- Use moderate security settings
- Test security features

### Production
- **Never** use default passwords
- **Always** use strong random SECRET_KEY (32+ characters)
- **Always** enable SSL/TLS
- **Always** use strict CORS policy
- **Always** enable rate limiting
- **Always** set up monitoring and alerting
- **Always** configure automated backups
- **Always** keep dependencies updated
- **Always** review security logs regularly
- **Never** commit production credentials to version control
- **Never** expose debug endpoints in production
- **Never** run as root user

### Credential Management

**Generate Strong Secret Key**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Generate Strong Database Password**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Store Credentials Securely**:
- Use environment variables
- Use secret management services (AWS Secrets Manager, HashiCorp Vault)
- Never commit to version control
- Rotate credentials regularly
- Use different credentials for each environment

---

## Monitoring and Maintenance

### Health Checks

**Endpoint**: `GET /health`

Returns:
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

### Monitoring

**Prometheus Metrics** (if enabled):
- Endpoint: `http://localhost:9090/metrics`
- Metrics: request count, latency, error rate, database connections, etc.

**Grafana Dashboards**:
- Set up dashboards for key metrics
- Configure alerts for anomalies
- Monitor resource usage

### Backups

**Database Backups**:
```bash
# Daily backup script
pg_dump -U tfm_user tfm_db > backup_$(date +%Y%m%d).sql

# Automated with cron
0 2 * * * /usr/bin/pg_dump -U tfm_user tfm_db > /backups/tfm_$(date +\%Y\%m\%d).sql
```

**Redis Backups**:
- Configure RDB snapshots
- Configure AOF persistence
- Copy dump.rdb and appendonly.aof regularly

### Log Rotation

**Configure logrotate** (`/etc/logrotate.d/tfm`):
```
/var/log/tfm/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 tfm tfm
    sharedscripts
    postrotate
        systemctl reload tfm-production
    endscript
}
```

---

## Additional Resources

- [Requirements Document](../.kiro/specs/telegram-football-manager/requirements.md)
- [Design Document](../.kiro/specs/telegram-football-manager/design.md)
- [Implementation Tasks](../.kiro/specs/telegram-football-manager/tasks.md)
- [Database Setup Guide](./DATABASE_SETUP.md)
- [Bot Setup Guide](./BOT_SETUP.md)
- [Celery Setup Guide](./CELERY_SETUP.md)

---

**Last Updated**: 2024
**Version**: 1.0
