# Celery Quick Reference

## Quick Start

### 1. Start Redis
```bash
redis-server
```

### 2. Start Celery Worker
```bash
# Linux/Mac
./scripts/start_celery_worker.sh

# Windows
scripts\start_celery_worker.bat
```

### 3. Start Celery Beat (Optional - for scheduled tasks)
```bash
# Linux/Mac
./scripts/start_celery_beat.sh

# Windows
scripts\start_celery_beat.bat
```

## Common Commands

### Worker Management
```bash
# Start worker
celery -A app.core.celery:celery_app worker --loglevel=info

# Start worker with specific queues
celery -A app.core.celery:celery_app worker -Q matches,updates

# Start worker with concurrency
celery -A app.core.celery:celery_app worker --concurrency=8

# Start worker in background (Linux)
celery -A app.core.celery:celery_app worker --detach
```

### Task Inspection
```bash
# List active tasks
celery -A app.core.celery:celery_app inspect active

# List registered tasks
celery -A app.core.celery:celery_app inspect registered

# List scheduled tasks
celery -A app.core.celery:celery_app inspect scheduled

# Worker statistics
celery -A app.core.celery:celery_app inspect stats

# Active queues
celery -A app.core.celery:celery_app inspect active_queues
```

### Task Control
```bash
# Revoke task
celery -A app.core.celery:celery_app control revoke <task_id>

# Purge all tasks
celery -A app.core.celery:celery_app purge

# Shutdown worker
celery -A app.core.celery:celery_app control shutdown
```

### Beat Scheduler
```bash
# Start beat scheduler
celery -A app.core.celery:celery_app beat --loglevel=info

# Start beat with custom schedule file
celery -A app.core.celery:celery_app beat --schedule=/path/to/schedule
```

## Task Usage in Code

### Execute Task Asynchronously
```python
from app.tasks.match_simulation import simulate_match

# Send task to queue (non-blocking)
task = simulate_match.delay(
    match_id=1,
    home_team_id=10,
    away_team_id=20,
    competition_id=1,
)

# Get task ID
print(f"Task ID: {task.id}")

# Check if task is ready
if task.ready():
    print("Task completed")

# Get result (blocking)
result = task.get(timeout=10)
```

### Execute Task with Options
```python
# Execute with custom queue
task = simulate_match.apply_async(
    args=[1, 10, 20, 1],
    queue='matches',
    priority=10,
)

# Execute with countdown (delay)
task = simulate_match.apply_async(
    args=[1, 10, 20, 1],
    countdown=60,  # Execute after 60 seconds
)

# Execute at specific time
from datetime import datetime, timedelta
task = simulate_match.apply_async(
    args=[1, 10, 20, 1],
    eta=datetime.now() + timedelta(hours=1),
)

# Execute with retry policy
task = simulate_match.apply_async(
    args=[1, 10, 20, 1],
    retry=True,
    retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    }
)
```

### Check Task Status
```python
from celery.result import AsyncResult

# Get task by ID
task = AsyncResult(task_id)

# Check status
print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY

# Get result if ready
if task.successful():
    result = task.result
elif task.failed():
    error = task.info  # Exception info
```

### Chain Tasks
```python
from celery import chain

# Execute tasks in sequence
workflow = chain(
    simulate_match.s(1, 10, 20, 1),
    simulate_match.s(2, 30, 40, 1),
    simulate_match.s(3, 50, 60, 1),
)
result = workflow.apply_async()
```

### Group Tasks (Parallel)
```python
from celery import group

# Execute tasks in parallel
job = group(
    simulate_match.s(1, 10, 20, 1),
    simulate_match.s(2, 30, 40, 1),
    simulate_match.s(3, 50, 60, 1),
)
result = job.apply_async()

# Wait for all tasks
results = result.get(timeout=300)
```

## Available Tasks

### Match Simulation
```python
from app.tasks.match_simulation import simulate_match, simulate_multiple_matches

# Simulate single match
simulate_match.delay(match_id=1, home_team_id=10, away_team_id=20, competition_id=1)

# Simulate multiple matches
simulate_multiple_matches.delay(match_ids=[1, 2, 3, 4, 5])
```

### Weekly Updates
```python
from app.tasks.weekly_updates import (
    process_weekly_update,
    update_player_training,
    update_club_finances,
    process_player_aging,
)

# Process all weekly updates
process_weekly_update.delay()

# Update player training
update_player_training.delay(career_id=1, player_ids=[101, 102, 103])

# Update club finances
update_club_finances.delay(career_id=1, club_id=10)

# Process player aging
process_player_aging.delay(player_ids=[201, 202, 203])
```

### AI Manager
```python
from app.tasks.ai_manager import (
    generate_ai_tactics,
    generate_ai_transfers,
    process_ai_squad_selection,
)

# Generate AI tactics
generate_ai_tactics.delay(team_id=10, opponent_team_id=20, competition_id=1)

# Generate AI transfers
generate_ai_transfers.delay(club_id=10, transfer_budget=10000000)

# Process AI squad selection
process_ai_squad_selection.delay(team_id=10, match_id=100)
```

### Maintenance
```python
from app.tasks.maintenance import cleanup_expired_results, health_check

# Cleanup expired results
cleanup_expired_results.delay()

# Health check
health_check.delay()
```

## Monitoring with Flower

### Install Flower
```bash
pip install flower
```

### Start Flower
```bash
celery -A app.core.celery:celery_app flower --port=5555
```

### Access Flower UI
Open browser: http://localhost:5555

## Redis Commands

### Check Queue Length
```bash
# Connect to Redis
redis-cli -n 1

# Check queue length
LLEN celery

# View queue items
LRANGE celery 0 -1

# Clear queue
DEL celery
```

### Check Results
```bash
# Connect to Redis
redis-cli -n 2

# List all result keys
KEYS celery-task-meta-*

# Get result
GET celery-task-meta-<task_id>

# Clear all results
FLUSHDB
```

## Environment Variables

```bash
# Required
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Optional
CELERY_TASK_TIME_LIMIT=300
CELERY_TASK_SOFT_TIME_LIMIT=240
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
```

## Task Queues

| Queue | Priority | Purpose |
|-------|----------|---------|
| matches | 10 | Match simulations |
| updates | 5 | Weekly updates |
| ai | 3 | AI decisions |
| default | 1 | Misc tasks |

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| process_weekly_update | Monday 00:00 UTC | Weekly game updates |
| cleanup_expired_results | Daily 02:00 UTC | Cleanup old results |

## Troubleshooting

### Worker won't start
```bash
# Check Redis
redis-cli ping

# Check broker URL
echo $CELERY_BROKER_URL

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tasks not executing
```bash
# Check active workers
celery -A app.core.celery:celery_app inspect active

# Check registered tasks
celery -A app.core.celery:celery_app inspect registered

# Check queue
redis-cli -n 1 LLEN celery
```

### Clear stuck tasks
```bash
# Purge all tasks
celery -A app.core.celery:celery_app purge

# Or manually in Redis
redis-cli -n 1 DEL celery
```

## Performance Tips

1. **Adjust concurrency** based on task type:
   - CPU-bound: `--concurrency=<num_cores>`
   - I/O-bound: `--concurrency=<num_cores * 2-4>`

2. **Use task routing** to separate different task types

3. **Set appropriate time limits** to prevent hanging tasks

4. **Monitor memory usage** and adjust `max_tasks_per_child`

5. **Use result backend only when needed** (set `ignore_result=True` for fire-and-forget tasks)

## Useful Links

- [Celery Documentation](https://docs.celeryproject.org/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#tips-and-best-practices)
- [Redis Commands](https://redis.io/commands)
