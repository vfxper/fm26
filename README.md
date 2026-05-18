# Telegram Football Manager

A simplified 2D Football Manager game running as a Telegram Web App. Manage a football club through a complete career mode with squad management, tactics, transfers, training, and real-time 2D match visualization.

## Features

- **Career Mode**: Manage a single club through multiple seasons
- **2D Match Visualization**: Real-time HTML5 Canvas rendering of matches
- **Complete Player Database**: 2600+ players with full attributes
- **Transfer System**: Buy, sell, and loan players
- **Training & Development**: Develop young players and maintain squad fitness
- **Tactics Editor**: Configure formations, roles, and team instructions
- **Financial Management**: Balance budgets, wages, and infrastructure investments
- **Competitions**: Domestic league, cups, and continental competitions

## Technology Stack

- **Backend**: Python 3.11, FastAPI, PostgreSQL, Redis, Celery
- **Frontend**: HTML5 Canvas, JavaScript, Telegram Web App SDK
- **Platform**: Telegram Bot

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+
- Redis 7+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd telegram-football-manager
```

### 2. Create virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Set up development environment (recommended for local development)
./scripts/setup_environment.sh development

# Or manually copy and edit
cp .env.example .env
# Edit .env with your configuration
```

**Note**: The project supports three environments (development, staging, production). See [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md) for details.

### 5. Initialize database

```bash
# Run database migrations
python -m alembic upgrade head

# Or use the migration helper script
python scripts/migrate.py upgrade

# Load player database from CSV (after migrations)
python scripts/load_players.py
```

### 6. Run the application

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (in another terminal)
celery -A app.celery_app worker --loglevel=info

# Start Celery beat scheduler (in another terminal)
celery -A app.celery_app beat --loglevel=info
```

## Development

### Project Structure

```
telegram-football-manager/
├── app/
│   ├── api/              # REST API endpoints
│   ├── core/             # Core game engine modules
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   └── main.py           # FastAPI application entry point
├── frontend/             # HTML5 Canvas frontend
├── tests/                # Test suite
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_match_simulator.py
```

### Code Quality

```bash
# Format code with Black
black app/ tests/

# Lint with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/
```

### Database Migrations

The project uses Alembic for database schema migrations. See the [Migration Guide](docs/MIGRATION_GUIDE.md) for complete documentation.

**Quick commands:**

```bash
# Create new migration (auto-generate from models)
python scripts/migrate.py create "Add email to User"

# Apply migrations
python scripts/migrate.py upgrade

# Rollback one migration
python scripts/migrate.py downgrade

# View current revision
python scripts/migrate.py current

# View migration history
python scripts/migrate.py history
```

**Or use Alembic directly:**

```bash
# Create migration
python -m alembic revision --autogenerate -m "Description"

# Apply migrations
python -m alembic upgrade head

# Rollback
python -m alembic downgrade -1
```

## Documentation

- [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md) - **NEW**: Complete guide for development, staging, and production environments
- [Environment Quick Reference](docs/ENVIRONMENT_QUICK_REFERENCE.md) - **NEW**: Quick commands and cheat sheet
- [Database Migration Guide](docs/MIGRATION_GUIDE.md) - **NEW**: Complete guide for database migrations with Alembic
- [Migration Quick Reference](docs/MIGRATION_QUICK_REFERENCE.md) - **NEW**: Quick migration commands
- [Requirements Document](.kiro/specs/telegram-football-manager/requirements.md)
- [Design Document](.kiro/specs/telegram-football-manager/design.md)
- [Implementation Tasks](.kiro/specs/telegram-football-manager/tasks.md)
- [Database Setup Guide](docs/DATABASE_SETUP.md)
- [Bot Setup Guide](docs/BOT_SETUP.md)
- [Celery Setup Guide](docs/CELERY_SETUP.md)

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]
