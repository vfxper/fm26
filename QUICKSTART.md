# Quick Start Guide - Telegram Football Manager

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

## Setup Instructions

### 1. Clone and Navigate to Project

```bash
cd telegram-football-manager
```

### 2. Create Virtual Environment

**Windows:**
```bash
# Run the setup script
./setup_venv.bat

# Or manually:
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
# Run the setup script
./setup_venv.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, update:
# - DATABASE_URL (PostgreSQL connection string)
# - REDIS_URL (Redis connection string)
# - SECRET_KEY (generate a strong random key)
```

### 5. Setup Database

```bash
# Create PostgreSQL database
createdb tfm_db

# Or using psql:
psql -U postgres
CREATE DATABASE tfm_db;
CREATE USER tfm_user WITH PASSWORD 'tfm_password';
GRANT ALL PRIVILEGES ON DATABASE tfm_db TO tfm_user;
\q

# Run database migrations
python scripts/migrate.py upgrade

# Or use Alembic directly:
python -m alembic upgrade head
```

### 6. Start Redis

**Windows:**
```bash
# If Redis is installed via WSL or Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

**Linux/Mac:**
```bash
redis-server
```

### 7. Run the Application

**Development Mode (with auto-reload):**
```bash
python app/main.py
```

**Or using uvicorn directly:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Verify Installation

Open your browser and navigate to:

- **API Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs (if DEBUG=True)
- **ReDoc**: http://localhost:8000/redoc (if DEBUG=True)

## Project Structure

```
telegram-football-manager/
├── app/                    # Main application package
│   ├── api/               # API routes and WebSocket handlers
│   ├── core/              # Configuration, database, cache
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # Business logic (game engine, modules)
│   ├── utils/             # Utilities and exceptions
│   └── main.py            # FastAPI application entry point
│
├── tests/                 # Test suite
│   ├── conftest.py        # Pytest fixtures
│   └── test_*.py          # Test files
│
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project configuration
└── README.md              # Project documentation
```

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=app

# Run specific test file
pytest tests/test_main.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
```

## Development Workflow

### 1. Task 1.2 ✅ (Current)
FastAPI project structure with async support is now complete.

### 2. Next Steps (Task 1.3+)
- Configure PostgreSQL database connection
- Set up Redis for caching
- Configure SQLAlchemy with async support
- Set up Celery task queue
- And more...

## Common Issues

### Issue: Database connection fails
**Solution**: Verify PostgreSQL is running and DATABASE_URL in .env is correct

### Issue: Redis connection fails
**Solution**: Verify Redis is running on port 6379 or update REDIS_URL in .env

### Issue: Import errors
**Solution**: Ensure virtual environment is activated and dependencies are installed

### Issue: Port 8000 already in use
**Solution**: Change API_PORT in .env or stop the process using port 8000

## API Endpoints (Current)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | API information |
| GET | /health | Health check |
| WS | /ws/match/{match_id} | WebSocket for match streaming |

## Environment Variables

Key environment variables (see .env.example for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for JWT tokens
- `DEBUG`: Enable debug mode (True/False)
- `ENVIRONMENT`: Environment name (development/staging/production)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Redis Python**: https://redis-py.readthedocs.io/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Support

For issues or questions, refer to:
- Project README.md
- app/README.md (detailed structure documentation)
- Design document: .kiro/specs/telegram-football-manager/design.md
