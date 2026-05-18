# Celery Task Queue Setup Guide

## Overview

This document describes the Celery task queue setup for the Telegram Football Manager project. Celery is used for background task processing, including:

- **Match Simulation**: AI-controlled match simulations running in parallel
- **Weekly Updates**: Scheduled tasks for player training, aging, and finances
- **AI Manager**: Background AI decision-making for opponent teams
- **Maintenance**: Cleanup and health check tasks

## Architecture

### Components

1. **Celery Application** (`app/core/celery.py`)
   - Main Celery configuration
   - Task routing and queue definitions
   - Periodic task scheduling (Celery Beat)

2. **Task Modules**
   - `app/tasks/match_simulation.py` - Match simulation tasks
   - `app/tasks/weekly_updates.py` - Weekly update tasks
   - `app/tasks/ai_manager.py` - AI manager tasks
   - `app/tasks/maintenance.py` - Maintenance tasks

3. **Redis Backend**
   - Broker: `redis://localhost:6379/1`
   - Result Backend: `redis://localhost:6379/2`

### Task Queues

Celery uses multiple queues with different priorities:

| Queue | Priority | Purpose | Example Tasks |
|-------|----------|---------|---------------|
| `matches` | 10 (High) | Match simulations | `simulate_match`, `simulate_multiple_matches` |
| `updates` | 5 (Medium) | Weekly updates | `process_weekly_update`, `update_player_training` |
| `ai` | 3 (Low) | AI decisions | `generate_ai_tactics`, `generate_ai_transfers` |
| `default` | 1 (Lowest) | Misc tasks | `cleanup_expired_results`, `health_check` |

## Configuration

### Celery Settings

Key configuration parameters in `app/core/celery.py`:

```python
# Task execution
task_serializer = "json"
result_serializer = "json"
timezone = "UTC"

# Worker settings
worker_prefetch_multiplier = 4
worker_max_tasks_per_child = 1000

# Task time limits
task_time_limit = 300  # 5 minutes hard limit
task_soft_time_limit = 240  # 4 minutes soft limit

# Task retry
task_acks_late = True
task_reject_on_worker_lost = True
```

### Environment Variables

Required environment variables in `.env`:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## Running Celery

### Start Celery Worker

**Linux/Mac:**
```bash
./scripts/start_celery_worker.sh
```

**Windows:**
```cmd
scripts\start_celery_worker.bat
```

**Manual command:**
```bash
celery -A app.core.celery:celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=matches,updates,ai,default \
    --max-tasks-per-child=1000 \
    --time-limit=300 \
    --soft-time-limit=240
```

### Start Celery Beat (Scheduler)

**Linux/Mac:**
```bash
./scripts/start_celery_beat.sh
```

**Windows:**
```cmd
scripts\start_celery_beat.bat
```

**Manual command:**
```bash
celery -A app.core.celery:celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat:PersistentScheduler
```

### Production Deployment

For production, use a process manager like Supervisor or systemd:

**Supervisor Example:**
```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A app.core.celery:celery_app worker --loglevel=info --concurrency=4
directory=/path/to/project
user=tfm
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A app.core.celery:celery_app beat --loglevel=info
directory=/path/to/project
user=tfm
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

## Task Examples

### Match Simulation Task

```python
from app.tasks.match_simulation import simulate_match

# Synchronous execution (blocking)
result = simulate_match(
    match_id=1,
    home_team_id=10,
    away_team_id=20,
    competition_id=1,
)

# Asynchronous execution (non-blocking)
task = simulate_match.delay(
    match_id=1,
    home_team_id=10,
    away_team_id=20,
    competition_id=1,
)

# Get result (blocks until task completes)
result = task.get(timeout=10)

# Check task status
if task.ready():
    print(f"Task completed: {task.result}")
else:
    print(f"Task status: {task.state}")
```

### Parallel Match Simulation

```python
from app.tasks.match_simulation import simulate_multiple_matches

# Simulate multiple matches in parallel
result = simulate_multiple_matches.delay(
    match_ids=[1, 2, 3, 4, 5]
)

# Wait for all matches to complete
results = result.get(timeout=300)
print(f"Completed {results['completed']} matches")
```

### Weekly Update Task

```python
from app.tasks.weekly_updates import process_weekly_update

# Trigger weekly update manually
task = process_weekly_update.delay()
result = task.get()

print(f"Processed {result['careers_processed']} careers")
print(f"Trained {result['players_trained']} players")
```

## Scheduled Tasks (Celery Beat)

Celery Beat runs periodic tasks automatically:

### Weekly Update
- **Schedule**: Every Monday at midnight (UTC)
- **Task**: `app.tasks.weekly_updates.process_weekly_update`
- **Purpose**: Process training, aging, finances for all careers

### Cleanup Expired Results
- **Schedule**: Every day at 2 AM (UTC)
- **Task**: `app.tasks.maintenance.cleanup_expired_results`
- **Purpose**: Remove old task results from Redis

## Monitoring

### Celery Flower (Web UI)

Install Flower for web-based monitoring:

```bash
pip install flower
```

Start Flower:

```bash
celery -A app.core.celery:celery_app flower --port=5555
```

Access at: http://localhost:5555

### Command Line Monitoring

**List active tasks:**
```bash
celery -A app.core.celery:celery_app inspect active
```

**List registered tasks:**
```bash
celery -A app.core.celery:celery_app inspect registered
```

**Check worker stats:**
```bash
celery -A app.core.celery:celery_app inspect stats
```

**Purge all tasks:**
```bash
celery -A app.core.celery:celery_app purge
```

## Error Handling

### Task Retry Configuration

All tasks inherit from `BaseTask` with automatic retry:

```python
class BaseTask(celery_app.Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True
```

### Task Callbacks

Tasks have lifecycle callbacks:

- `on_success`: Called when task succeeds
- `on_failure`: Called when task fails after all retries
- `on_retry`: Called when task is retried

## Testing

### Unit Tests

Run Celery tests:

```bash
pytest tests/test_celery.py -v
pytest tests/test_tasks.py -v
```

### Manual Testing

Test task execution:

```python
from app.core.celery import celery_app
from app.tasks.match_simulation import simulate_match

# Test task registration
print(celery_app.tasks)

# Test task execution
result = simulate_match(1, 10, 20, 1)
print(result)
```

## Troubleshooting

### Worker Not Starting

1. Check Redis is running:
   ```bash
   redis-cli ping
   ```

2. Check broker URL in `.env`:
   ```bash
   echo $CELERY_BROKER_URL
   ```

3. Check for port conflicts:
   ```bash
   netstat -an | grep 6379
   ```

### Tasks Not Executing

1. Check worker is running:
   ```bash
   celery -A app.core.celery:celery_app inspect active_queues
   ```

2. Check task routing:
   ```bash
   celery -A app.core.celery:celery_app inspect registered
   ```

3. Check task queue:
   ```bash
   redis-cli -n 1 LLEN celery
   ```

### High Memory Usage

1. Reduce `worker_prefetch_multiplier`
2. Lower `worker_max_tasks_per_child`
3. Increase number of workers with lower concurrency

### Task Timeout

1. Increase `task_time_limit` and `task_soft_time_limit`
2. Optimize task logic
3. Split large tasks into smaller subtasks

## Performance Tuning

### Worker Concurrency

Adjust based on CPU cores and task type:

- **CPU-bound tasks**: `concurrency = CPU_cores`
- **I/O-bound tasks**: `concurrency = CPU_cores * 2-4`

### Prefetch Multiplier

- **High throughput**: `worker_prefetch_multiplier = 4-8`
- **Long-running tasks**: `worker_prefetch_multiplier = 1-2`

### Result Backend

For better performance, consider:

- Using Redis with persistence disabled for result backend
- Setting shorter `result_expires` time
- Using `ignore_result=True` for tasks that don't need results

## Security

### Production Checklist

- [ ] Use strong Redis password
- [ ] Enable Redis AUTH
- [ ] Use TLS for Redis connections
- [ ] Restrict Redis network access
- [ ] Use separate Redis databases for broker and results
- [ ] Enable Celery task message signing
- [ ] Limit task time limits
- [ ] Monitor task execution

### Redis Security

Add to Redis configuration:

```conf
requirepass your_strong_password
bind 127.0.0.1
protected-mode yes
```

Update Celery broker URL:

```python
CELERY_BROKER_URL = "redis://:password@localhost:6379/1"
```

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#tips-and-best-practices)
