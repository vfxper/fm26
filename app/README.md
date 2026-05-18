# Telegram Football Manager - Application Structure

## Directory Structure

```
app/
├── main.py                 # FastAPI application entry point
├── __init__.py            # Package initialization
│
├── api/                   # API Layer
│   ├── __init__.py
│   ├── dependencies.py    # Dependency injection (DB, cache, auth)
│   ├── websocket.py       # WebSocket handler for match streaming
│   └── routes/            # API route modules
│       └── __init__.py    # API router registration
│
├── core/                  # Core Infrastructure
│   ├── __init__.py
│   ├── config.py          # Application configuration (env variables)
│   ├── database.py        # Async SQLAlchemy setup
│   ├── cache.py           # Redis cache setup
│   └── logging.py         # Structured logging configuration
│
├── models/                # SQLAlchemy ORM Models
│   └── __init__.py        # Model imports
│
├── schemas/               # Pydantic Schemas
│   └── __init__.py        # Schema imports (request/response models)
│
├── services/              # Business Logic Layer
│   └── __init__.py        # Service imports (game engine, modules)
│
└── utils/                 # Utility Functions
    ├── __init__.py
    └── exceptions.py      # Custom exceptions
```

## Layer Responsibilities

### API Layer (`app/api/`)
- **Purpose**: HTTP endpoints and WebSocket handlers
- **Components**:
  - `dependencies.py`: Dependency injection for routes (DB sessions, cache, authentication)
  - `websocket.py`: Real-time match event streaming via WebSocket
  - `routes/`: REST API endpoint definitions organized by domain

### Core Layer (`app/core/`)
- **Purpose**: Infrastructure and configuration
- **Components**:
  - `config.py`: Environment-based configuration using Pydantic Settings
  - `database.py`: Async SQLAlchemy engine and session management
  - `cache.py`: Redis connection pool and cache utilities
  - `logging.py`: Structured logging setup (JSON in production, readable in dev)

### Models Layer (`app/models/`)
- **Purpose**: Database schema definitions
- **Components**: SQLAlchemy ORM models for all database tables
- **Note**: Models will be created in subsequent tasks (Task 2.x)

### Schemas Layer (`app/schemas/`)
- **Purpose**: API request/response validation
- **Components**: Pydantic models for API data validation and serialization
- **Note**: Schemas will be created alongside API routes

### Services Layer (`app/services/`)
- **Purpose**: Business logic and game engine
- **Components**:
  - `game_engine.py`: Match simulation (Task 4.x)
  - `career_manager.py`: Career mode logic (Task 6.x)
  - `transfer_engine.py`: Transfer market (Task 8.x)
  - `training_module.py`: Player development (Task 10.x)
  - `finance_module.py`: Club finances (Task 11.x)
  - And other game modules...

### Utils Layer (`app/utils/`)
- **Purpose**: Shared utilities and helpers
- **Components**:
  - `exceptions.py`: Custom exception classes
  - Additional utilities as needed

## Key Features

### Async Support
- All database operations use `async/await` with SQLAlchemy 2.0
- Redis operations are async using `redis.asyncio`
- FastAPI routes are async by default

### Configuration Management
- Environment variables loaded via Pydantic Settings
- Type-safe configuration with validation
- Separate configs for dev/staging/production

### Database Management
- Async PostgreSQL with connection pooling
- SQLAlchemy 2.0 with async support
- Automatic session management via dependency injection

### Caching
- Redis for session data, match state, and frequently accessed data
- Connection pooling for optimal performance
- Predefined cache key patterns in `CacheKeys` class

### Error Handling
- Custom exception hierarchy for domain-specific errors
- Global exception handlers in `main.py`
- Structured error responses

### Logging
- Structured JSON logging in production
- Human-readable format in development
- Configurable log levels per module

### WebSocket Support
- Real-time match event streaming
- Connection management with room-based broadcasting
- Automatic reconnection handling

## Development Workflow

1. **Add a new feature**:
   - Create model in `app/models/`
   - Create schema in `app/schemas/`
   - Create service in `app/services/`
   - Create route in `app/api/routes/`
   - Register route in `app/api/routes/__init__.py`

2. **Run the application**:
   ```bash
   # Development mode with auto-reload
   python app/main.py
   
   # Or using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Run tests**:
   ```bash
   pytest tests/ -v --cov=app
   ```

## Next Steps

The following components will be implemented in subsequent tasks:

- **Task 2.x**: Database schema and models
- **Task 3.x**: Player database loader
- **Task 4.x**: Match simulation engine
- **Task 6.x**: Career manager
- **Task 8.x**: Transfer engine
- **Task 23-29**: REST API endpoints
- **Task 30**: WebSocket implementation (already scaffolded)
