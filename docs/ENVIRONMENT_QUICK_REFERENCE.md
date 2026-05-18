# Environment Setup - Quick Reference

## Quick Commands

### Switch Environment

```bash
# Development
./scripts/setup_environment.sh development

# Staging
./scripts/setup_environment.sh staging

# Production
./scripts/setup_environment.sh production
```

**Windows:**
```cmd
scripts\setup_environment.bat [environment]
```

### Verify Setup

```bash
python scripts/verify_environment.py
```

### Start Application

```bash
# Development (auto-reload)
python app/main.py

# Staging/Production (multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Environment Comparison

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| **Debug** | ON | OFF | OFF |
| **Log Level** | DEBUG | INFO | WARNING |
| **Rate Limit** | OFF | 120/min | 60/min |
| **Workers** | 1 | 2 | 4 |
| **Database** | Local | Staging | Production |
| **CORS** | Relaxed | Moderate | Strict |

---

## Critical Variables to Update

### Staging & Production

Before deploying, update these in `.env`:

1. **DATABASE_URL** - Database connection string
2. **REDIS_URL** - Redis connection string
3. **SECRET_KEY** - Generate strong key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. **TELEGRAM_BOT_TOKEN** - Bot token from @BotFather
5. **TELEGRAM_WEBHOOK_URL** - Your domain webhook URL
6. **CORS_ORIGINS** - Your domain(s)

---

## Common Tasks

### Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Check Current Environment

```bash
grep "^ENVIRONMENT=" .env
```

### View All Settings

```bash
cat .env | grep -v "^#" | grep -v "^$"
```

### Backup Current .env

```bash
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

---

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U tfm_user -d tfm_db -h localhost
```

### Redis Connection Failed
```bash
# Check Redis is running
sudo systemctl status redis

# Test connection
redis-cli ping
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

---

## File Locations

- **Environment Files**: `.env.development`, `.env.staging`, `.env.production`
- **Active Config**: `.env`
- **Setup Scripts**: `scripts/setup_environment.sh` (Linux/macOS), `scripts/setup_environment.bat` (Windows)
- **Verification**: `scripts/verify_environment.py`
- **Documentation**: `docs/ENVIRONMENT_SETUP.md`

---

## Security Checklist (Production)

- [ ] Strong database password
- [ ] Strong SECRET_KEY (32+ chars)
- [ ] SSL/TLS enabled
- [ ] Strict CORS policy
- [ ] Rate limiting enabled
- [ ] Debug mode OFF
- [ ] Monitoring enabled
- [ ] Automated backups configured
- [ ] Firewall configured
- [ ] Log rotation configured

---

## Next Steps After Setup

1. **Verify**: `python scripts/verify_environment.py`
2. **Migrate**: `alembic upgrade head`
3. **Load Data**: `python scripts/load_players.py` (if needed)
4. **Start**: `python app/main.py` or `uvicorn app.main:app --reload`
5. **Test**: Visit `http://localhost:8000/health`

---

For detailed information, see [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)
